from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TicketCreate(BaseModel):
    subject: str
    description: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_tier: str = "standard"
    source: str = "ticket"
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None


class KBSuggestionOut(BaseModel):
    article_id: int
    article_title: str
    confidence_score: float
    rewritten_steps: Optional[str] = None

    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    id: int
    external_id: Optional[str] = None
    subject: str
    description: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_tier: str
    source: str
    status: str

    # AI fields
    emotion_type: Optional[str] = None
    emotion_score: Optional[float] = None
    urgency_score: Optional[float] = None
    intent: Optional[str] = None
    product_area: Optional[str] = None
    platform: Optional[str] = None
    severity: Optional[str] = None
    resolution_type: Optional[str] = None

    # Flags
    is_churn_risk: bool
    is_escalated: bool
    requires_human: bool

    # Duplicate detection
    duplicate_of_id: Optional[int] = None
    duplicate_similarity: Optional[float] = None

    # AI content
    ai_summary: Optional[str] = None
    ai_draft_reply: Optional[str] = None
    ai_draft_confidence: Optional[float] = None

    # SLA
    sla_deadline: Optional[datetime] = None
    sla_breached: bool
    csat_score: Optional[float] = None

    # Agent
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    ai_draft_reply: Optional[str] = None  # agent edited reply
    csat_score: Optional[float] = None
    resolution_type: Optional[str] = None


class DraftReplyRequest(BaseModel):
    ticket_id: int
    agent_id: Optional[str] = "agent-1"


class DraftReplyOut(BaseModel):
    draft: str
    confidence: float
    tone_applied: str
    policy_flags: List[str] = []
    low_confidence: bool = False


class ManagerQARequest(BaseModel):
    question: str
    agent_id: Optional[str] = "manager-1"


class ManagerQAResponse(BaseModel):
    answer: str
    evidence_tickets: List[dict] = []
    chart_data: Optional[dict] = None
    query_type: str = "general"


class WeeklyDigestOut(BaseModel):
    generated_at: datetime
    period: str
    narrative: str
    top_categories: List[dict]
    csat_summary: dict
    sla_summary: dict
    recommendation: str


class AgentStatsOut(BaseModel):
    agent_id: str
    agent_name: str
    open_tickets: int
    resolved_this_week: int
    avg_resolution_hours: float
    sla_at_risk: int
    csat_avg: Optional[float] = None


class DashboardStatsOut(BaseModel):
    total_open: int
    total_resolved_today: int
    sla_breached: int
    churn_risks: int
    avg_urgency: float
    avg_csat: Optional[float] = None
    ticket_by_category: dict
    ticket_by_emotion: dict
    csat_trend: List[dict]
    volume_trend: List[dict]


class KBArticleCreate(BaseModel):
    title: str
    content: str
    product_area: Optional[str] = None
    tags: Optional[str] = None


class KBArticleOut(BaseModel):
    id: int
    title: str
    content: str
    product_area: Optional[str] = None
    tags: Optional[str] = None
    view_count: int
    helpful_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ClusterOut(BaseModel):
    id: int
    label: str
    description: Optional[str] = None
    ticket_count: int
    date_window: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    ollama_model: str
    db_connected: bool
    kb_articles_count: int
    tickets_count: int
    rag_index_ready: bool
