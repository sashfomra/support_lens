"""
ingest_docs.py — Document ingestion into ChromaDB vector store.

Run with: python ingest_docs.py

Sources:
  1. Local knowledge base files from knowledge_base/ folder (primary)
  2. Remote URLs in DOC_SOURCES (optional, for extra context)

Chunks text (300 words, 50-word overlap), embeds with all-MiniLM-L6-v2,
and stores in ChromaDB collection 'supportlens_docs'.
"""

import re
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Optional extra URLs (leave empty to use only local KB) ───────────────────
DOC_SOURCES = [
    "https://docs.stripe.com/refunds",
    "https://docs.stripe.com/disputes",
    "https://docs.stripe.com/billing/subscriptions/cancel"
]
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CHROMA_COLLECTION = "supportlens_docs"
CHUNK_SIZE = 300       # words
CHUNK_OVERLAP = 50     # words

KB_DIR = Path(__file__).parent / "knowledge_base"


def read_local_file(path: Path) -> tuple[str, dict]:
    """Read a local .txt knowledge base file."""
    text = path.read_text(encoding="utf-8")
    # Extract TITLE and SECTIONs as headings
    headings = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TITLE:"):
            headings[line.replace("TITLE:", "").strip()] = "h1"
        elif line.startswith("SECTION:"):
            headings[line.replace("SECTION:", "").strip()] = "h2"
    return text, {"headings": headings, "filename": path.name}


def scrape_url_requests(url: str) -> tuple[str, dict]:
    """Scrape a URL using requests + BeautifulSoup."""
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "SupportLens-Scraper/1.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "header", "script", "style", "aside", "form"]):
        tag.decompose()

    headings = {h.get_text(strip=True): h.name for h in soup.find_all(["h1", "h2"])}
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text, {"headings": headings}


def scrape_url_playwright(url: str) -> str:
    """Fallback scraper for JS-rendered pages using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed — skipping JS fallback")
        return ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        html = page.content()
        browser.close()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "footer", "header", "script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk) > 30:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def get_section_title(chunk: str, headings: dict) -> str:
    """Find the nearest heading to a chunk by substring match."""
    for heading_text in headings:
        if heading_text and any(w.lower() in chunk.lower() for w in heading_text.split()[:3]):
            return heading_text
    return "General"


def main():
    # ── Import ChromaDB ───────────────────────────────────────────────────────
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("Missing: pip install chromadb sentence-transformers")
        sys.exit(1)

    # ── Setup ChromaDB ────────────────────────────────────────────────────────
    db_path = Path(__file__).parent / "chroma_db"
    db_path.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))

    # Clear + recreate collection for fresh ingest
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    # ── Load embedding model ──────────────────────────────────────────────────
    logger.info("Loading embedding model all-MiniLM-L6-v2 ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    total_chunks = 0
    stored = 0
    scraped_count = 0

    # ── Step 1: Ingest local KB files ─────────────────────────────────────────
    local_files = list(KB_DIR.glob("*.txt")) if KB_DIR.exists() else []
    if local_files:
        logger.info(f"Found {len(local_files)} local KB files in {KB_DIR}")
    else:
        logger.warning(f"No local KB files found in {KB_DIR}")

    for kb_file in local_files:
        logger.info(f"Ingesting local: {kb_file.name}")
        text, meta = read_local_file(kb_file)
        headings = meta.get("headings", {})

        chunks = chunk_text(text)
        logger.info(f"  -> {len(chunks)} chunks")
        total_chunks += len(chunks)

        scrape_time = datetime.now(timezone.utc).isoformat()
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_id = f"local::{kb_file.stem}::chunk_{i}"
            section = get_section_title(chunk, headings)
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source_url": f"local://{kb_file.name}",
                    "chunk_index": i,
                    "section_title": section,
                    "scraped_at": scrape_time,
                    "filename": kb_file.name,
                }],
            )
            stored += 1

        scraped_count += 1
        logger.info(f"  -> Stored {len(chunks)} chunks for {kb_file.name}")

    # ── Step 2: Ingest remote URLs (optional) ────────────────────────────────
    for url in DOC_SOURCES:
        logger.info(f"Scraping URL: {url}")
        text = ""
        headings = {}

        try:
            text, meta = scrape_url_requests(url)
            headings = meta.get("headings", {})
            if len(text) < 200:
                raise ValueError("Content too short")
        except Exception as e:
            logger.warning(f"  requests failed ({e}), trying Playwright...")
            try:
                text = scrape_url_playwright(url)
            except Exception as pe:
                logger.error(f"  Playwright also failed ({pe}) - skipping {url}")
                text = ""

        if not text or len(text) < 30:
            logger.warning(f"  Skipping {url} - no content extracted")
            continue

        scraped_count += 1
        chunks = chunk_text(text)
        logger.info(f"  -> {len(chunks)} chunks")
        total_chunks += len(chunks)

        scrape_time = datetime.now(timezone.utc).isoformat()
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_id = f"{url}::chunk_{i}"
            section = get_section_title(chunk, headings)
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source_url": url,
                    "chunk_index": i,
                    "section_title": section,
                    "scraped_at": scrape_time,
                }],
            )
            stored += 1

        logger.info(f"  -> Stored {len(chunks)} chunks for {url}")

    print("\n" + "="*50)
    print("DONE! Ingest complete!")
    print(f"   Sources ingested: {scraped_count}")
    print(f"   Chunks created:   {total_chunks}")
    print(f"   Chunks stored:    {stored}")
    print("="*50)


if __name__ == "__main__":
    main()
