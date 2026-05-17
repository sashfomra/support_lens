"""Tickets router — CRUD + AI enrichment."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from database import get_db, SessionLocal, Ticket, KBArticle, KBSuggestion, AuditLog
from models import TicketCreate, TicketOut, TicketUpdate, DraftReplyRequest, DraftReplyOut
from ai import pipeline, ollama_client as llm, rag_engine as rag
from ai.pipeline import apply_policy_filter

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/", response_model=TicketOut)
async def create_ticket(payload: TicketCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ticket = Ticket(
        subject=payload.subject,
        description=payload.description,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_tier=payload.customer_tier,
        source=payload.source,
        assigned_agent_id=payload.assigned_agent_id,
        assigned_agent_name=payload.assigned_agent_name,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Run AI pipeline in background (non-blocking for fast response)
    background_tasks.add_task(_enrich_ticket, ticket.id, payload.subject, payload.description, payload.customer_tier)
    return ticket


@router.post("/process-sync", response_model=TicketOut)
async def create_ticket_sync(payload: TicketCreate, db: Session = Depends(get_db)):
    """Create ticket and wait for full AI enrichment (for demo mode)."""
    ticket = Ticket(
        subject=payload.subject,
        description=payload.description,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_tier=payload.customer_tier,
        source=payload.source,
        assigned_agent_id=payload.assigned_agent_id,
        assigned_agent_name=payload.assigned_agent_name,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    result = await pipeline.process_ticket(
        subject=payload.subject,
        description=payload.description,
        customer_tier=payload.customer_tier,
        run_llm=True,
    )
    _apply_pipeline_result(db, ticket, result)
    db.commit()
    db.refresh(ticket)

    # Save KB suggestions
    for kb in result.get("kb_suggestions", []):
        sug = KBSuggestion(
            ticket_id=ticket.id,
            article_id=kb["article_id"],
            confidence_score=kb["confidence"],
        )
        db.add(sug)
    db.commit()

    # Audit log
    db.add(AuditLog(
        ticket_id=ticket.id,
        action="pipeline_run",
        slm_prompt=result.get("masked_text", "")[:1000],
        policy_flags=",".join(result.get("policy_flags", [])),
    ))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/", response_model=List[TicketOut])
def list_tickets(
    status: Optional[str] = None,
    intent: Optional[str] = None,
    emotion_type: Optional[str] = None,
    customer_tier: Optional[str] = None,
    is_churn_risk: Optional[bool] = None,
    sort_by: str = Query("urgency_score", enum=["urgency_score", "created_at", "emotion_score"]),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    q = db.query(Ticket)
    if status:
        q = q.filter(Ticket.status == status)
    if intent:
        q = q.filter(Ticket.intent == intent)
    if emotion_type:
        q = q.filter(Ticket.emotion_type == emotion_type)
    if customer_tier:
        q = q.filter(Ticket.customer_tier == customer_tier)
    if is_churn_risk is not None:
        q = q.filter(Ticket.is_churn_risk == is_churn_risk)

    if sort_by == "urgency_score":
        q = q.order_by(Ticket.urgency_score.desc().nulls_last())
    elif sort_by == "created_at":
        q = q.order_by(Ticket.created_at.desc())
    elif sort_by == "emotion_score":
        q = q.order_by(Ticket.emotion_score.desc().nulls_last())

    return q.offset(offset).limit(limit).all()


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(ticket, k, v)
    if payload.status == "resolved" and not ticket.resolved_at:
        ticket.resolved_at = datetime.now(timezone.utc)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}/suggestions")
def get_suggestions(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    suggestions = db.query(KBSuggestion).filter(KBSuggestion.ticket_id == ticket_id).all()
    result = []
    for s in suggestions:
        article = db.query(KBArticle).filter(KBArticle.id == s.article_id).first()
        result.append({
            "article_id": s.article_id,
            "article_title": article.title if article else "Unknown",
            "confidence_score": s.confidence_score,
            "rewritten_steps": s.rewritten_steps,
        })

    if not result and ticket.description_masked:
        # Real-time RAG search
        hits = rag.search(ticket.description_masked or ticket.description, top_k=3)
        for aid, title, content, conf in hits:
            result.append({
                "article_id": aid,
                "article_title": title,
                "confidence_score": conf,
                "rewritten_steps": None,
            })
    return result


@router.post("/draft-reply", response_model=DraftReplyOut)
async def get_draft_reply(payload: DraftReplyRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == payload.ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    # Get KB solution steps if available
    kb_steps = None
    if rag.is_ready():
        hits = rag.search(ticket.description_masked or ticket.description, top_k=1)
        if hits:
            aid, title, content, conf = hits[0]
            if conf >= 0.72:
                try:
                    kb_steps = await llm.rewrite_kb_solution(title, content, ticket.ai_summary or ticket.subject)
                except Exception:
                    kb_steps = content[:300]

    draft, tone = await llm.generate_draft_reply(
        masked_text=ticket.description_masked or ticket.description,
        ai_summary=ticket.ai_summary or ticket.subject,
        intent=ticket.intent or "complaint",
        emotion_type=ticket.emotion_type or "neutral",
        emotion_score=ticket.emotion_score or 5.0,
        customer_tier=ticket.customer_tier,
        is_churn_risk=ticket.is_churn_risk,
        kb_steps=kb_steps,
    )

    filtered_draft, flags = apply_policy_filter(draft)
    confidence = 0.85 if not flags else 0.65

    # Cache draft on ticket
    ticket.ai_draft_reply = filtered_draft
    ticket.ai_draft_confidence = confidence
    db.commit()

    # Audit
    db.add(AuditLog(
        ticket_id=ticket.id,
        agent_id=payload.agent_id,
        action="reply_generated",
        slm_raw_output=draft[:2000],
        slm_final_output=filtered_draft[:2000],
        policy_flags=",".join(flags),
    ))
    db.commit()

    return DraftReplyOut(
        draft=filtered_draft,
        confidence=confidence,
        tone_applied=tone,
        policy_flags=flags,
        low_confidence=confidence < 0.72,
    )


async def _enrich_ticket(ticket_id: int, subject: str, description: str, customer_tier: str):
    """Background task to run AI pipeline on a new ticket."""
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return
        result = await pipeline.process_ticket(subject, description, customer_tier, run_llm=True)
        _apply_pipeline_result(db, ticket, result)
        db.commit()
    except Exception as e:
        print(f"Pipeline error for ticket {ticket_id}: {e}")
    finally:
        db.close()


def _apply_pipeline_result(db, ticket: Ticket, result: dict):
    ticket.description_masked = result.get("masked_text")
    ticket.emotion_type = result.get("emotion_type")
    ticket.emotion_score = result.get("emotion_score")
    ticket.intent = result.get("intent")
    ticket.urgency_score = result.get("urgency_score")
    ticket.is_churn_risk = result.get("is_churn_risk", False)
    ticket.is_escalated = result.get("is_escalated", False)
    ticket.requires_human = result.get("requires_human", False)
    ticket.severity = result.get("severity")
    ticket.sla_deadline = result.get("sla_deadline")
    ticket.product_area = result.get("product_area")
    ticket.platform = result.get("platform")
    ticket.ai_summary = result.get("ai_summary")
    ticket.updated_at = datetime.now(timezone.utc)
