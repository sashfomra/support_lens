"""
Ollama HTTP client — wraps all 6 SLM workflows.
All prompts use PII-masked text. Outputs go through policy filter before returning.
"""
import httpx
import json
import os
import re
from typing import Optional

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
TIMEOUT = 120.0  # seconds


async def _generate(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """Core Ollama /api/generate call."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 512,
            "top_p": 0.9,
        }
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()


async def check_connection() -> bool:
    """Returns True if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def list_models() -> list:
    """Return available models from Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ── Workflow 1: Ticket Summarizer ─────────────────────────────────────────────
async def summarize_ticket(masked_text: str, subject: str) -> str:
    system = (
        "You are a support ticket summarizer. "
        "Produce exactly 3 lines — no bullets, no numbering, no extra text. "
        "Line 1: What happened (the issue in one sentence). "
        "Line 2: What the customer wants (explicit or implied ask). "
        "Line 3: What has been tried (prior attempts, or 'None mentioned'). "
        "Be concise and factual. Do not add any intro or closing."
    )
    prompt = f"Subject: {subject}\n\nTicket:\n{masked_text}\n\nSummarize:"
    result = await _generate(prompt, system, temperature=0.2)
    # Ensure exactly 3 lines
    lines = [l.strip() for l in result.strip().split("\n") if l.strip()]
    if len(lines) >= 3:
        return "\n".join(lines[:3])
    return result


# ── Workflow 2: Solution Rewriter (RAG) ───────────────────────────────────────
async def rewrite_kb_solution(article_title: str, article_content: str, ticket_summary: str) -> str:
    system = (
        "You are a support knowledge base assistant. "
        "Rewrite the provided KB article as clear, numbered step-by-step resolution instructions "
        "tailored to the customer's specific issue. Use simple language. "
        "Do not add information not in the KB article. "
        "Start immediately with Step 1."
    )
    prompt = (
        f"Customer Issue Summary:\n{ticket_summary}\n\n"
        f"KB Article: {article_title}\n{article_content}\n\n"
        "Rewrite as step-by-step instructions:"
    )
    return await _generate(prompt, system, temperature=0.1)


# ── Workflow 3: Draft Reply Generator ─────────────────────────────────────────
async def generate_draft_reply(
    masked_text: str,
    ai_summary: str,
    intent: str,
    emotion_type: str,
    emotion_score: float,
    customer_tier: str,
    is_churn_risk: bool,
    kb_steps: Optional[str] = None,
) -> tuple[str, str]:
    """Returns (draft_reply, tone_applied)."""

    # Determine tone
    if is_churn_risk:
        tone = "churn_risk"
        tone_instruction = (
            "Use a warm, empathetic tone. "
            "Acknowledge their frustration sincerely. "
            "Include a specific retention offer or goodwill gesture. "
            "Express genuine care about keeping them as a customer."
        )
    elif emotion_score and emotion_score >= 7:
        tone = "angry_customer"
        tone_instruction = (
            "Start with a sincere empathetic opening and apology. "
            "Acknowledge the specific frustration. "
            "Provide a concrete next step. "
            "Use simple language — no jargon. No corporate-speak."
        )
    elif customer_tier == "enterprise":
        tone = "enterprise"
        tone_instruction = (
            "Use formal, professional tone. "
            "Reference SLA commitment. "
            "Provide a named escalation path. "
            "Be precise and structured."
        )
    else:
        tone = "neutral"
        tone_instruction = (
            "Be concise, direct, and solution-first. "
            "Acknowledge the issue briefly, then focus on resolution."
        )

    kb_section = f"\nRelevant KB Solution Steps:\n{kb_steps}" if kb_steps else ""

    system = (
        "You are a professional customer support agent writing a reply. "
        "Write ONLY the reply email body — no subject line, no 'From:', no meta-text. "
        f"{tone_instruction} "
        "End with a polite closing."
    )
    prompt = (
        f"Ticket Summary:\n{ai_summary}\n"
        f"Customer Tier: {customer_tier}\n"
        f"Intent: {intent}\n"
        f"Emotion: {emotion_type} (score {emotion_score}/10)\n"
        f"{kb_section}\n\n"
        f"Ticket Text:\n{masked_text}\n\n"
        "Write the reply:"
    )
    draft = await _generate(prompt, system, temperature=0.4)
    return draft, tone


# ── Workflow 4: Weekly Insight Narrator ───────────────────────────────────────
async def generate_weekly_narrative(stats: dict) -> str:
    system = (
        "You are a support operations analyst writing a weekly digest for team leads. "
        "Write in plain English, no bullet hell — use short paragraphs. "
        "Be specific, reference the numbers provided, be actionable."
    )
    prompt = (
        f"Weekly Support Stats (past 7 days):\n"
        f"Total tickets: {stats.get('total', 0)}\n"
        f"Top categories: {stats.get('top_categories', [])}\n"
        f"CSAT average: {stats.get('avg_csat', 'N/A')}\n"
        f"CSAT change from last week: {stats.get('csat_change', 'N/A')}\n"
        f"SLA breach rate: {stats.get('sla_breach_rate', 'N/A')}%\n"
        f"Churn risk tickets: {stats.get('churn_risks', 0)}\n"
        f"Most common intent: {stats.get('top_intent', 'N/A')}\n"
        f"Resolved tickets: {stats.get('resolved', 0)}\n"
        f"Previous week total: {stats.get('prev_total', 0)}\n\n"
        "Write a professional weekly digest covering: top issue categories, CSAT analysis, "
        "SLA performance, what improved, and ONE specific action recommendation:"
    )
    return await _generate(prompt, system, temperature=0.5)


# ── Workflow 5: Manager Q&A Bot ───────────────────────────────────────────────
async def answer_manager_question(question: str, context_data: str) -> str:
    system = (
        "You are a support data analyst assistant for a team manager. "
        "Answer questions about support data clearly and concisely. "
        "Use the provided data context. Be direct — give the answer first, then explain. "
        "If the data doesn't support a clear answer, say so honestly."
    )
    prompt = (
        f"Support Data Context:\n{context_data}\n\n"
        f"Manager Question: {question}\n\n"
        "Answer:"
    )
    return await _generate(prompt, system, temperature=0.3)


# ── Workflow 6: Auto-Tagger ───────────────────────────────────────────────────
async def auto_tag_ticket(masked_text: str, subject: str) -> dict:
    system = (
        "You are a support ticket classifier. "
        "Return ONLY a JSON object with these exact keys: "
        "product_area (one of: Billing, Login, Performance, UX, Feature, Other), "
        "platform (one of: Android, iOS, Web, API, Unknown), "
        "severity (one of: P1, P2, P3). "
        "No explanation, no markdown, just the JSON."
    )
    prompt = f"Subject: {subject}\nTicket: {masked_text[:500]}\n\nClassify:"
    result = await _generate(prompt, system, temperature=0.1)

    # Parse JSON from response
    try:
        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception:
        pass

    # Fallback defaults
    return {"product_area": "Other", "platform": "Unknown", "severity": "P3"}
