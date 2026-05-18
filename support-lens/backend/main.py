"""
SupportLens FastAPI Application
"""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env file — must happen before any other imports that read env vars
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
        print(f"Loaded .env from {_env_path}")
    else:
        load_dotenv()  # try current dir
except ImportError:
    pass  # dotenv not installed, rely on system env vars

from database import create_tables, SessionLocal, KBArticle
from routers import tickets as tickets_router
from routers import manager as manager_router
from routers import insights as insights_router
from routers import solution as solution_router
from routers import voice as voice_router
from routers import ingest as ingest_router
from ai import rag_engine as rag
from ai import ollama_client as llm
from models import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, seed DB, build RAG index."""
    print("SupportLens starting up...")
    create_tables()

    # Seed database
    db = SessionLocal()
    try:
        from data.seeder import seed
        seed(db)
    except Exception as e:
        print(f"Seeder error (non-fatal): {e}")
    finally:
        db.close()

    # Build RAG index from KB articles
    print("Building RAG index...")
    db = SessionLocal()
    try:
        articles = db.query(KBArticle).all()
        article_dicts = [{"id": a.id, "title": a.title, "content": a.content} for a in articles]
        if article_dicts:
            await rag.async_build_index(article_dicts)
            print(f"  ✓ RAG index built with {len(article_dicts)} articles")
    except Exception as e:
        print(f"RAG index error (non-fatal): {e}")
    finally:
        db.close()

    # Start spike alerter scheduler
    try:
        from spike_alerter import start_scheduler
        start_scheduler()
        print("Spike alerter started.")
    except Exception as e:
        print(f"Spike alerter startup error (non-fatal): {e}")

    print("SupportLens ready.")
    yield
    print("SupportLens shutting down.")


app = FastAPI(
    title="SupportLens API",
    description="AI-powered customer support intelligence system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router.router)
app.include_router(manager_router.router)
app.include_router(insights_router.router)
app.include_router(solution_router.router)
app.include_router(voice_router.router)
app.include_router(ingest_router.router)


@app.get("/health", response_model=HealthResponse)
async def health():
    db = SessionLocal()
    try:
        ollama_ok = await llm.check_connection()
        models = await llm.list_models() if ollama_ok else []
        kb_count = db.query(KBArticle).count()
        from database import Ticket
        ticket_count = db.query(Ticket).count()
    except Exception:
        ollama_ok = False
        kb_count = 0
        ticket_count = 0
    finally:
        db.close()

    return HealthResponse(
        status="ok",
        ollama_connected=ollama_ok,
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        db_connected=True,
        kb_articles_count=kb_count,
        tickets_count=ticket_count,
        rag_index_ready=rag.is_ready(),
    )


@app.get("/")
def root():
    return {"message": "SupportLens API — see /docs for full API reference"}
