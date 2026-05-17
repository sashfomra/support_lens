"""Seed the database with KB articles and synthetic tickets."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from database import create_tables, SessionLocal, Ticket, KBArticle, AuditLog, IssueCluster
from data.seed_data import KB_ARTICLES, TICKETS, AGENTS
from ai.pipeline import (
    detect_emotion, detect_intent, detect_churn_risk,
    compute_urgency_score, requires_human_escalation,
    SLA_HOURS,
)
from ai.pii_masker import mask_pii


def seed(db: Session):
    # Check already seeded
    if db.query(Ticket).count() > 0:
        print("Database already seeded — skipping.")
        return

    print("Seeding KB articles...")
    kb_map = {}
    for art_data in KB_ARTICLES:
        art = KBArticle(**art_data)
        db.add(art)
        db.flush()
        kb_map[art.title] = art.id
    db.commit()
    print(f"  OK {len(KB_ARTICLES)} KB articles")

    print("Seeding tickets (with AI enrichment — no LLM, rule-based only)...")
    now = datetime.now(timezone.utc)

    for i, t_data in enumerate(TICKETS):
        agent = random.choice(AGENTS)
        text = f"{t_data['subject']}. {t_data['description']}"
        masked, pii = mask_pii(text)

        emotion_type, emotion_score = detect_emotion(t_data["description"])
        intent = detect_intent(t_data["description"])
        churn = detect_churn_risk(t_data["description"]) or intent == "churn"
        severity = "P1" if emotion_score >= 8 or churn else "P2" if emotion_score >= 5 else "P3"
        sla_h = SLA_HOURS.get(severity, 24)

        # Spread tickets over last 14 days
        offset_hours = random.randint(0, 14 * 24)
        created = now - timedelta(hours=offset_hours)
        sla_deadline = created + timedelta(hours=sla_h)
        sla_breached = sla_deadline < now and random.random() > 0.5

        urgency = compute_urgency_score(
            emotion_score=emotion_score,
            emotion_type=emotion_type,
            is_churn_risk=churn,
            customer_tier=t_data.get("customer_tier", "standard"),
            intent=intent,
            sla_hours_remaining=max(0, (sla_deadline - now).total_seconds() / 3600),
            keyword_severity=severity,
        )

        status = random.choice(["open", "open", "open", "in_progress", "resolved"])
        resolved_at = None
        if status == "resolved":
            resolved_at = created + timedelta(hours=random.randint(1, sla_h))

        csat = None
        if status == "resolved":
            # Angry customers give lower CSAT
            if emotion_score >= 7:
                csat = round(random.uniform(1.5, 3.5), 1)
            elif emotion_score >= 5:
                csat = round(random.uniform(2.5, 4.5), 1)
            else:
                csat = round(random.uniform(3.5, 5.0), 1)

        product_areas = ["Billing", "Login", "Performance", "UX", "Feature", "Other"]
        platforms = ["Android", "iOS", "Web", "API"]

        ticket = Ticket(
            subject=t_data["subject"],
            description=t_data["description"],
            description_masked=masked,
            customer_name=t_data.get("customer_name"),
            customer_email=t_data.get("customer_email"),
            customer_tier=t_data.get("customer_tier", "standard"),
            source=t_data.get("source", "ticket"),
            status=status,
            emotion_type=emotion_type,
            emotion_score=emotion_score,
            intent=intent,
            urgency_score=urgency,
            is_churn_risk=churn,
            is_escalated=churn or emotion_score >= 8,
            requires_human=requires_human_escalation(churn, emotion_score, intent, t_data.get("customer_tier","standard"), t_data["description"]),
            severity=severity,
            sla_deadline=sla_deadline,
            sla_breached=sla_breached,
            product_area=random.choice(product_areas),
            platform=random.choice(platforms),
            assigned_agent_id=agent["id"],
            assigned_agent_name=agent["name"],
            created_at=created,
            updated_at=created,
            resolved_at=resolved_at,
            csat_score=csat,
            ai_summary=f"Issue: {t_data['subject']}\nCustomer wants: Resolution\nTried: Check account settings",
        )
        db.add(ticket)

    db.commit()
    print(f"  OK {len(TICKETS)} tickets")

    # Seed some issue clusters
    clusters = [
        {"label": "Payment failures on Android v4.2", "ticket_count": 12, "description": "128 tickets this period share the root cause: Payment failure following the v4.2 Android app update."},
        {"label": "Login lockouts — 2FA related", "ticket_count": 8, "description": "Multiple users locked out after enabling 2FA. Linked to authenticator time-sync issue."},
        {"label": "Performance degradation — web platform", "ticket_count": 15, "description": "Spike in slow-load complaints across the web platform, starting May 13."},
        {"label": "Subscription cancellation — pricing", "ticket_count": 6, "description": "Churn cluster: customers citing competitor pricing as primary reason."},
    ]
    for c in clusters:
        now_dt = datetime.now(timezone.utc)
        cluster = IssueCluster(
            label=c["label"],
            description=c["description"],
            ticket_count=c["ticket_count"],
            date_window="2026-05-09_to_2026-05-16",
            created_at=now_dt,
        )
        db.add(cluster)
    db.commit()
    print(f"  OK {len(clusters)} issue clusters")
    print("Seeding complete.")


if __name__ == "__main__":
    create_tables()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
