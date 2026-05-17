"""
Core AI pipeline — processes every incoming ticket through:
1. PII masking
2. Emotion detection & scoring
3. Urgency scoring (weighted composite)
4. Intent detection
5. Churn risk detection
6. Auto-tagging via SLM
7. Ticket summarization via SLM
8. RAG KB search
9. Guardrails (policy filter)
10. Audit logging
"""
import re
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from ai.pii_masker import mask_pii
from ai import ollama_client as llm
from ai import rag_engine as rag

# ── Constants ─────────────────────────────────────────────────────────────────
CHURN_PHRASES = [
    "cancelling", "cancel my account", "switching to competitor",
    "last chance", "requesting refund", "closing my account",
    "cancel subscription", "leaving your service", "never using again",
    "worst service", "going to [competitor]"
]

POLICY_BANNED = {
    "legal": ["liable", "legal action", "lawsuit", "litigation", "sue you"],
    "commitment": ["we guarantee", "we promise", "definitely will", "100% certain"],
    "refund_terms": [],  # Populated per-request
}

INTENT_KEYWORDS = {
    "refund": ["refund", "money back", "charge", "overcharged", "billing error", "payment failed"],
    "bug": ["bug", "crash", "error", "broken", "not working", "doesn't work", "500", "404"],
    "feature": ["feature request", "would be nice", "suggestion", "add", "improvement"],
    "account": ["can't login", "locked out", "password", "access", "account blocked", "2fa"],
    "churn": CHURN_PHRASES,
    "complaint": ["frustrated", "disappointed", "terrible", "awful", "unacceptable"],
}

EMOTION_KEYWORDS = {
    "angry": ["furious", "angry", "rage", "outraged", "unacceptable", "terrible", "disgusting"],
    "frustrated": ["frustrated", "annoyed", "fed up", "sick of", "tired of", "been waiting"],
    "confused": ["confused", "don't understand", "not sure", "unclear", "how do i"],
    "worried": ["worried", "concerned", "anxious", "afraid", "scared"],
    "neutral": [],
    "happy": ["thank", "great", "awesome", "love", "amazing", "excellent"],
}

SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24}


# ── Emotion Detection (rule-based with optional transformer) ──────────────────
def detect_emotion(text: str) -> Tuple[str, float]:
    """Returns (emotion_type, intensity_score 1-10)."""
    text_lower = text.lower()
    scores = {}

    for emotion, keywords in EMOTION_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        scores[emotion] = count

    # Find dominant emotion
    dominant = max(scores, key=scores.get)
    if scores[dominant] == 0:
        dominant = "neutral"

    # Score intensity 1-10 based on multiple signals
    intensity = 5.0  # base

    # Caps/exclamation boosters
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    exclamations = text.count("!")
    questions = text.count("?")

    intensity += min(caps_ratio * 10, 2.0)
    intensity += min(exclamations * 0.5, 2.0)
    intensity += min(questions * 0.3, 1.0)

    # Anger/frustration keyword boost
    anger_words = ["furious", "outraged", "terrible", "worst", "horrible", "unacceptable"]
    anger_count = sum(1 for w in anger_words if w in text_lower)
    intensity += min(anger_count * 0.8, 2.0)

    # Happy dampens intensity
    if dominant == "happy":
        intensity = min(intensity, 4.0)

    intensity = round(max(1.0, min(10.0, intensity)), 1)
    return dominant, intensity


# ── Intent Detection ──────────────────────────────────────────────────────────
def detect_intent(text: str) -> str:
    """Returns the primary intent label."""
    text_lower = text.lower()
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        scores[intent] = sum(1 for kw in keywords if kw in text_lower)

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "complaint"
    return best


# ── Churn Risk Detection ──────────────────────────────────────────────────────
def detect_churn_risk(text: str) -> bool:
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in CHURN_PHRASES)


# ── Urgency Scoring Engine ────────────────────────────────────────────────────
def compute_urgency_score(
    emotion_score: float,
    emotion_type: str,
    is_churn_risk: bool,
    customer_tier: str,
    intent: str,
    sla_hours_remaining: Optional[float] = None,
    keyword_severity: str = "P3",
) -> float:
    """
    Composite urgency score 0-100 using weighted signals.
    Weights:
      emotion_score: 30%
      customer_tier: 20%
      churn_risk: 20%
      sla_pressure: 15%
      intent_severity: 15%
    """
    # Emotion (0-30)
    emotion_component = (emotion_score / 10) * 30

    # Tier (0-20)
    tier_scores = {"enterprise": 20, "premium": 12, "standard": 5}
    tier_component = tier_scores.get(customer_tier, 5)

    # Churn risk (0-20)
    churn_component = 20 if is_churn_risk else 0

    # SLA pressure (0-15)
    if sla_hours_remaining is not None:
        if sla_hours_remaining <= 0:
            sla_component = 15
        elif sla_hours_remaining <= 1:
            sla_component = 12
        elif sla_hours_remaining <= 2:
            sla_component = 8
        else:
            sla_component = max(0, 15 - (sla_hours_remaining / 4) * 5)
    else:
        sla_component = 5

    # Intent severity (0-15)
    intent_scores = {
        "churn": 15, "refund": 12, "bug": 10, "account": 8, "complaint": 6, "feature": 2
    }
    intent_component = intent_scores.get(intent, 5)

    total = emotion_component + tier_component + churn_component + sla_component + intent_component
    return round(min(100.0, max(0.0, total)), 1)


