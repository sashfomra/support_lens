# SupportLens 🔍

**AI-Powered Customer Support Intelligence System**  
*Relanto Hackathon 2026*

> "Turn every support agent into your best support agent — and give every team lead the visibility they have never had."

---

## Quick Start

### Prerequisites
- **Python 3.9+** (installed ✓)
- **Node.js 18+** (installed ✓)  
- **Ollama** running locally with `llama3.2:3b` pulled ✓

### 1. Install Dependencies (one time only)

**Double-click `install.bat`** — or run manually:

```bash
# Backend
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic pydantic-settings httpx numpy scikit-learn python-multipart aiofiles python-dateutil sentence-transformers faiss-cpu transformers torch spacy
python -m spacy download en_core_web_sm

# Frontend
cd frontend && npm install
```

### 2. Launch the App

**Double-click `start.bat`** — this opens two terminal windows:
- Backend at **http://localhost:8000**
- Frontend at **http://localhost:5173**

The browser opens automatically.

---

## Features

### 🎯 Agent View — Urgency Queue
- Real-time ticket queue sorted by AI-computed urgency score (0–100)
- Color-coded badges: 🔴 HIGH / 🟡 MED / 🟢 LOW
- Emotion detection with intensity score (1–10)
- SLA countdown timers (live, auto-updates)
- One-click "View Draft Reply" — opens AI-generated reply for editing
- RAG knowledge base suggestions with confidence scores

### 📥 New Ticket Inbox  
- Submit any ticket and watch the AI pipeline process it in real time
- Animated step-by-step pipeline progress (PII masking → emotion → urgency → SLM)
- Shows all AI outputs: summary, emotion, intent, tags, urgency score
- 4 pre-loaded sample tickets (angry, churn-risk, enterprise, neutral)

### 📊 Manager Dashboard
- Live stats: open tickets, SLA breaches, churn risks, CSAT
- CSAT trend chart (7 days)
- Volume trend chart (7 days)  
- Issue category breakdown (doughnut)
- Emotion distribution (doughnut)
- Issue cluster detection
- Agent leaderboard with CSAT, open tickets, SLA risk
- **Conversational Q&A bot** — ask in plain English:
  - "Why did CSAT drop?"
  - "Which agent has the most SLA risks?"
  - "How many churn risks do we have this week?"

### 📋 Weekly Digest
- SLM-generated plain-English narrative (llama3.2:3b)
- Top 3 issue categories, CSAT trend, SLA performance
- One recommended action for the coming week

---

## AI Pipeline (Every Ticket)

```
Customer Message
     ↓
1. PII Masking (regex + spaCy NER)
     ↓
2. Emotion detection (type + intensity 1-10)
     ↓
3. Intent classification (refund/bug/churn/account/...)
     ↓
4. Churn risk detection (keyword triggers)
     ↓
5. Urgency score (composite weighted formula, 0-100)
     ↓
6. Human escalation gate (auto-routes if needed)
     ↓
7. SLM Auto-tagger (product area, platform, severity)
     ↓
8. SLM 3-line summarizer
     ↓
9. RAG KB search (FAISS, cosine threshold 0.72)
     ↓
Enriched ticket in queue
```

## Guardrails

- **PII masking**: emails, phones, order IDs stripped before SLM
- **Confidence gate**: low-confidence drafts marked for review
- **Policy filter**: blocks legal language, competitor mentions, false commitments
- **Human gate**: churn-risk, high-anger, enterprise tickets never handled autonomously
- **Audit log**: every SLM input/output logged immutably

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Chart.js |
| Backend | FastAPI (Python), SQLite |
| SLM | Ollama — llama3.2:3b |
| RAG | FAISS + sentence-transformers (all-MiniLM-L6-v2) |
| PII | Regex + spaCy NER |

---

## API Reference

Full interactive docs at: **http://localhost:8000/docs**

Key endpoints:
- `GET /health` — system status
- `POST /tickets/process-sync` — create + AI-enrich ticket (synchronous)
- `GET /tickets/` — list tickets with filters
- `POST /tickets/draft-reply` — generate SLM draft reply
- `GET /manager/dashboard` — dashboard stats
- `POST /manager/ask` — conversational Q&A bot
- `GET /manager/weekly-digest` — SLM weekly narrative
- `GET /manager/clusters` — issue clusters
- `GET /manager/agents/stats` — agent leaderboard

---

## Environment Variables

Create `backend/.env` to override defaults:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
DATABASE_URL=sqlite:///./support_lens.db
```
