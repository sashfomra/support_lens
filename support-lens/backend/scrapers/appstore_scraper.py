"""
App Store Review Scraper — pulls 1-star and 2-star reviews from:
  - Apple App Store (iTunes public RSS feed — no auth needed)
  - Google Play Store (google-play-scraper package)

Converts low-rated reviews into SupportLens tickets automatically.
"""
import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict

logger = logging.getLogger(__name__)


def fetch_apple_reviews(app_id: str, country: str = "us", max_pages: int = 3) -> List[Dict]:
    """
    Fetch Apple App Store reviews using the public iTunes RSS endpoint.
    No API key required. Returns list of low-rated (<=2 star) reviews.
    
    app_id: The numeric App Store ID (visible in the app's App Store URL)
    Example: Notion = 1232780281, Stripe Dashboard = 978516833
    """
    reviews = []
    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "SupportLens/1.0"})
            if resp.status_code != 200:
                break
            data = resp.json()
            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                break

            for entry in entries:
                # Skip the first entry if it is the app metadata
                if "im:rating" not in entry:
                    continue
                rating = int(entry.get("im:rating", {}).get("label", "5"))
                if rating <= 2:
                    reviews.append({
                        "source": "apple_appstore",
                        "subject": entry.get("title", {}).get("label", "App Store Review"),
                        "description": entry.get("content", {}).get("label", ""),
                        "rating": rating,
                        "customer_name": entry.get("author", {}).get("name", {}).get("label", "App User"),
                        "customer_email": f"appstore_{entry.get('id', {}).get('label', 'unknown')}@reviews.local",
                        "customer_tier": "standard",
                    })
        except Exception as e:
            logger.error(f"Apple App Store fetch error (page {page}): {e}")
            break

    logger.info(f"Apple App Store: fetched {len(reviews)} low-rated reviews for app {app_id}")
    return reviews


def fetch_google_play_reviews(app_id: str, count: int = 100) -> List[Dict]:
    """
    Fetch Google Play reviews using the google-play-scraper package.
    No API key required.
    Install: pip install google-play-scraper
    
    app_id: Package name e.g. 'notion.id' or 'com.stripe.android.dashboard'
    """
    try:
        from google_play_scraper import reviews, Sort
        result, _ = reviews(
            app_id,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=count,
            filter_score_with=None,
        )
        low_rated = []
        for r in result:
            if r.get("score", 5) <= 2:
                low_rated.append({
                    "source": "google_play",
                    "subject": r.get("title") or f"Play Store Review — {r.get('score')} stars",
                    "description": r.get("content", ""),
                    "rating": r.get("score", 0),
                    "customer_name": r.get("userName", "Play User"),
                    "customer_email": f"play_{r.get('reviewId', 'unknown')}@reviews.local",
                    "customer_tier": "standard",
                })
        logger.info(f"Google Play: fetched {len(low_rated)} low-rated reviews for {app_id}")
        return low_rated
    except ImportError:
        logger.warning("google-play-scraper not installed. Run: pip install google-play-scraper")
        return []
    except Exception as e:
        logger.error(f"Google Play fetch error: {e}")
        return []


def ingest_reviews_to_db(reviews_list: List[Dict]) -> int:
    """Insert fetched reviews as tickets into the SupportLens database."""
    if not reviews_list:
        return 0

    from database import SessionLocal, Ticket
    from ai.pipeline import detect_emotion, detect_intent, detect_churn_risk, compute_urgency_score
    from datetime import timedelta
    import random

    db = SessionLocal()
    created = 0
    now = datetime.utcnow()

    try:
        for r in reviews_list:
            # Check for exact duplicates by email
            existing = db.query(Ticket).filter(Ticket.customer_email == r["customer_email"]).first()
            if existing:
                continue

            text = f"{r['subject']}. {r['description']}"
            emotion_type, emotion_score = detect_emotion(r["description"])
            intent = detect_intent(r["description"])
            churn = detect_churn_risk(r["description"])
            severity = "P1" if r["rating"] == 1 else "P2"
            sla_h = 4 if severity == "P1" else 12
            urgency = compute_urgency_score(
                emotion_score=emotion_score,
                emotion_type=emotion_type,
                is_churn_risk=churn,
                customer_tier="standard",
                intent=intent,
                sla_hours_remaining=sla_h,
                keyword_severity=severity,
            )

            ticket = Ticket(
                subject=r["subject"][:200],
                description=r["description"][:2000],
                customer_name=r["customer_name"],
                customer_email=r["customer_email"],
                customer_tier=r["customer_tier"],
                source=r["source"],
                status="open",
                emotion_type=emotion_type,
                emotion_score=emotion_score,
                intent=intent,
                urgency_score=urgency,
                is_churn_risk=churn,
                is_escalated=churn or r["rating"] == 1,
                requires_human=r["rating"] == 1,
                severity=severity,
                sla_deadline=now + timedelta(hours=sla_h),
                sla_breached=False,
                product_area="App Store",
                platform="iOS" if r["source"] == "apple_appstore" else "Android",
                created_at=now,
                updated_at=now,
            )
            db.add(ticket)
            created += 1

        db.commit()
        logger.info(f"App Store Scraper: inserted {created} new tickets")
    except Exception as e:
        db.rollback()
        logger.error(f"DB insert error: {e}")
    finally:
        db.close()

    return created
