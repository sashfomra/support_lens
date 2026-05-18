# 🔍 SupportLens — AI Support Intelligence Platform

> **Turn every support agent into your best support agent.**  
> Real-time AI triage, churn detection, RAG knowledge retrieval, voice transcription, multi-channel ingestion, and full manager analytics — all running locally with Ollama.

---

## 🚀 Quick Start

```bash
# 1. Install backend dependencies
cd support-lens/backend
pip install -r requirements.txt

# 2. Install frontend dependencies
cd ../frontend
npm install

# 3. Start everything
cd ..
./start.ps1          # PowerShell
# or
start.bat            # Windows CMD
```

Backend runs on **http://localhost:8000** | Frontend on **http://localhost:5173**  
API Docs: **http://localhost:8000/docs**

---

## 🧠 AI Pipeline — 8-Step Processing Engine

Every ticket (web form, voice, Reddit, App Store, Email) passes through this pipeline:

| Step | Feature | Description |
|------|---------|-------------|
| 1 | 🔒 **PII Masking** | Strips names, emails, phone numbers, card numbers before LLM processing |
| 2 | 😡 **Emotion Detection** | Classifies emotion type (angry/frustrated/confused/neutral/happy/worried) + intensity score 0–10 |
| 3 | 🎯 **Intent Classification** | Tags intent: billing, refund, bug_report, feature_request, cancellation, etc. |
| 4 | ⚠️ **Churn Risk Analysis** | Flags tickets with high cancellation/competitor language as churn risks |
| 5 | 📊 **Urgency Scoring** | 0–100 composite score from emotion × tier × SLA × churn signals |
| 6 | 🏷️ **Auto-Tagging** | Product area, platform, severity (P1/P2/P3), source channel — via Llama 3.2:3b |
| 7 | 📝 **3-Line AI Summary** | Concise 3-point summary of customer issue via SLM |
| 8 | 🔍 **RAG KB Search** | ChromaDB vector search against knowledge base → top-3 article suggestions with confidence scores |

---

## ✨ Core Features

### 🎯 Agent Queue (Urgency-Sorted Workspace)
- Real-time ticket list auto-sorted by urgency score (0–100)
- Filters: status (open/in_progress/all), source channel, sort order
- **Churn Risk** and **Escalated** visual indicators (colored left border)
- SLA countdown timer — live, color-coded (green → amber → red breach)
- Emotion badges with emoji + intensity score
- Customer tier display (Standard / Premium / Enterprise)
- One-click **Ticket Modal** with full AI enrichment display
- Auto-refreshes every 15 seconds

### 📋 Ticket Detail Modal
- Full AI 3-line summary (numbered ①②③)
- Original customer message (PII-masked view)
- **Customer 360 Context** — full history for the same email, sentiment trend (emoji timeline), "High Friction Account" badge
- KB Solution Matches with confidence % from ChromaDB RAG
- **AI Draft Reply Generator** — tone-adapted (empathetic/firm/apologetic) based on emotion + tier
- Policy filter flags on draft (auto-removes disallowed content)
- Confidence score on draft (low confidence warning)
- **AI Solution Engine** — ChromaDB + Reddit + Stack Overflow cross-search
- Solution feedback (👍/👎) — feeds back into ranking
- "Use as Draft" button to inject solution into reply box
- "Open in Mail Client" — mailto link with pre-filled subject + draft body
- Save & Mark In Progress action

### 🔁 Duplicate Ticket Detection
- Vector similarity check on every new ticket submission
- Flags tickets that are ≥ X% similar to existing open tickets
- Shows `duplicate_of_id` and `duplicate_similarity` score in UI
- Prevents agents from working on the same issue twice
- Background indexing for all new tickets

### 📥 Ticket Submission (Full AI Pipeline Demo)
- Manual web form with subject, description, customer name, email, tier
- **Quick Load** — 4 sample tickets (payment failure, churn threat, crash, export request)
- 8-step animated pipeline progress indicator (real-time, synced to backend)
- Full pipeline result display: urgency level, emotion, intent, tags, 3-line summary
- Churn Risk and Human Required alert banners

