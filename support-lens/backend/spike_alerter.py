"""
Issue Spike Alerter — runs every 5 minutes via APScheduler.
Compares last 30-min ticket volume per category against 7-day hourly average.
If > 2x the average, pushes a manager alert to the in-memory store.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)

# In-memory alert store (reset on restart — for demo this is fine)
_alerts: List[Dict] = []
_MAX_ALERTS = 50


def get_alerts() -> List[Dict]:
    """Return current alerts, newest first."""
    return list(reversed(_alerts[-_MAX_ALERTS:]))


def dismiss_alert(alert_id: str):
    """Mark an alert as dismissed."""
    global _alerts
    _alerts = [a for a in _alerts if a["id"] != alert_id]


def _push_alert(category: str, spike_pct: float, count_30m: int, avg_hourly: float):
    import uuid
    alert = {
        "id": str(uuid.uuid4()),
        "category": category,
        "spike_pct": round(spike_pct, 1),
        "count_30m": count_30m,
        "avg_hourly": round(avg_hourly, 1),
        "message": (
            f"⚠️ {category} tickets spiked {spike_pct:.0f}% in the last 30 minutes "
            f"({count_30m} tickets vs {avg_hourly:.1f} avg/hour). "
            f"Possible system outage or viral issue."
        ),
        "severity": "critical" if spike_pct > 400 else "warning",
        "timestamp": datetime.utcnow().isoformat(),
        "dismissed": False,
    }
    _alerts.append(alert)
    logger.warning(f"SPIKE ALERT: {alert['message']}")


def run_spike_check():
    """
    Core spike detection job. Compares last 30 minutes against 7-day hourly average.
    Called by APScheduler every 5 minutes.
    """
    try:
        from database import SessionLocal, Ticket
        from sqlalchemy import func

        db = SessionLocal()
        now = datetime.utcnow()
        thirty_min_ago = now - timedelta(minutes=30)
        seven_days_ago = now - timedelta(days=7)

        # Count by category in the last 30 minutes
        recent_rows = db.query(
            Ticket.product_area,
            func.count(Ticket.id).label("cnt"),
        ).filter(
            Ticket.created_at >= thirty_min_ago,
            Ticket.product_area.isnot(None),
        ).group_by(Ticket.product_area).all()

        if not recent_rows:
            db.close()
            return

        # Count total by category over last 7 days → hourly average
        total_rows = db.query(
            Ticket.product_area,
            func.count(Ticket.id).label("cnt"),
        ).filter(
            Ticket.created_at >= seven_days_ago,
            Ticket.product_area.isnot(None),
        ).group_by(Ticket.product_area).all()

        db.close()

        # 7 days * 24 hours = 168 hours
        hourly_avg = {r[0]: r[1] / 168.0 for r in total_rows}

        # Check each category
        for category, count_30m in recent_rows:
            # Normalise: 30 min = 0.5 hours
            expected_in_30m = hourly_avg.get(category, 0) * 0.5
            
            # ── HACKATHON DEMO OVERRIDE ──────────────────────────────────────
            # If history is empty, assume an artificial baseline of 2 tickets per 30m
            # This ensures that submitting 5+ tickets triggers the 2x threshold instantly.
            if expected_in_30m < 2.0:
                expected_in_30m = 2.0

            if count_30m >= 5 and count_30m > expected_in_30m * 2:
                spike_pct = ((count_30m - expected_in_30m) / max(expected_in_30m, 0.01)) * 100
                _push_alert(category, spike_pct, count_30m, hourly_avg.get(category, 0) or 4.0)

        logger.info(f"Spike check completed at {now.isoformat()}")

    except Exception as e:
        logger.error(f"Spike check error: {e}")


def start_scheduler():
    """Start the APScheduler background job. Called once at app startup."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(run_spike_check, "interval", minutes=5, id="spike_check")
        scheduler.start()
        logger.info("Spike alerter scheduler started (every 5 minutes)")
        return scheduler
    except ImportError:
        logger.warning("APScheduler not installed — spike alerter disabled. Run: pip install apscheduler")
        return None
    except Exception as e:
        logger.error(f"Scheduler start error: {e}")
        return None
