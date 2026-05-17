"""
Solution Engine — multi-source search, reranking, SLM rewriting, guardrails.

Flow:
  1. Build clean search query from ticket data
  2. Parallel search: ChromaDB docs + Reddit + Stack Overflow
  3. Rerank candidates by weighted scoring formula
  4. Compute confidence score — fallback if < 0.65
  5. Rewrite with Groq LLM (llama3-8b-8192, free tier)
  6. Guardrail check on SLM output
  7. Return structured response
"""
import os
import re
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CHROMA_COLLECTION = "supportlens_docs"
CONFIDENCE_THRESHOLD = 0.35   # lowered from 0.45 — works well with small local KBs
_executor = ThreadPoolExecutor(max_workers=4)

# Guardrail phrases — block if present in SLM output
BLOCK_PHRASES = [
    "i cannot", "i don't know", "not sure", "as an ai",
    "no information available", "i'm unable", "i am unable",
]

# PII placeholder tokens to strip from queries
PII_TOKENS = re.compile(
    r"\[(?:CUSTOMER_NAME|EMAIL|PHONE|ORDER_ID|IP_ADDRESS|CARD_NUMBER|SSN|CUSTOMER|ORGANIZATION|LOCATION)\]",
    re.IGNORECASE,
)


def _build_query(summary: str, issue_category: str, product_name: str) -> str:
    """Build a clean 10–15 word search query."""
    base = f"{summary} {issue_category} {product_name}"
    base = PII_TOKENS.sub("", base)
    base = re.sub(r"\s+", " ", base).strip()
    words = base.split()[:15]
    return " ".join(words)


def _chroma_search(query: str, top_k: int = 3) -> list[dict]:
    """Search ChromaDB for similar document chunks."""
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        from pathlib import Path

        db_path = Path(__file__).parent / "chroma_db"
        if not db_path.exists():
            return []

        client = chromadb.PersistentClient(path=str(db_path))
        try:
            col = client.get_collection(CHROMA_COLLECTION)
        except Exception:
            return []

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode([query]).tolist()[0]

        results = col.query(
            query_embeddings=[embedding],
            n_results=min(top_k, col.count() or 1),
            include=["documents", "metadatas", "distances"],
        )

        candidates = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            similarity = max(0.0, 1.0 - dist)
            candidates.append({
                "type": "docs",
                "url": meta.get("source_url", ""),
                "text": doc,
                "section": meta.get("section_title", ""),
                "raw_score": similarity,
                "source_weight": 1.0,
                "final_score": similarity * 1.0,
                "snippet": doc[:100],
            })
        return candidates
    except Exception as e:
        logger.error(f"ChromaDB search error: {e}")
        return []


def _reddit_search_sync(query: str, product_name: str) -> list[dict]:
    """Sync wrapper for Reddit search."""
    from scrapers.reddit_scraper import search_reddit_solutions
    raw = search_reddit_solutions(query, product_name)
    candidates = []
    for r in raw:
        upvotes = r.get("upvote_count", 0)
        raw_score = min(upvotes / 500, 1.0)
        final = raw_score * 0.75
        candidates.append({
            "type": "reddit",
            "url": r.get("post_url", ""),
            "text": r.get("top_comment_body", ""),
            "section": r.get("post_title", ""),
            "raw_score": raw_score,
            "source_weight": 0.75,
            "final_score": final,
            "snippet": r.get("top_comment_body", "")[:100],
        })
    return candidates


def _stackoverflow_search_sync(query: str) -> list[dict]:
    """Sync wrapper for Stack Overflow search."""
    from scrapers.stackoverflow_scraper import search_stackoverflow
    r = search_stackoverflow(query)
    if not r:
        return []
    raw_score = 0.85  # accepted answers are reliable
    final = raw_score * 0.9
    return [{
        "type": "stackoverflow",
        "url": r.get("question_url", ""),
        "text": r.get("answer_body", ""),
        "section": r.get("question_title", ""),
        "raw_score": raw_score,
        "source_weight": 0.9,
        "final_score": final,
        "snippet": r.get("answer_body", "")[:100],
    }]


