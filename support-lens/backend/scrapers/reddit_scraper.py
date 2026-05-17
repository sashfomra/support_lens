"""
Reddit Solution Scraper — uses PRAW to find community-vetted solutions.

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
from typing import List, Optional

logger = logging.getLogger(__name__)

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "SupportLens/1.0")


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
