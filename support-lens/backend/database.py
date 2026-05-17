from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import os

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./support_lens.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True, nullable=True)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    description_masked = Column(Text, nullable=True)  # PII-masked version
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_tier = Column(String, default="standard")  # standard / premium / enterprise
    source = Column(String, default="ticket")  # ticket / reddit / email / review
    status = Column(String, default="open")  # open / in_progress / resolved / closed

    # AI-enriched fields
    emotion_type = Column(String, nullable=True)     # angry / frustrated / confused / neutral / happy
    emotion_score = Column(Float, nullable=True)     # 1-10
    urgency_score = Column(Float, nullable=True)     # 0-100
    intent = Column(String, nullable=True)           # refund / bug / feature / account / churn / complaint
    product_area = Column(String, nullable=True)     # Billing / Login / Performance / UX / Feature
    platform = Column(String, nullable=True)         # Android / iOS / Web / API
    severity = Column(String, nullable=True)         # P1 / P2 / P3
    resolution_type = Column(String, nullable=True)  # Self-serve / Agent-resolved / Escalated / Refund issued

    # Flags
    is_churn_risk = Column(Boolean, default=False)
    is_escalated = Column(Boolean, default=False)
    requires_human = Column(Boolean, default=False)

    # AI-generated content
    ai_summary = Column(Text, nullable=True)         # 3-line summary
    ai_draft_reply = Column(Text, nullable=True)
    ai_draft_confidence = Column(Float, nullable=True)

    # SLA
    sla_deadline = Column(DateTime, nullable=True)
    sla_breached = Column(Boolean, default=False)

    # CSAT (post-resolution)
    csat_score = Column(Float, nullable=True)  # 1-5

    # Agent
    assigned_agent_id = Column(String, nullable=True)
    assigned_agent_name = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="ticket")
    kb_suggestions = relationship("KBSuggestion", back_populates="ticket")


class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    product_area = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # comma-separated
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    suggestions = relationship("KBSuggestion", back_populates="article")


class KBSuggestion(Base):
    __tablename__ = "kb_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    article_id = Column(Integer, ForeignKey("kb_articles.id"))
    confidence_score = Column(Float, nullable=False)
    rewritten_steps = Column(Text, nullable=True)
    was_helpful = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ticket = relationship("Ticket", back_populates="kb_suggestions")
    article = relationship("KBArticle", back_populates="suggestions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    agent_id = Column(String, nullable=True)
    action = Column(String, nullable=False)        # pipeline_run / reply_generated / reply_edited / reply_sent / escalated
    slm_prompt = Column(Text, nullable=True)       # masked prompt sent to SLM
    slm_raw_output = Column(Text, nullable=True)   # raw output before filter
    slm_final_output = Column(Text, nullable=True) # output after policy filter
    agent_edited = Column(Boolean, default=False)
    agent_edit_diff = Column(Text, nullable=True)
    policy_flags = Column(Text, nullable=True)     # comma-separated flags triggered
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ticket = relationship("Ticket", back_populates="audit_logs")


class IssueCluster(Base):
    __tablename__ = "issue_clusters"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    ticket_count = Column(Integer, default=0)
    ticket_ids = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    date_window = Column(String, nullable=True)  # e.g. "2026-05-09_to_2026-05-16"


class SolutionAudit(Base):
    """Immutable audit log for every solution engine run."""
    __tablename__ = "solution_audit"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, nullable=True, index=True)
    query_used = Column(Text, nullable=True)
    sources_retrieved = Column(Text, nullable=True)   # JSON
    confidence_score = Column(Float, nullable=True)
    fallback_flag = Column(Boolean, default=False)
    slm_output = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SolutionFeedback(Base):
    """Agent thumbs up/down feedback on generated solutions."""
    __tablename__ = "solution_feedback"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, nullable=True, index=True)
    rating = Column(Integer, nullable=False)   # 1 = thumbs up, -1 = thumbs down
    comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
