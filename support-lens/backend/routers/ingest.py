"""
Ingest router — exposes all data source ingestion as API endpoints.
All endpoints are async and return a summary of what was ingested.

Endpoints:
  POST /ingest/reddit          → scrape Reddit subreddits
  POST /ingest/appstore        → scrape App Store reviews  
  POST /ingest/email           → fetch unread IMAP emails
  GET  /ingest/status          → last run timestamps + counts
"""
import logging
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Simple in-memory status tracker
_status = {
    "reddit": {"last_run": None, "last_count": 0, "status": "never"},
    "appstore": {"last_run": None, "last_count": 0, "status": "never"},
    "email": {"last_run": None, "last_count": 0, "status": "never"},
}


class RedditIngestRequest(BaseModel):
    subreddits: list[str] = ["stripe", "techsupport", "softwaregore"]
    limit_per_sub: int = 20


class AppStoreIngestRequest(BaseModel):
    apple_app_id: Optional[str] = None   # e.g. "1232780281" for Notion
    google_app_id: Optional[str] = None  # e.g. "notion.id"
    country: str = "us"


class EmailIngestRequest(BaseModel):
    max_emails: int = 20


@router.get("/status")
def get_ingest_status():
    """Returns the last ingestion run details for all sources."""
    return _status


@router.post("/reddit")
async def ingest_reddit(payload: RedditIngestRequest, background_tasks: BackgroundTasks):
    """
    Trigger Reddit ingestion.
    Scrapes the given subreddits and creates tickets from complaints.
    """
    background_tasks.add_task(_run_reddit, payload.subreddits, payload.limit_per_sub)
    return {"message": f"Reddit ingestion started for: {payload.subreddits}", "status": "queued"}


@router.post("/appstore")
async def ingest_appstore(payload: AppStoreIngestRequest, background_tasks: BackgroundTasks):
    """
    Trigger App Store review ingestion.
    Pulls 1-2 star reviews from Apple and/or Google Play.
    """
    if not payload.apple_app_id and not payload.google_app_id:
        raise HTTPException(status_code=400, detail="Provide at least one of: apple_app_id or google_app_id")
    background_tasks.add_task(_run_appstore, payload.apple_app_id, payload.google_app_id, payload.country)
    return {"message": "App Store ingestion started", "status": "queued"}


@router.post("/email")
async def ingest_email(payload: EmailIngestRequest, background_tasks: BackgroundTasks):
    """
    Trigger Email IMAP ingestion.
    Fetches unread emails from configured inbox and creates tickets.
    Requires EMAIL_ADDRESS and EMAIL_APP_PASSWORD in backend/.env
    """
    background_tasks.add_task(_run_email, payload.max_emails)
    return {"message": "Email ingestion started", "status": "queued"}


# ── Background task runners ────────────────────────────────────────────────────

def _run_reddit(subreddits: list, limit: int):
    _status["reddit"]["status"] = "running"
    try:
        from scrapers.reddit_scraper import fetch_reddit_tickets, ingest_reddit_to_db
        all_tickets = []
        for sub in subreddits:
            all_tickets.extend(fetch_reddit_tickets(sub, limit=limit))
        count = ingest_reddit_to_db(all_tickets)
        _status["reddit"] = {"last_run": datetime.utcnow().isoformat(), "last_count": count, "status": "ok"}
        logger.info(f"Reddit ingest done: {count} tickets created")
    except Exception as e:
        _status["reddit"]["status"] = f"error: {e}"
        logger.error(f"Reddit ingest error: {e}")


def _run_appstore(apple_id: Optional[str], google_id: Optional[str], country: str):
    _status["appstore"]["status"] = "running"
    try:
        from scrapers.appstore_scraper import fetch_apple_reviews, fetch_google_play_reviews, ingest_reviews_to_db
        all_reviews = []
        if apple_id:
            all_reviews.extend(fetch_apple_reviews(apple_id, country=country))
        if google_id:
            all_reviews.extend(fetch_google_play_reviews(google_id))
        count = ingest_reviews_to_db(all_reviews)
        _status["appstore"] = {"last_run": datetime.utcnow().isoformat(), "last_count": count, "status": "ok"}
    except Exception as e:
        _status["appstore"]["status"] = f"error: {e}"
        logger.error(f"App Store ingest error: {e}")


def _run_email(max_emails: int):
    _status["email"]["status"] = "running"
    try:
        from scrapers.email_scraper import fetch_unread_emails, ingest_emails_to_db
        emails = fetch_unread_emails(max_emails=max_emails)
        count = ingest_emails_to_db(emails)
        _status["email"] = {"last_run": datetime.utcnow().isoformat(), "last_count": count, "status": "ok"}
    except Exception as e:
        _status["email"]["status"] = f"error: {e}"
        logger.error(f"Email ingest error: {e}")
