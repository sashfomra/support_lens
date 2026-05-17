"""Insights router — heatmap, SLA breakdown, sentiment trend, CSAT forecast."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
import random

from database import get_db, Ticket

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/heatmap")
def get_heatmap(db: Session = Depends(get_db)):
    """
    7-day x 24-hour issue volume heatmap.
    Returns list of {day, hour, count, dominant_category}
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)

    rows = db.query(
        Ticket.created_at,
        Ticket.product_area,
    ).filter(Ticket.created_at >= week_ago).all()

    # Build 7x24 grid
    grid = {}
    for row in rows:
        if not row[0]:
            continue
        day = row[0].weekday()   # 0=Mon … 6=Sun
        hour = row[0].hour
        key = (day, hour)
        if key not in grid:
            grid[key] = {"count": 0, "categories": {}}
        grid[key]["count"] += 1
        cat = row[1] or "Other"
        grid[key]["categories"][cat] = grid[key]["categories"].get(cat, 0) + 1

    result = []
    for (day, hour), data in grid.items():
        dominant = max(data["categories"], key=data["categories"].get) if data["categories"] else "Other"
        result.append({"day": day, "hour": hour, "count": data["count"], "dominant_category": dominant})

    # Fill empty cells with 0
    for day in range(7):
        for hour in range(24):
            if not any(r["day"] == day and r["hour"] == hour for r in result):
                result.append({"day": day, "hour": hour, "count": 0, "dominant_category": None})

    return sorted(result, key=lambda x: (x["day"], x["hour"]))


@router.get("/sla-breakdown")
def get_sla_breakdown(db: Session = Depends(get_db)):
    """Returns counts of tickets by SLA status per agent."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    open_tickets = db.query(Ticket).filter(Ticket.status.in_(["open", "in_progress"])).all()

    safe = []
    at_risk = []
    breached = []

    for t in open_tickets:
        if t.sla_breached:
            breached.append(t)
        elif t.sla_deadline and t.sla_deadline <= now + timedelta(hours=2):
            at_risk.append(t)
        else:
            safe.append(t)

    # Per-agent breakdown
    agent_breakdown = {}
    for t in open_tickets:
        name = t.assigned_agent_name or "Unassigned"
        if name not in agent_breakdown:
            agent_breakdown[name] = {"safe": 0, "at_risk": 0, "breached": 0}
        if t.sla_breached:
            agent_breakdown[name]["breached"] += 1
        elif t.sla_deadline and t.sla_deadline <= now + timedelta(hours=2):
            agent_breakdown[name]["at_risk"] += 1
        else:
            agent_breakdown[name]["safe"] += 1

    return {
        "totals": {"safe": len(safe), "at_risk": len(at_risk), "breached": len(breached)},
        "by_agent": [{"agent": k, **v} for k, v in agent_breakdown.items()],
    }


@router.get("/sentiment-trend")
def get_sentiment_trend(db: Session = Depends(get_db)):
    """30-day sentiment trend by source channel."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    thirty_ago = now - timedelta(days=30)

    rows = db.query(
        Ticket.created_at,
        Ticket.source,
        Ticket.emotion_score,
    ).filter(
        Ticket.created_at >= thirty_ago,
        Ticket.emotion_score.isnot(None),
    ).all()

    # Group by day
    daily = {}
    for row in rows:
        if not row[0]:
            continue
        day_key = row[0].strftime("%Y-%m-%d")
        source = row[1] or "ticket"
        score = 10 - (row[2] or 5)  # invert: high anger = low sentiment
        if day_key not in daily:
            daily[day_key] = {}
        if source not in daily[day_key]:
            daily[day_key][source] = []
        daily[day_key][source].append(score)

    result = []
    for day in sorted(daily.keys()):
        entry = {"date": day}
        for source, scores in daily[day].items():
            entry[source] = round(sum(scores) / len(scores), 2)
        result.append(entry)

    return result


@router.get("/csat-forecast")
def get_csat_forecast(db: Session = Depends(get_db)):
    """
    Predict current period CSAT based on open ticket emotion scores
    and recent resolution speed.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)

    # Recent resolved CSAT
    recent_csat = db.query(func.avg(Ticket.csat_score)).filter(
        Ticket.resolved_at >= week_ago,
        Ticket.csat_score.isnot(None),
    ).scalar()

    # Open ticket avg emotion (high anger = lower forecast)
    avg_emotion = db.query(func.avg(Ticket.emotion_score)).filter(
        Ticket.status.in_(["open", "in_progress"]),
        Ticket.emotion_score.isnot(None),
    ).scalar() or 5.0

    # Churn risk ratio
    total_open = db.query(func.count(Ticket.id)).filter(Ticket.status.in_(["open", "in_progress"])).scalar() or 1
    churn_open = db.query(func.count(Ticket.id)).filter(
        Ticket.status.in_(["open", "in_progress"]),
        Ticket.is_churn_risk == True,
    ).scalar() or 0

    churn_penalty = (churn_open / total_open) * 0.5
    emotion_penalty = max(0, (float(avg_emotion) - 5) / 10) * 0.3

    base = float(recent_csat or 3.8)
    forecast = round(max(1.0, min(5.0, base - churn_penalty - emotion_penalty)), 2)

    prev_week_csat = db.query(func.avg(Ticket.csat_score)).filter(
        Ticket.resolved_at >= now - timedelta(days=14),
        Ticket.resolved_at < week_ago,
        Ticket.csat_score.isnot(None),
    ).scalar()

    return {
        "forecast": forecast,
        "current_actual": round(float(recent_csat), 2) if recent_csat else None,
        "prev_week": round(float(prev_week_csat), 2) if prev_week_csat else None,
        "confidence": "medium",
        "drivers": [
            {"label": "Churn risk ratio", "impact": round(-churn_penalty, 3)},
            {"label": "Avg emotion intensity", "impact": round(-emotion_penalty, 3)},
        ],
    }
