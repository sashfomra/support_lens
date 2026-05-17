"""
Stack Overflow Solution Fetcher — uses the public Stack Exchange API (no key needed).
"""
import logging
import requests
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SO_BASE = "https://api.stackexchange.com/2.3"


def search_stackoverflow(query: str) -> Optional[dict]:
    """
    Search Stack Overflow for an accepted answer to the given query.

    Args:
        query: The issue search query

    Returns:
        Dict with question_title, question_url, answer_body, score
        or None if nothing found / API fails
    """
    try:
        # Step 1 — search for questions
        search_resp = requests.get(
            f"{SO_BASE}/search/advanced",
            params={
                "q": query,
                "order": "desc",
                "sort": "relevance",
                "site": "stackoverflow",
                "accepted": "True",
                "filter": "withbody",
                "pagesize": 5,
            },
            timeout=10,
        )
        search_resp.raise_for_status()
        items = search_resp.json().get("items", [])

        # Find first answered question with accepted answer
        target = None
        for item in items:
            if item.get("is_answered") and item.get("accepted_answer_id"):
                target = item
                break

        if not target:
            logger.info("Stack Overflow: no accepted answer found for query")
            return None

        # Step 2 — fetch the accepted answer body
        answer_id = target["accepted_answer_id"]
        ans_resp = requests.get(
            f"{SO_BASE}/answers/{answer_id}",
            params={"site": "stackoverflow", "filter": "withbody"},
            timeout=10,
        )
        ans_resp.raise_for_status()
        ans_items = ans_resp.json().get("items", [])
        if not ans_items:
            return None

        # Strip HTML tags from answer body
        raw_body = ans_items[0].get("body", "")
        plain_body = BeautifulSoup(raw_body, "html.parser").get_text(separator="\n").strip()
        plain_body = plain_body[:800]

        result = {
            "question_title": target.get("title", ""),
            "question_url": target.get("link", ""),
            "answer_body": plain_body,
            "score": ans_items[0].get("score", 0),
        }
        logger.info(f"Stack Overflow: found accepted answer (score={result['score']})")
        return result

    except Exception as e:
        logger.error(f"Stack Overflow search failed: {e}")
        return None
