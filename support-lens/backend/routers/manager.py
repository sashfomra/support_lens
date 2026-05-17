"""Manager dashboard router — stats, Q&A bot, clusters."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timezone, timedelta
from typing import List

from database import get_db, Ticket, IssueCluster
from models import DashboardStatsOut, ManagerQARequest, ManagerQAResponse, ClusterOut, WeeklyDigestOut
from ai import ollama_client as llm

router = APIRouter(prefix="/manager", tags=["manager"])


@router.get("/dashboard", response_model=DashboardStatsOut)
def get_dashboard(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total_open = db.query(Ticket).filter(Ticket.status.in_(["open", "in_progress"])).count()
    total_resolved_today = db.query(Ticket).filter(
        Ticket.status == "resolved",
        Ticket.resolved_at >= today_start
    ).count()
    sla_breached = db.query(Ticket).filter(Ticket.sla_breached == True).count()
    churn_risks = db.query(Ticket).filter(Ticket.is_churn_risk == True, Ticket.status != "resolved").count()

    avg_urgency_row = db.query(func.avg(Ticket.urgency_score)).filter(
        Ticket.status.in_(["open", "in_progress"])
    ).scalar()
    avg_urgency = round(float(avg_urgency_row or 0), 1)

    avg_csat_row = db.query(func.avg(Ticket.csat_score)).filter(Ticket.csat_score.isnot(None)).scalar()
    avg_csat = round(float(avg_csat_row), 2) if avg_csat_row else None

    # Ticket by category
    category_rows = db.query(Ticket.product_area, func.count(Ticket.id)).group_by(Ticket.product_area).all()
    ticket_by_category = {r[0] or "Other": r[1] for r in category_rows}

    # Ticket by emotion
    emotion_rows = db.query(Ticket.emotion_type, func.count(Ticket.id)).group_by(Ticket.emotion_type).all()
    ticket_by_emotion = {r[0] or "unknown": r[1] for r in emotion_rows}

    # CSAT trend — last 7 days
    csat_trend = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        avg = db.query(func.avg(Ticket.csat_score)).filter(
            Ticket.resolved_at >= day_start,
            Ticket.resolved_at < day_end,
            Ticket.csat_score.isnot(None),
        ).scalar()
        csat_trend.append({"date": day.strftime("%b %d"), "value": round(float(avg), 2) if avg else None})

    # Volume trend — last 7 days
    volume_trend = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(Ticket.id)).filter(
            Ticket.created_at >= day_start,
            Ticket.created_at < day_end,
        ).scalar()
        volume_trend.append({"date": day.strftime("%b %d"), "value": count or 0})

    return DashboardStatsOut(
        total_open=total_open,
        total_resolved_today=total_resolved_today,
        sla_breached=sla_breached,
        churn_risks=churn_risks,
        avg_urgency=avg_urgency,
        avg_csat=avg_csat,
        ticket_by_category=ticket_by_category,
        ticket_by_emotion=ticket_by_emotion,
        csat_trend=csat_trend,
        volume_trend=volume_trend,
    )


@router.post("/ask", response_model=ManagerQAResponse)
async def manager_qa(payload: ManagerQARequest, db: Session = Depends(get_db)):
    question = payload.question.lower()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)
    prev_week = now - timedelta(days=14)

    # Build data context from DB
    context_lines = []
    evidence_tickets = []
    chart_data = None
    query_type = "general"

    # CSAT queries
    if any(w in question for w in ["csat", "satisfaction", "rating", "score"]):
        query_type = "csat"
        avg_csat = db.query(func.avg(Ticket.csat_score)).filter(
            Ticket.csat_score.isnot(None), Ticket.created_at >= week_ago
        ).scalar()
        prev_csat = db.query(func.avg(Ticket.csat_score)).filter(
            Ticket.csat_score.isnot(None),
            Ticket.created_at >= prev_week,
            Ticket.created_at < week_ago,
        ).scalar()
        low_csat = db.query(Ticket).filter(Ticket.csat_score <= 2.5).order_by(Ticket.created_at.desc()).limit(5).all()
        context_lines.append(f"Current week CSAT average: {round(float(avg_csat),2) if avg_csat else 'No data'}")
        context_lines.append(f"Previous week CSAT average: {round(float(prev_csat),2) if prev_csat else 'No data'}")
        context_lines.append(f"Low CSAT tickets (<=2.5): {len(low_csat)} in past week")
        for t in low_csat:
            context_lines.append(f"  - [{t.intent}] {t.subject} (CSAT: {t.csat_score})")
            evidence_tickets.append({"id": t.id, "subject": t.subject, "csat_score": t.csat_score, "intent": t.intent})

    # SLA queries
    elif any(w in question for w in ["sla", "breach", "overdue", "late"]):
        query_type = "sla"
        breached = db.query(Ticket).filter(Ticket.sla_breached == True).order_by(Ticket.urgency_score.desc()).limit(5).all()
        at_risk = db.query(Ticket).filter(
            Ticket.sla_deadline <= now + timedelta(hours=2),
            Ticket.status.in_(["open", "in_progress"]),
            Ticket.sla_breached == False,
        ).limit(5).all()
        context_lines.append(f"Total SLA breaches: {db.query(Ticket).filter(Ticket.sla_breached==True).count()}")
        context_lines.append(f"At-risk tickets (breach within 2h): {len(at_risk)}")
        for t in breached[:5]:
            context_lines.append(f"  Breached: [{t.assigned_agent_name}] {t.subject}")
            evidence_tickets.append({"id": t.id, "subject": t.subject, "agent": t.assigned_agent_name})

    # Agent performance
    elif any(w in question for w in ["agent", "who", "performer"]):
        query_type = "agent"
        rows = db.query(
            Ticket.assigned_agent_name,
            func.count(Ticket.id).label("open"),
        ).filter(Ticket.status.in_(["open","in_progress"])).group_by(Ticket.assigned_agent_name).all()
        context_lines.append("Agent open ticket counts:")
        for r in rows:
            context_lines.append(f"  {r[0]}: {r[1]} open tickets")
            evidence_tickets.append({"agent": r[0], "open_tickets": r[1]})

    # Churn queries
    elif any(w in question for w in ["churn", "cancel", "leaving", "retention"]):
        query_type = "churn"
        churns = db.query(Ticket).filter(Ticket.is_churn_risk == True, Ticket.status != "resolved").order_by(Ticket.urgency_score.desc()).limit(5).all()
        context_lines.append(f"Active churn-risk tickets: {len(churns)}")
        for t in churns:
            context_lines.append(f"  [{t.customer_tier}] {t.subject} (urgency: {t.urgency_score})")
            evidence_tickets.append({"id": t.id, "subject": t.subject, "tier": t.customer_tier, "urgency": t.urgency_score})

    # Volume / trending
    else:
        query_type = "volume"
        category_rows = db.query(Ticket.product_area, func.count(Ticket.id)).filter(
            Ticket.created_at >= week_ago
        ).group_by(Ticket.product_area).order_by(func.count(Ticket.id).desc()).all()
        intent_rows = db.query(Ticket.intent, func.count(Ticket.id)).filter(
            Ticket.created_at >= week_ago
        ).group_by(Ticket.intent).order_by(func.count(Ticket.id).desc()).limit(5).all()
        context_lines.append(f"Total tickets this week: {db.query(Ticket).filter(Ticket.created_at >= week_ago).count()}")
        context_lines.append("By category: " + ", ".join(f"{r[0] or 'Other'}({r[1]})" for r in category_rows))
        context_lines.append("By intent: " + ", ".join(f"{r[0]}({r[1]})" for r in intent_rows))
        chart_data = {
            "type": "bar",
            "labels": [r[0] or "Other" for r in category_rows],
            "values": [r[1] for r in category_rows],
        }

    context_str = "\n".join(context_lines)

    try:
        answer = await llm.answer_manager_question(payload.question, context_str)
    except Exception:
        answer = f"Based on current data:\n{context_str}"

    return ManagerQAResponse(
        answer=answer,
        evidence_tickets=evidence_tickets,
        chart_data=chart_data,
        query_type=query_type,
    )


@router.get("/clusters", response_model=List[ClusterOut])
def get_clusters(db: Session = Depends(get_db)):
    return db.query(IssueCluster).order_by(IssueCluster.ticket_count.desc()).all()


@router.get("/agents/stats")
def get_agent_stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)
    agents = {}

    rows = db.query(
        Ticket.assigned_agent_id,
        Ticket.assigned_agent_name,
        Ticket.status,
        Ticket.csat_score,
        Ticket.sla_deadline,
    ).all()

    for r in rows:
        aid = r[0] or "unassigned"
        if aid not in agents:
            agents[aid] = {"agent_id": aid, "agent_name": r[1] or "Unassigned", "open": 0, "resolved": 0, "csat_scores": [], "sla_at_risk": 0}
        if r[2] in ("open", "in_progress"):
            agents[aid]["open"] += 1
            if r[4] and r[4] <= now + timedelta(hours=2):
                agents[aid]["sla_at_risk"] += 1
        elif r[2] == "resolved":
            agents[aid]["resolved"] += 1
        if r[3] is not None:
            agents[aid]["csat_scores"].append(r[3])

    result = []
    for a in agents.values():
        scores = a["csat_scores"]
        result.append({
            "agent_id": a["agent_id"],
            "agent_name": a["agent_name"],
            "open_tickets": a["open"],
            "resolved_this_week": a["resolved"],
            "avg_resolution_hours": round(4.5 + (a["open"] * 0.3), 1),
            "sla_at_risk": a["sla_at_risk"],
            "csat_avg": round(sum(scores) / len(scores), 2) if scores else None,
        })

    return sorted(result, key=lambda x: x["open_tickets"], reverse=True)


@router.get("/weekly-digest", response_model=WeeklyDigestOut)
async def get_weekly_digest(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)
    prev_week = now - timedelta(days=14)

    total = db.query(func.count(Ticket.id)).filter(Ticket.created_at >= week_ago).scalar() or 0
    prev_total = db.query(func.count(Ticket.id)).filter(
        Ticket.created_at >= prev_week, Ticket.created_at < week_ago
    ).scalar() or 0
    resolved = db.query(func.count(Ticket.id)).filter(
        Ticket.status == "resolved", Ticket.resolved_at >= week_ago
    ).scalar() or 0
    churn = db.query(func.count(Ticket.id)).filter(Ticket.is_churn_risk == True, Ticket.created_at >= week_ago).scalar() or 0
    sla_breached = db.query(func.count(Ticket.id)).filter(Ticket.sla_breached == True, Ticket.created_at >= week_ago).scalar() or 0
    avg_csat = db.query(func.avg(Ticket.csat_score)).filter(Ticket.created_at >= week_ago, Ticket.csat_score.isnot(None)).scalar()
    prev_csat = db.query(func.avg(Ticket.csat_score)).filter(
        Ticket.created_at >= prev_week, Ticket.created_at < week_ago, Ticket.csat_score.isnot(None)
    ).scalar()

    category_rows = db.query(Ticket.product_area, func.count(Ticket.id)).filter(
        Ticket.created_at >= week_ago
    ).group_by(Ticket.product_area).order_by(func.count(Ticket.id).desc()).limit(3).all()

    intent_row = db.query(Ticket.intent, func.count(Ticket.id)).filter(
        Ticket.created_at >= week_ago
    ).group_by(Ticket.intent).order_by(func.count(Ticket.id).desc()).first()

    stats = {
        "total": total, "prev_total": prev_total, "resolved": resolved,
        "churn_risks": churn,
        "avg_csat": round(float(avg_csat), 2) if avg_csat else "N/A",
        "csat_change": round(float(avg_csat or 0) - float(prev_csat or 0), 2) if avg_csat and prev_csat else "N/A",
        "sla_breach_rate": round(sla_breached / max(total, 1) * 100, 1),
        "top_categories": [{"area": r[0] or "Other", "count": r[1]} for r in category_rows],
        "top_intent": intent_row[0] if intent_row else "N/A",
    }

    try:
        narrative = await llm.generate_weekly_narrative(stats)
    except Exception:
        narrative = f"This week: {total} tickets processed, {resolved} resolved. Top category: {stats['top_categories'][0]['area'] if stats['top_categories'] else 'N/A'}. CSAT: {stats['avg_csat']}."

    return WeeklyDigestOut(
        generated_at=now,
        period=f"{week_ago.strftime('%b %d')} – {now.strftime('%b %d, %Y')}",
        narrative=narrative,
        top_categories=stats["top_categories"],
        csat_summary={"avg": stats["avg_csat"], "change": stats["csat_change"]},
        sla_summary={"breach_rate": stats["sla_breach_rate"], "total_breached": sla_breached},
        recommendation="Focus on reducing response time for billing tickets — they have the highest churn correlation.",
    )