### 🎙️ Voice Note Transcription (Whisper AI)
- Upload `.mp3 .wav .ogg .m4a .webm .flac` — up to 25MB
- Local Whisper `base` model — **no API key required**, runs offline
- Auto-fills form: subject, customer name, email from transcript
- Smart regex + Groq LLM fallback for metadata extraction (email "at" / "dot" spoken forms)
- `transcribe-and-process` endpoint: one-shot audio → enriched ticket

### 📊 Manager Dashboard
- **5 KPI stat cards**: Open Tickets, SLA Breaches, Churn Risks, Avg Urgency, CSAT Score
- **🚨 Live Spike Alerts** — APScheduler checks every 5 min, fires if 2× avg volume in any category
- **Issue Heatmap** — 7-day × 24-hour grid, category color-coded (Billing=red, Technical=blue, etc.)
- **SLA Tracker by Agent** — stacked bar (safe/at-risk/breached) per agent
- **CSAT Forecast** — ML-predicted CSAT from emotion intensity + churn ratio
- **Volume Trend** — 7-day bar chart (Chart.js)
- **Issues by Category** — Doughnut chart
- **Emotion Breakdown** — Doughnut chart
- **Issue Clusters** — AI-detected problem groupings with ticket count
- **Agent Leaderboard** — open tickets, resolved this week, SLA at risk, avg resolution hours, CSAT avg
- **Manager Q&A Bot** — plain-English questions answered from live DB data + evidence + inline bar charts

### 📈 Manager Analytics (5 Tabs)
| Tab | Content |
|-----|---------|
| Overview | 4 metric cards + Volume 7-day bar + Sentiment trend line + Hourly inflow |
| Issue Categories | Category bar chart + doughnut share breakdown + spike alert banner |
| Heatmap | 7d×24h interactive heatmap with purple intensity scale |
| Agent Performance | Full agent leaderboard table + resolved-per-agent bar chart |
| SLA Tracker | Stacked bars by category + At-Risk ticket list with countdown timers |

### 📋 Weekly Digest
- SLM-generated plain-English narrative for team leads
- Powered by `llama3.2:3b` via Ollama
- KPI pills: CSAT avg (with change), SLA breach rate, top 3 categories
- AI narrative section + recommended action for next week
- Regenerate on demand

### 📡 Data Sources & Ingestion
| Source | Technology | Details |
|--------|-----------|---------|
| Reddit | PRAW | Configurable subreddits, complaint-keyword filter, limit per sub |
| Apple App Store | RSS Feed | 1–2 star reviews, no API key needed |
| Google Play | google-play-scraper | 1–2 star reviews, package ID |
| Email IMAP | Python imaplib | Gmail / Outlook unread emails → tickets |
| Voice | OpenAI Whisper (local) | Audio upload → transcript → pipeline |
| Web Form | Manual | Direct ticket creation via UI |

- Live ingestion status per source (never / running / ok / error + last count + last run time)
- **Run Now** button per source with configurable parameters
- 10-second polling for live status updates

### 🚨 Spike Alerter
- APScheduler background job — runs every **5 minutes**
- Compares last-30-min volume vs 7-day hourly average per category
- Fires `critical` alert at 2× threshold, `warning` at 1.5×
- Alerts appear on both Manager Dashboard and Data Sources pages
- Dismiss with one click; dismissed alerts expire
- Demo trigger: submit 5+ same-topic tickets → alert fires within 5 min

### 💡 AI Solution Engine (ChromaDB + Reddit + Stack Overflow)
- POST `/api/solution` — semantic search across 3 knowledge sources
- Confidence score — high (≥75%) uses verified KB, low falls back to AI general knowledge
- `is_general_knowledge` flag shown to agent with "review before sending" warning
- Source chips — clickable links to original docs/Reddit/SO posts
- Feedback loop — 👍/👎 rating sent to `/api/solution/feedback`
- Escalation button when no verified solution found

### 🔐 Policy Filter
- Applied to every AI-generated draft reply
- Strips: refund promises, legal guarantees, off-brand language
- Flags violations shown as red badges on draft
- Confidence degrades if flags triggered (0.85 → 0.65)
- Audit log entry created for every reply generated

### 📚 Knowledge Base (RAG)
- ChromaDB vector store built at startup from KB articles
- Real-time similarity search via `rag_engine.py`
- KB suggestions saved to `KBSuggestion` table per ticket
- Fallback: live RAG search if no cached suggestions
- `ingest_docs.py` — bulk-load markdown/text docs into ChromaDB
- `inject_customer_360.py` — seed customer history for demo

