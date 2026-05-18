"""
Reddit Solution Scraper — uses PRAW to:
  1. Search for community solutions to support issues (existing)
  2. Fetch complaint posts from subreddits and ingest as tickets (new)

CREDENTIALS SETUP:
1. Go to https://www.reddit.com/prefs/apps and create an app (type: script)
2. Copy the client_id (under app name) and client_secret
3. Add to your .env file:
   REDDIT_CLIENT_ID=your_client_id_here
   REDDIT_CLIENT_SECRET=your_client_secret_here
   REDDIT_USER_AGENT=SupportLens/1.0 (by u/your_reddit_username)
"""
import os
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "SupportLens/1.0")

# Flairs considered as support issues
COMPLAINT_FLAIRS = {"bug", "issue", "help", "complaint", "problem", "broken", "not working", "error"}


def _get_reddit():
    """Create and return an authenticated Reddit instance."""
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return None
    try:
        import praw
        return praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
    except ImportError:
        logger.error("praw not installed — run: pip install praw")
        return None
    except Exception as e:
        logger.error(f"Reddit auth error: {e}")
        return None


def search_reddit_solutions(query: str, product_name: str) -> List[dict]:
    """
    Search Reddit for community solutions related to a support issue.
    Returns list of up to 3 results with post_title, post_url, top_comment_body, upvote_count.
    """
    reddit = _get_reddit()
    if not reddit:
        logger.warning("Reddit credentials not set — using HACKATHON DEMO mode for Reddit solutions")
        query_lower = query.lower()
        
        # 1. Stripe Webhook Issue
        if "webhook" in query_lower or "event" in query_lower:
            return [{
                "post_title": "Stripe webhooks not sending to my server (payment_intent.succeeded)",
                "post_url": "https://reddit.com/r/stripe/comments/demo1",
                "top_comment_body": "I had this exact issue last week. 90% of the time, this happens because you are missing the raw body in your endpoint before calling `stripe.Webhook.construct_event`. If you are using Express/Node.js, make sure you use `express.raw({type: 'application/json'})` for that specific route! Also, check your Stripe Dashboard Developer settings to confirm the webhook signature secret matches what you have in your .env file.",
                "upvote_count": 234,
                "created_utc": 1690000000,
            }]
            
        # 2. Stripe Card Declined
        elif "decline" in query_lower or "fail" in query_lower:
            return [{
                "post_title": "All payments failing with card_declined error code - HELP",
                "post_url": "https://reddit.com/r/stripe/comments/demo2",
                "top_comment_body": "If you are testing in Test Mode, make sure you are using one of the Stripe provided test cards (like the '4242' Visa). If this is Live Mode and valid cards are declining, check your Radar settings — you might have the Risk Level set too strict, which causes false positives and blocks legitimate cards. Also check if the bank is declining it due to missing CVC/ZIP code validation.",
                "upvote_count": 156,
                "created_utc": 1690000000,
            }]
            
        # 3. Stripe Subscription Cancel
        elif "cancel" in query_lower or "subscription" in query_lower:
            return [{
                "post_title": "User cancelled subscription but still got charged?",
                "post_url": "https://reddit.com/r/stripe/comments/demo3",
                "top_comment_body": "When you cancel a Stripe subscription via API, you have to pass `cancel_at_period_end=false` if you want it to cancel immediately. If you just call `stripe.subscriptions.update(id, {cancel_at_period_end: true})`, Stripe will still charge them for the current billing cycle and it will remain active until the end of the month. To refund them, you'll need to manually issue a refund on the specific Charge object.",
                "upvote_count": 489,
                "created_utc": 1690000000,
            }]
            
        # Default fallback
        return [{
            "post_title": f"How to fix {query} issue?",
            "post_url": "https://reddit.com/r/techsupport/comments/demo",
            "top_comment_body": "The best way to resolve this is to restart your local dev server, clear your browser cache, and verify your API keys are set correctly in your environment variables. If that fails, checking the server logs in your dashboard usually pinpoints the exact line causing the crash.",
            "upvote_count": 89,
            "created_utc": 1690000000,
        }]

    try:
        search_query = f"{product_name} {query}"
        logger.info(f"Searching Reddit: '{search_query}'")

        results = []
        submissions = reddit.subreddit("all").search(
            search_query,
            sort="relevance",
            time_filter="year",
            limit=10,
        )

        for sub in submissions:
            if len(results) >= 3:
                break

            top_comment = None
            try:
                sub.comments.replace_more(limit=0)
                candidates = [
                    c for c in sub.comments.list()
                    if hasattr(c, "body") and len(c.body) > 50 and c.body != "[deleted]"
                ]
                if candidates:
                    top_comment = max(candidates, key=lambda c: c.score)
            except Exception as e:
                logger.debug(f"Comment fetch error: {e}")

            results.append({
                "post_title": sub.title,
                "post_url": f"https://reddit.com{sub.permalink}",
                "top_comment_body": top_comment.body[:800] if top_comment else "",
                "upvote_count": sub.score,
                "created_utc": sub.created_utc,
            })

        logger.info(f"Reddit search returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Reddit search failed: {e}")
        return []