# ── Policy Filter ─────────────────────────────────────────────────────────────
def apply_policy_filter(text: str, is_refund_eligible: bool = False) -> Tuple[str, list]:
    """
    Hard policy rules on generated text.
    Returns (filtered_text, list_of_flags_triggered)
    """
    flags = []
    result = text

    # Block legal statements
    for term in POLICY_BANNED["legal"]:
        if term.lower() in result.lower():
            flags.append(f"LEGAL_STATEMENT:{term}")
            result = re.sub(re.escape(term), "[POLICY REMOVED]", result, flags=re.IGNORECASE)

    # Flag commitment language
    for term in POLICY_BANNED["commitment"]:
        if term.lower() in result.lower():
            flags.append(f"COMMITMENT_LANGUAGE:{term}")

    # Block competitor mentions (common competitor names)
    competitors = ["zendesk", "freshdesk", "salesforce", "hubspot", "intercom", "competitor"]
    for c in competitors:
        if c.lower() in result.lower():
            flags.append(f"COMPETITOR_MENTION:{c}")
            result = re.sub(re.escape(c), "[competitor]", result, flags=re.IGNORECASE)

    return result, flags


# ── Requires Human Gate ───────────────────────────────────────────────────────
def requires_human_escalation(
    is_churn_risk: bool,
    emotion_score: float,
    intent: str,
    customer_tier: str,
    text: str,
) -> bool:
    """Returns True if this ticket must be human-handled."""
    if is_churn_risk:
        return True
    if emotion_score >= 8:
        return True
    if any(w in text.lower() for w in ["lawsuit", "legal", "attorney", "regulatory"]):
        return True
    if customer_tier == "enterprise" and intent in ("refund", "churn"):
        return True
    return False


# ── Main Pipeline ─────────────────────────────────────────────────────────────
async def process_ticket(
    subject: str,
    description: str,
    customer_tier: str = "standard",
    agent_id: str = "system",
    run_llm: bool = True,
) -> dict:
    """
    Full pipeline: PII mask → emotion → urgency → intent → tags → summary → RAG.
    Returns enriched ticket data dict.
    """
    # 1. PII masking
    combined_text = f"{subject}. {description}"
    masked_text, pii_found = mask_pii(combined_text)

    # 2. Emotion detection
    emotion_type, emotion_score = detect_emotion(description)

    # 3. Intent & churn
    intent = detect_intent(description)
    is_churn_risk = detect_churn_risk(description) or intent == "churn"

    # 4. Urgency score
    severity = "P1" if emotion_score >= 8 or is_churn_risk else "P2" if emotion_score >= 5 else "P3"
    sla_hours = SLA_HOURS.get(severity, 24)
    sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

    urgency_score = compute_urgency_score(
        emotion_score=emotion_score,
        emotion_type=emotion_type,
        is_churn_risk=is_churn_risk,
        customer_tier=customer_tier,
        intent=intent,
        sla_hours_remaining=sla_hours,
        keyword_severity=severity,
    )

    # 5. Human escalation gate
    is_human_required = requires_human_escalation(
        is_churn_risk, emotion_score, intent, customer_tier, description
    )

    result = {
        "masked_text": masked_text,
        "pii_found": pii_found,
        "emotion_type": emotion_type,
        "emotion_score": emotion_score,
        "intent": intent,
        "is_churn_risk": is_churn_risk,
        "is_escalated": is_churn_risk or emotion_score >= 8,
        "requires_human": is_human_required,
        "urgency_score": urgency_score,
        "severity": severity,
        "sla_deadline": sla_deadline,
        "ai_summary": None,
        "ai_draft_reply": None,
        "ai_draft_confidence": None,
        "product_area": None,
        "platform": None,
        "kb_suggestions": [],
        "policy_flags": [],
    }

    if not run_llm:
        return result

    # 6. LLM auto-tagger
    try:
        tags = await llm.auto_tag_ticket(masked_text, subject)
        result["product_area"] = tags.get("product_area", "Other")
        result["platform"] = tags.get("platform", "Unknown")
        if tags.get("severity") and tags["severity"] in SLA_HOURS:
            result["severity"] = tags["severity"]
    except Exception as e:
        result["product_area"] = "Other"
        result["platform"] = "Unknown"

    # 7. Ticket summarizer
    try:
        summary = await llm.summarize_ticket(masked_text, subject)
        result["ai_summary"] = summary
    except Exception:
        result["ai_summary"] = f"Issue: {subject}\nWants: Resolution\nTried: Unknown"

    # 8. RAG KB search
    try:
        kb_results = await rag.async_search(masked_text, top_k=3)
        result["kb_suggestions"] = [
            {"article_id": aid, "title": title, "content": content, "confidence": conf}
            for aid, title, content, conf in kb_results
        ]
    except Exception:
        result["kb_suggestions"] = []

    return result
