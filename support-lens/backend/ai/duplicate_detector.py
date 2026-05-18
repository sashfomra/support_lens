"""
Duplicate Ticket Detector — checks new tickets against ChromaDB for similarity.
Threshold: 0.85 cosine similarity = flag as duplicate.
"""
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

DUPLICATE_THRESHOLD = 0.82  # similarity above this → flag as duplicate
CHROMA_COLLECTION = "supportlens_docs"
TICKET_COLLECTION = "supportlens_tickets"


def _get_ticket_collection():
    """Get or create the ChromaDB ticket collection."""
    try:
        import chromadb
        from pathlib import Path
        db_path = Path(__file__).parent.parent / "chroma_db"
        client = chromadb.PersistentClient(path=str(db_path))
        col = client.get_or_create_collection(TICKET_COLLECTION)
        return col
    except Exception as e:
        logger.error(f"ChromaDB ticket collection error: {e}")
        return None


def _embed(text: str) -> list:
    """Embed text using sentence-transformers."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model.encode([text]).tolist()[0]


def index_ticket(ticket_id: int, subject: str, description: str) -> bool:
    """Add a ticket to the ChromaDB ticket index for future duplicate checks."""
    col = _get_ticket_collection()
    if col is None:
        return False
    try:
        text = f"{subject}. {description}"
        embedding = _embed(text)
        col.upsert(
            ids=[str(ticket_id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"ticket_id": ticket_id, "subject": subject}],
        )
        return True
    except Exception as e:
        logger.error(f"Failed to index ticket {ticket_id}: {e}")
        return False


def check_duplicate(subject: str, description: str, exclude_id: Optional[int] = None) -> Optional[Tuple[int, float, str]]:
    """
    Check if a new ticket is a duplicate of any existing ticket.
    Returns (original_ticket_id, similarity_score, original_subject) or None.
    """
    col = _get_ticket_collection()
    if col is None:
        return None

    count = col.count()
    if count == 0:
        return None

    try:
        text = f"{subject}. {description}"
        embedding = _embed(text)

        results = col.query(
            query_embeddings=[embedding],
            n_results=min(3, count),
            include=["documents", "metadatas", "distances"],
        )

        if not results["distances"] or not results["distances"][0]:
            return None

        for dist, meta in zip(results["distances"][0], results["metadatas"][0]):
            similarity = max(0.0, 1.0 - dist)
            original_id = meta.get("ticket_id")
            if exclude_id and original_id == exclude_id:
                continue
            if similarity >= DUPLICATE_THRESHOLD:
                return (original_id, round(similarity, 3), meta.get("subject", "Unknown"))

        return None
    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        return None
