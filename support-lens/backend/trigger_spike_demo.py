import sys
import os
from datetime import datetime

from database import SessionLocal, Ticket
from spike_alerter import run_spike_check

print("="*60)
print("  Triggering Live Spike Alerter Demo (Direct DB Insert)")
print("="*60)

db = SessionLocal()
now = datetime.utcnow()

# Insert 6 fake tickets directly to bypass the slow LLM pipeline
for i in range(1, 7):
    print(f"[1/2] Inserting Ticket {i}/6 directly to DB...")
    t = Ticket(
        subject=f"URGENT: Billing API is down (Report #{i})",
        description="Our checkout is failing with 500 errors. Fix immediately.",
        customer_name=f"Enterprise {i}",
        customer_email=f"ceo{i}@enterprise.com",
        customer_tier="premium",
        source="web",
        status="open",
        product_area="Billing",
        urgency_score=80.0,
        emotion_score=9.0,
        emotion_type="angry",
        created_at=now,
        updated_at=now
    )
    db.add(t)

db.commit()
db.close()

print("\n[2/2] Running APScheduler spike detection background job manually...")
run_spike_check()

print("\n✅ Done! Switch back to the UI:")
print("   Check the Data Sources or Manager Dashboard pages to see the RED ALERT banner!")