---

## 🗄️ Database Schema (SQLite)

| Table | Purpose |
|-------|---------|
| `tickets` | Core ticket data + all AI enrichment fields |
| `kb_articles` | Knowledge base articles |
| `kb_suggestions` | Per-ticket KB article matches with confidence |
| `issue_clusters` | AI-detected issue groupings |
| `audit_logs` | Full audit trail: LLM prompt, raw output, final output, policy flags |
| `agents` | Agent assignments |

**Key ticket fields:** `urgency_score`, `emotion_type`, `emotion_score`, `intent`, `is_churn_risk`, `is_escalated`, `requires_human`, `severity`, `sla_deadline`, `sla_breached`, `product_area`, `platform`, `ai_summary`, `ai_draft_reply`, `ai_draft_confidence`, `description_masked`, `duplicate_of_id`, `duplicate_similarity`, `csat_score`, `source`

---

## 🔌 API Reference

### Tickets
| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/tickets/` | Create ticket (async AI enrichment) |
| POST | `/tickets/process-sync` | Create + wait for full AI pipeline (demo mode) |
| GET | `/tickets/` | List tickets — filters: status, source, intent, emotion, tier, churn, sort |
| GET | `/tickets/{id}` | Get single ticket |
| PATCH | `/tickets/{id}` | Update ticket (status, draft, etc.) |
| GET | `/tickets/{id}/suggestions` | KB suggestions for ticket |
| POST | `/tickets/draft-reply` | Generate AI draft reply with tone + policy filter |

### Manager
| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/manager/dashboard` | KPI stats + trend data |
| POST | `/manager/ask` | Q&A bot — natural language → DB query → LLM answer + chart |
| GET | `/manager/clusters` | Issue clusters |
| GET | `/manager/agents/stats` | Per-agent performance stats |
| GET | `/manager/weekly-digest` | Generate SLM weekly narrative |
| GET | `/manager/alerts` | Live spike alerts |
| DELETE | `/manager/alerts/{id}` | Dismiss spike alert |

### Insights
| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/insights/heatmap` | 7d×24h ticket volume grid |
| GET | `/insights/sla-breakdown` | SLA status totals + per-agent breakdown |
| GET | `/insights/sentiment-trend` | 30-day sentiment trend by source |
| GET | `/insights/csat-forecast` | Predicted CSAT with drivers |

### Voice
| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/voice/transcribe` | Upload audio → transcript + extracted name/email/subject |
| POST | `/voice/transcribe-and-process` | Upload audio → transcript → full AI pipeline |

### Ingestion
| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/ingest/status` | Last run info for all sources |
| POST | `/ingest/reddit` | Trigger Reddit scraping |
| POST | `/ingest/appstore` | Trigger App Store review scraping |
| POST | `/ingest/email` | Trigger IMAP email fetch |

### Solution Engine
| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/api/solution` | Find solution from ChromaDB + Reddit + SO |
| POST | `/api/solution/feedback` | Submit 👍👎 feedback on solution quality |

### Health
| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/health` | Ollama status, model name, DB connection, KB count, ticket count, RAG ready |

---

## ⚙️ Environment Variables (`backend/.env`)

```env
# Ollama (required)
OLLAMA_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434

# Reddit (optional — for Reddit ingestion)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=SupportLens/1.0

# Email IMAP (optional — for email ingestion)
EMAIL_ADDRESS=your@gmail.com
EMAIL_APP_PASSWORD=your_app_password
IMAP_HOST=imap.gmail.com

