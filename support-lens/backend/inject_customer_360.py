import sys
import os
from datetime import datetime, timedelta

# Add backend to path so we can import modules
sys.path.append(os.path.abspath("support-lens/backend"))

from database import SessionLocal, Ticket

def inject_history():
    db = SessionLocal()
    now = datetime.utcnow()
    email = "ceo@enterprise.com"
    name = "Emily Chen"
    
    # Check if we already have it
    existing = db.query(Ticket).filter(Ticket.customer_email == email).count()
    if existing > 0:
        print(f"History already exists for {email} ({existing} tickets). Skipping.")
        db.close()
        return

    print("Injecting historical tickets for Customer 360 demo...")

    # 1. 3 months ago: Onboarding (Happy)
    t1 = Ticket(
        subject="Thanks for the smooth onboarding!",
        description="Just wanted to say the platform is amazing and our team is loving it.",
        customer_name=name, customer_email=email, customer_tier="enterprise",
        source="email", status="resolved",
        emotion_type="happy", emotion_score=1.2,
        intent="praise", urgency_score=5.0, is_churn_risk=False,
        product_area="Onboarding", platform="Web",
        created_at=now - timedelta(days=90), updated_at=now - timedelta(days=89)
    )

    # 2. 1 month ago: Small bug (Neutral/Worried)
    t2 = Ticket(
        subject="Minor issue with CSV exports",
        description="The CSV export seems to drop the last column occasionally. Not a huge deal but would be nice to have fixed.",
        customer_name=name, customer_email=email, customer_tier="enterprise",
        source="email", status="resolved",
        emotion_type="worried", emotion_score=4.5,
        intent="bug", urgency_score=25.0, is_churn_risk=False,
        product_area="Exports", platform="Web",
        created_at=now - timedelta(days=30), updated_at=now - timedelta(days=28)
    )

    # 3. 2 days ago: Billing problem (Frustrated)
    t3 = Ticket(
        subject="Double charged for our monthly subscription",
        description="I'm looking at our credit card statement and we were charged twice this month. Please refund the duplicate charge ASAP.",
        customer_name=name, customer_email=email, customer_tier="enterprise",
        source="email", status="resolved",
        emotion_type="frustrated", emotion_score=7.8,
        intent="billing", urgency_score=65.0, is_churn_risk=True,
        product_area="Billing", platform="Web",
        created_at=now - timedelta(days=2), updated_at=now - timedelta(days=1)
    )

    # 4. CURRENT: Total outage (Angry)
    t4 = Ticket(
        subject="URGENT: Checkout API is completely down",
        description="This is completely unacceptable. We are losing thousands of dollars an hour because your API is returning 500s. We need someone on this immediately or we are cancelling our contract.",
        customer_name=name, customer_email=email, customer_tier="enterprise",
        source="email", status="open",
        emotion_type="angry", emotion_score=9.5,
        intent="outage", urgency_score=98.0, is_churn_risk=True, is_escalated=True,
        product_area="API", platform="Web",
        created_at=now, updated_at=now
    )

    db.add_all([t1, t2, t3, t4])
    db.commit()
    db.close()
    print(f"Successfully injected 4 tickets for {email}")

if __name__ == "__main__":
    inject_history()
