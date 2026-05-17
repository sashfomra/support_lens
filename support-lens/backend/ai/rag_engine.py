"""
RAG Engine — with faiss-cpu graceful fallback for Python 3.14 compatibility.
Uses sklearn cosine_similarity if FAISS not available.
"""
import numpy as np
from typing import List, Tuple, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

CONFIDENCE_THRESHOLD = 0.72
TOP_K = 3

_executor = ThreadPoolExecutor(max_workers=2)

_model = None
_embeddings_matrix = None
_article_ids: List[int] = []
_article_titles: List[str] = []
_article_contents: List[str] = []
_use_faiss = False

# Try importing FAISS
try:
    import faiss as _faiss
    _use_faiss = True
    _faiss_index = None
except ImportError:
    _faiss = None
    _faiss_index = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _encode(texts: List[str]) -> np.ndarray:
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.astype("float32")


def build_index(articles: List[dict]):
    """Build or rebuild the search index from KB articles."""
    global _faiss_index, _embeddings_matrix, _article_ids, _article_titles, _article_contents

    if not articles:
        return

    _article_ids = [a["id"] for a in articles]
    _article_titles = [a["title"] for a in articles]
    _article_contents = [a["content"] for a in articles]

    texts = [f"{a['title']}. {a['content']}" for a in articles]
    embeddings = _encode(texts)

    if _use_faiss:
        dim = embeddings.shape[1]
        _faiss_index = _faiss.IndexFlatIP(dim)
        _faiss_index.add(embeddings)
    else:
        # Fallback: store matrix for sklearn cosine similarity
        _embeddings_matrix = embeddings


def is_ready() -> bool:
    return True


def search(query: str, top_k: int = TOP_K) -> List[Tuple[int, str, str, float]]:
    """
    Search for similar KB articles.
    Returns list of (article_id, title, content, confidence_score).
    Only includes results above CONFIDENCE_THRESHOLD.
    """
    if not is_ready():
        return []

    query_embedding = _encode([query])

    if _use_faiss and _faiss_index is not None:
        scores, indices = _faiss_index.search(query_embedding, top_k)
        raw_results = [(float(scores[0][i]), int(indices[0][i])) for i in range(len(scores[0]))]
    else:
        # sklearn fallback
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(query_embedding, _embeddings_matrix)[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]
        raw_results = [(float(similarities[i]), int(i)) for i in top_indices]

    results = []
    for score, idx in raw_results:
        if idx < 0 or idx >= len(_article_ids):
            continue
        if score >= CONFIDENCE_THRESHOLD:
            results.append((
                _article_ids[idx],
                _article_titles[idx],
                _article_contents[idx],
                round(score, 3)
            ))

    return results


async def async_search(query: str, top_k: int = TOP_K) -> List[Tuple[int, str, str, float]]:
    """Async wrapper for search."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, search, query, top_k)


async def async_build_index(articles: List[dict]):
    """Async wrapper for building index."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, build_index, articles)