# Groq (optional — improves voice metadata extraction)
GROQ_API_KEY=your_groq_key
```

---

## 🏗️ Architecture

```
support-lens/
├── backend/
│   ├── main.py                    # FastAPI app, lifespan, startup
│   ├── database.py                # SQLAlchemy models + session
│   ├── models.py                  # Pydantic request/response schemas
│   ├── spike_alerter.py           # APScheduler spike detection
│   ├── solution_engine.py         # ChromaDB + Reddit + SO search
│   ├── ingest_docs.py             # Bulk KB document ingestion
│   ├── inject_customer_360.py     # Customer history seeder
│   ├── ai/
│   │   ├── pipeline.py            # 8-step AI processing pipeline
│   │   ├── ollama_client.py       # Llama 3.2:3b client (summary, draft, Q&A, digest)
│   │   ├── rag_engine.py          # ChromaDB vector search
│   │   ├── pii_masker.py          # PII detection and masking
│   │   └── duplicate_detector.py  # Vector similarity duplicate check
│   ├── routers/
│   │   ├── tickets.py             # Ticket CRUD + draft + suggestions
│   │   ├── manager.py             # Dashboard + Q&A + agents + digest + alerts
│   │   ├── insights.py            # Heatmap + SLA + sentiment + CSAT forecast
│   │   ├── solution.py            # Solution engine API
│   │   ├── voice.py               # Whisper transcription + Groq metadata
│   │   └── ingest.py              # Reddit + App Store + Email ingestion
│   └── scrapers/
│       ├── reddit_scraper.py      # PRAW Reddit scraper
│       ├── appstore_scraper.py    # Apple RSS + Google Play scraper
│       ├── email_scraper.py       # IMAP email fetcher
│       └── stackoverflow_scraper.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Sidebar + routing
│   │   ├── index.css              # Design system tokens + components
│   │   ├── api/client.js          # Axios API client
│   │   ├── pages/
│   │   │   ├── AgentView.jsx      # Urgency queue + ticket modal + Customer 360
│   │   │   ├── TicketInbox.jsx    # Ticket submit + voice upload + pipeline demo
│   │   │   ├── ManagerDashboard.jsx  # KPI + heatmap + SLA + CSAT + Q&A bot
│   │   │   ├── ManagerAnalytics.jsx  # 5-tab deep analytics
│   │   │   ├── WeeklyDigest.jsx   # LLM-generated weekly narrative
│   │   │   └── DataSources.jsx    # Ingestion controls + spike alerts
│   │   └── components/
│   │       └── SolutionPanel.jsx  # Solution engine UI + feedback
│   └── vite.config.js
└── README.md
```

---

## 🤖 AI Models Used

| Model | Provider | Purpose |
|-------|---------|---------|
| `llama3.2:3b` | Ollama (local) | 3-line summary, draft reply, weekly digest, manager Q&A |
| `whisper-base` | OpenAI Whisper (local) | Voice transcription — ~145MB, no API key |
| `llama3-8b-8192` | Groq API (optional) | Fast metadata extraction from voice transcripts |
| ChromaDB | Local vector DB | RAG KB search, duplicate detection, solution search |

---

## 🔑 Key Design Decisions

- **Local-first AI** — Ollama + Whisper run 100% offline, no cloud LLM costs
- **Sync vs Async pipeline** — `/process-sync` waits for full AI enrichment (demo mode); `POST /tickets/` runs pipeline in background (production mode)
- **SLA deadlines set by tier** — Enterprise: 4h, Premium: 8h, Standard: 24h
- **Churn detection** — keyword matching (cancel, switching, competitor, refund) + emotion intensity threshold
- **Duplicate detection** — TF-IDF / vector similarity on (subject + description), threshold configurable
- **Policy filter** — runs on every AI draft before showing to agent; strips legally risky content
- **Spike alerter** — compares 30-min rolling count vs 7-day hourly average per product area

---

## 🧪 Demo Walkthrough

1. **Submit a ticket** → `/inbox` → click a sample → `Process with AI Pipeline` → watch 8 steps animate
2. **View agent queue** → `/` → tickets sorted by urgency score, churn risks highlighted
3. **Open a ticket** → view AI summary, Customer 360, KB suggestions, generate draft reply
4. **Voice upload** → record or use `demo_voice_ticket.wav` → form auto-fills
5. **Trigger spike alert** → submit 5+ similar tickets → wait up to 5 min → alert appears on Dashboard
6. **Reddit ingestion** → `/sources` → enter subreddits → Run Now → tickets appear in queue
7. **Manager Q&A** → `/dashboard` → ask "Why did CSAT drop?" or "Show SLA at-risk"
8. **Weekly digest** → `/digest` → click Regenerate → LLM narrative generated
9. **Analytics** → `/analytics` → explore all 5 tabs with real-time data

---

*Built for Relanto Hackathon 2026 · SupportLens AI Intelligence Platform*