def _groq_rewrite(
    summary: str,
    issue_category: str,
    emotion_score: float,
    source_1: dict,
    source_2: dict,
) -> Optional[str]:
    """Call Groq API (llama3-8b-8192) to rewrite solution. Falls back if unavailable."""
    # Read key here (after dotenv has been loaded by main.py)
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        logger.warning("GROQ_API_KEY not set in environment or .env file")
        return None

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        empathetic_instruction = (
            "Start with one empathetic opening line acknowledging their frustration."
            if emotion_score > 6
            else "Skip the empathetic opening — go straight to the solution."
        )

        prompt = f"""Customer issue summary:
{summary}

Issue category: {issue_category}
Customer emotion score: {emotion_score:.1f} out of 10

Best matching sources:
Source 1 ({source_1.get('url', 'internal docs')}):
{source_1.get('text', '')[:600]}

Source 2 ({source_2.get('url', 'internal docs')}):
{source_2.get('text', '')[:600]}

Write a solution reply with:
- {empathetic_instruction}
- 4 to 6 numbered resolution steps using ONLY the information from the sources above
- Closing line: "If these steps do not resolve your issue, please reply and we will escalate this immediately."

Do not mention the sources by name. Do not add disclaimers. Do not make up information."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # updated — llama3-8b-8192 was decommissioned
            messages=[
                {"role": "system", "content": "You are a senior customer support agent. Write clear, empathetic, step-by-step solutions based only on the provided sources. Never invent steps not present in the sources."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return None


def _guardrail_check(text: Optional[str]) -> bool:
    """Returns True if text passes guardrails, False if it should be blocked."""
    if not text or len(text) < 100:
        return False
    lower = text.lower()
    for phrase in BLOCK_PHRASES:
        if phrase in lower:
            logger.warning(f"Guardrail blocked phrase: '{phrase}'")
            return False
    return True


def _groq_general_knowledge(
    summary: str,
    issue_category: str,
    emotion_score: float,
    intent: str,
) -> Optional[str]:
    """
    General-knowledge fallback: ask Groq to generate a best-effort support
    answer from its training knowledge when no KB/Reddit/SO match is found.
    The answer is clearly flagged as AI-generated, not source-grounded.
    """
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        return None

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        empathetic_line = (
            "Start with one empathetic opening line."
            if emotion_score > 6
            else "Get straight to the solution."
        )

        prompt = f"""You are a senior customer support agent.

A customer submitted this support issue:
{summary}

Issue category: {issue_category}
Intent: {intent}
Emotion score: {emotion_score:.1f}/10

Our internal knowledge base has no specific article for this issue, so use your
best general knowledge as an experienced support agent to help.

Write a helpful support reply:
- {empathetic_line}
- 4 to 5 numbered practical resolution steps a customer can try right now
- Closing: "If these steps do not resolve your issue, please reply with more details and we will investigate further."

Keep it clear, concise, and friendly. Do not invent company-specific policies."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert customer support agent. Provide practical, clear, step-by-step answers."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq general knowledge fallback error: {e}")
        return None


async def generate_solution(
    ticket_id: str,
    summary: str,
    issue_category: str,
    product_name: str,
    emotion_score: float,
    intent: str,
) -> dict:
    """
    Main async solution generator.
    Returns structured solution object.
    """
    query = _build_query(summary, issue_category, product_name)
    logger.info(f"Solution engine query: '{query}' for ticket {ticket_id}")

    loop = asyncio.get_event_loop()

    # Step 2 — Run all 3 searches in parallel
    chroma_task = loop.run_in_executor(_executor, _chroma_search, query)
    reddit_task = loop.run_in_executor(_executor, _reddit_search_sync, query, product_name)
    so_task = loop.run_in_executor(_executor, _stackoverflow_search_sync, query)

    chroma_results, reddit_results, so_results = await asyncio.gather(
        chroma_task, reddit_task, so_task
    )

    # Step 3 — Merge + rerank
    all_candidates = chroma_results + reddit_results + so_results
    all_candidates.sort(key=lambda x: x["final_score"], reverse=True)
    top_2 = all_candidates[:2]

    # Step 4 — Confidence
    if top_2:
        confidence = round(max(c["final_score"] for c in top_2), 2)
    else:
        confidence = 0.0

    low_confidence = confidence < CONFIDENCE_THRESHOLD or len(top_2) == 0

    # Step 5 — SLM rewriting (source-grounded path)
    solution_text = None
    is_general_knowledge = False

    if not low_confidence:
        src1 = top_2[0]
        src2 = top_2[1] if len(top_2) > 1 else top_2[0]
        raw_solution = await loop.run_in_executor(
            _executor, _groq_rewrite, summary, issue_category, emotion_score, src1, src2
        )
        if _guardrail_check(raw_solution):
            solution_text = raw_solution
        else:
            low_confidence = True  # guardrail blocked — try general knowledge

    # Step 5b — General knowledge fallback (when no source match)
    if low_confidence or solution_text is None:
        logger.info(f"No source match for ticket {ticket_id} — trying general knowledge fallback")
        raw_general = await loop.run_in_executor(
            _executor, _groq_general_knowledge, summary, issue_category, emotion_score, intent
        )
        if _guardrail_check(raw_general):
            solution_text = raw_general
            is_general_knowledge = True
            logger.info("General knowledge fallback succeeded")
        else:
            logger.warning("General knowledge fallback also failed guardrails")

    fallback_flag = solution_text is None

    # Build response
    source_urls = [c["url"] for c in top_2 if c.get("url")]
    sources_used = [{
        "type": c["type"],
        "url": c["url"],
        "score": round(c["final_score"], 3),
        "snippet": c.get("snippet", ""),
    } for c in top_2]

    return {
        "ticket_id": ticket_id,
        "solution_text": solution_text,
        "source_urls": source_urls,
        "confidence_score": confidence,
        "fallback_flag": fallback_flag,
        "is_general_knowledge": is_general_knowledge,  # frontend can show a note
        "sources_used": sources_used,
        "message": None if not fallback_flag else "No solution could be generated — escalating to senior agent",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query_used": query,
    }