def fetch_reddit_tickets(subreddit_name: str, limit: int = 25) -> List[Dict]:
    """
    Fetch complaint/bug posts from a subreddit and convert them to ticket dicts.
    Uses post flair and keyword filtering to identify genuine complaints.
    """
    reddit = _get_reddit()
    tickets = []

    if not reddit:
        logger.warning("Reddit credentials missing/invalid — using HACKATHON DEMO mode for Reddit tickets")
        import uuid
        run_id = uuid.uuid4().hex[:8]
        # Generate some highly realistic simulated Reddit posts for the demo
        return [
            {
                "source": "reddit",
                "subject": f"[{subreddit_name}] Major issue with the new dashboard update",
                "description": "Ever since the update rolled out yesterday, I can't export my data. The CSV button just spins forever. Anyone else experiencing this? Our whole team is blocked right now.",
                "customer_name": "u/angry_pm_guy",
                "customer_email": f"reddit_{run_id}_1@reddit.local",
                "customer_tier": "standard",
                "reddit_url": f"https://reddit.com/r/{subreddit_name}/comments/mock1",
                "upvotes": 142,
            },
            {
                "source": "reddit",
                "subject": f"[{subreddit_name}] Billing API throwing 500s constantly",
                "description": "Is it just me or is the API completely unstable today? I'm getting 500 internal server errors on about 30% of my checkout requests. Losing money over here.",
                "customer_name": "u/dev_in_distress",
                "customer_email": f"reddit_{run_id}_2@reddit.local",
                "customer_tier": "standard",
                "reddit_url": f"https://reddit.com/r/{subreddit_name}/comments/mock2",
                "upvotes": 89,
            },
            {
                "source": "reddit",
                "subject": f"[{subreddit_name}] How do I cancel my subscription? Hidden button?",
                "description": "I've been clicking around for 20 minutes and literally cannot find the cancellation page. Are they deliberately hiding it? This feels like a dark pattern.",
                "customer_name": "u/frustrated_user99",
                "customer_email": f"reddit_{run_id}_3@reddit.local",
                "customer_tier": "standard",
                "reddit_url": f"https://reddit.com/r/{subreddit_name}/comments/mock3",
                "upvotes": 45,
            },
            {
                "source": "reddit",
                "subject": f"[{subreddit_name}] Security alert: Weird login attempts?",
                "description": "Got three emails last night about login attempts from Russia. I have 2FA enabled so they didn't get in, but how did they get my email? Is there a breach?",
                "customer_name": "u/sec_paranoid",
                "customer_email": f"reddit_{run_id}_4@reddit.local",
                "customer_tier": "standard",
                "reddit_url": f"https://reddit.com/r/{subreddit_name}/comments/mock4",
                "upvotes": 210,
            },
            {
                "source": "reddit",
                "subject": f"[{subreddit_name}] Terrible customer support response times",
                "description": "Submitted a ticket 3 days ago about a billing discrepancy and still haven't heard back. Has anyone actually had a human respond to them this week?",
                "customer_name": "u/waiting_forever",
                "customer_email": f"reddit_{run_id}_5@reddit.local",
                "customer_tier": "standard",
                "reddit_url": f"https://reddit.com/r/{subreddit_name}/comments/mock5",
                "upvotes": 334,
            }
        ]

    try:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.new(limit=limit):
            # Filter by flair or keyword in title
            flair = (post.link_flair_text or "").lower()
            title_lower = post.title.lower()
            is_complaint = (
                flair in COMPLAINT_FLAIRS or
                any(kw in title_lower for kw in ["issue", "bug", "broken", "error", "not working", "help", "problem", "fail"])
            )
            if not is_complaint:
                continue
            if not post.selftext or len(post.selftext) < 20:
                continue

            tickets.append({
                "source": "reddit",
                "subject": post.title[:200],
                "description": post.selftext[:2000],
                "customer_name": str(post.author) if post.author else "Reddit User",
                "customer_email": f"reddit_{post.id}@reddit.local",
                "customer_tier": "standard",
                "reddit_url": f"https://reddit.com{post.permalink}",
                "upvotes": post.score,
            })

        logger.info(f"Reddit r/{subreddit_name}: found {len(tickets)} complaint posts")
    except Exception as e:
        logger.error(f"Reddit subreddit fetch error: {e}")

    return tickets


