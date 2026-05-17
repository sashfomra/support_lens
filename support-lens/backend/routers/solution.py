"""Solution API router — /api/solution and /api/solution/feedback."""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, SolutionAudit, SolutionFeedback
from solution_engine import generate_solution

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/solution", tags=["solution"])


class SolutionRequest(BaseModel):
    ticket_id: str
    summary: str
    issue_category: str
    product_name: str = "SupportLens"
    emotion_score: float = 5.0
    intent: str = "general_complaint"


class FeedbackRequest(BaseModel):
    ticket_id: str
    rating: int  # 1 = thumbs up, -1 = thumbs down
    comment: str = ""


@router.post("")
async def get_solution(payload: SolutionRequest, db: Session = Depends(get_db)):
    """Generate an AI solution using multi-source retrieval and optional SLM rewriting."""
    try:
        result = await generate_solution(
            ticket_id=payload.ticket_id,
            summary=payload.summary,
            issue_category=payload.issue_category,
            product_name=payload.product_name,
            emotion_score=payload.emotion_score,
            intent=payload.intent,
        )

        # Audit log
        audit = SolutionAudit(
            ticket_id=payload.ticket_id,
            query_used=result.get("query_used", ""),
            sources_retrieved=json.dumps(result.get("sources_used", [])),
            confidence_score=result.get("confidence_score", 0.0),
            fallback_flag=result.get("fallback_flag", True),
            slm_output=result.get("solution_text") or result.get("message", ""),
            generated_at=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()

        return result

    except Exception as e:
        logger.error(f"Solution engine error: {e}", exc_info=True)
        # Never return 500 — always safe fallback
        return {
            "ticket_id": payload.ticket_id,
            "solution_text": None,
            "source_urls": [],
            "confidence_score": 0.0,
            "fallback_flag": True,
            "sources_used": [],
            "message": "Solution engine temporarily unavailable — escalating to senior agent",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    """Store agent thumbs up/down feedback on a generated solution."""
    fb = SolutionFeedback(
        ticket_id=payload.ticket_id,
        rating=payload.rating,
        comment=payload.comment,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(fb)
    db.commit()
    return {"status": "ok", "message": "Feedback recorded"}