def ingest_reddit_to_db(tickets_list: List[Dict]) -> int:
    """Insert Reddit complaint posts as SupportLens tickets."""
    if not tickets_list:
        return 0

    from database import SessionLocal, Ticket
    from ai.pipeline import detect_emotion, detect_intent, detect_churn_risk, compute_urgency_score

    db = SessionLocal()
    created = 0
    now = datetime.utcnow()

    try:
        for t in tickets_list:
            existing = db.query(Ticket).filter(Ticket.customer_email == t["customer_email"]).first()
            if existing:
                continue

            emotion_type, emotion_score = detect_emotion(t["description"])
            intent = detect_intent(t["description"])
            churn = detect_churn_risk(t["description"])
            severity = "P2"
            urgency = compute_urgency_score(
                emotion_score=emotion_score,
                emotion_type=emotion_type,
                is_churn_risk=churn,
                customer_tier="standard",
                intent=intent,
                sla_hours_remaining=12,
                keyword_severity=severity,
            )

            ticket = Ticket(
                subject=t["subject"],
                description=t["description"],
                customer_name=t["customer_name"],
                customer_email=t["customer_email"],
                customer_tier="standard",
                source="reddit",
                status="open",
                emotion_type=emotion_type,
                emotion_score=emotion_score,
                intent=intent,
                urgency_score=urgency,
                is_churn_risk=churn,
                is_escalated=False,
                requires_human=churn,
                severity=severity,
                sla_deadline=now + timedelta(hours=12),
                sla_breached=False,
                product_area="Community",
                platform="Web",
                created_at=now,
                updated_at=now,
            )
            db.add(ticket)
            created += 1

        db.commit()
        logger.info(f"Reddit ingester: inserted {created} new tickets")
    except Exception as e:
        db.rollback()
        logger.error(f"Reddit DB insert error: {e}")
    finally:
        db.close()

    return created



def search_reddit_solutions(query: str, product_name: str) -> List[dict]:
    """
    Search Reddit for community solutions related to a support issue.

    Args:
        query: The issue description or search terms
        product_name: Name of the product for context

    Returns:
        List of up to 3 results with post_title, post_url, top_comment_body,
        upvote_count, created_utc
    """
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        logger.warning("Reddit credentials not configured — skipping Reddit search")
        return []

    try:
        import praw
    except ImportError:
        logger.error("praw not installed — run: pip install praw")
        return []

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )

        search_query = f"{product_name} {query}"
        logger.info(f"Searching Reddit: '{search_query}'")

        results = []
        submissions = reddit.subreddit("all").search(
            search_query,
            sort="relevance",
            time_filter="year",
            limit=10,
        )

        for sub in submissions:
            if len(results) >= 3:
                break

            # Find best comment (highest score, >50 chars)
            top_comment = None
            try:
                sub.comments.replace_more(limit=0)
                candidates = [
                    c for c in sub.comments.list()
                    if hasattr(c, "body") and len(c.body) > 50 and c.body != "[deleted]"
                ]
                if candidates:
                    top_comment = max(candidates, key=lambda c: c.score)
            except Exception as e:
                logger.debug(f"Comment fetch error: {e}")

            results.append({
                "post_title": sub.title,
                "post_url": f"https://reddit.com{sub.permalink}",
                "top_comment_body": top_comment.body[:800] if top_comment else "",
                "upvote_count": sub.score,
                "created_utc": sub.created_utc,
            })

        logger.info(f"Reddit search returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Reddit search failed: {e}")
        return []
