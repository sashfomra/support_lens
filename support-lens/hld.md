# 🏗️ SupportLens — High Level Design

---

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph CLIENT["🌐 Client Layer (React + Vite :5173)"]
        UI_AUTH["Login Page\nGoogle / Microsoft OAuth"]
        UI_AGENT["Agent Queue\n/"]
        UI_INBOX["Submit Ticket\n/inbox"]
        UI_DASH["Manager Dashboard\n/dashboard"]
        UI_ANA["Analytics\n/analytics"]
        UI_DIGEST["Weekly Digest\n/digest"]
        UI_SOURCES["Data Sources\n/sources"]
    end

    subgraph AUTH["🔐 Auth Layer"]
        GOOGLE["Google OAuth 2.0"]
        MICROSOFT["Microsoft Azure AD\n(@relanto.ai only)"]
    end

    subgraph API["⚙️ FastAPI Backend (:8000)"]
        direction TB
        R_TICKETS["routers/tickets.py\nCRUD + pipeline trigger"]
        R_MANAGER["routers/manager.py\nDashboard + Q&A + Alerts"]
        R_INSIGHTS["routers/insights.py\nHeatmap + SLA + CSAT"]
        R_VOICE["routers/voice.py\nWhisper transcription"]
        R_INGEST["routers/ingest.py\nReddit / AppStore / Email"]
        R_SOLUTION["routers/solution.py\nSolution engine"]
        SPIKE["spike_alerter.py\nAPScheduler (5 min)"]
    end

    subgraph AI["🧠 AI Layer"]
        PIPELINE["ai/pipeline.py\n8-Step Processing"]
        OLLAMA["Ollama\nllama3.2:3b (local)"]
        WHISPER["OpenAI Whisper base\n(local, offline)"]
        GROQ["Groq API\nllama3-8b-8192"]
        RAG["ai/rag_engine.py\nChromaDB Vector Search"]
        PII["ai/pii_masker.py"]
        DUPL["ai/duplicate_detector.py"]
    end

    subgraph DATA["🗄️ Data Layer"]
        SQLITE[("SQLite DB\ntickets / agents\naudit_logs / clusters")]
        CHROMA[("ChromaDB\nVector Store\nKB + Duplicates")]
    end

    subgraph INGEST["📡 Ingestion Sources"]
        REDDIT["Reddit\nPRAW"]
        APPSTORE["Apple App Store\nRSS Feed"]
        GPLAY["Google Play\nScraper"]
        EMAIL["Email IMAP\nGmail / Outlook"]
        VOICE_IN["Voice Upload\n.mp3 .wav .ogg"]
        WEBFORM["Web Form\nManual Entry"]
    end

    UI_AUTH --> GOOGLE
    UI_AUTH --> MICROSOFT
    CLIENT --> API
    API --> AI
    API --> DATA
    AI --> DATA
    INGEST --> R_INGEST
    INGEST --> R_VOICE
    INGEST --> R_TICKETS
    PIPELINE --> OLLAMA
    PIPELINE --> RAG
    PIPELINE --> PII
    PIPELINE --> DUPL
    R_VOICE --> WHISPER
    R_VOICE --> GROQ
    RAG --> CHROMA
    DUPL --> CHROMA
    R_TICKETS --> PIPELINE
    R_MANAGER --> OLLAMA
    SPIKE --> SQLITE
```

---

## 2. Ticket Ingestion & AI Pipeline Flow

```mermaid
flowchart TD
    A([Ticket Source]) --> B{Input Type}

    B -->|Web Form| C[POST /tickets/process-sync]
    B -->|Voice Upload| D[POST /voice/transcribe]
    B -->|Reddit| E[reddit_scraper.py]
    B -->|App Store| F[appstore_scraper.py]
    B -->|Email IMAP| G[email_scraper.py]

    D --> D1[ffmpeg → convert to WAV]
    D1 --> D2[Whisper base → transcript]
    D2 --> D3[Groq LLM → extract\nname / email / subject]
    D3 --> C

    E --> C
    F --> C
    G --> C

    C --> P1

    subgraph PIPELINE["🤖 8-Step AI Pipeline"]
        P1["① PII Masking\npii_masker.py\nStrip name/email/phone/card"]
        P2["② Emotion Detection\nType + Intensity 0–10"]
        P3["③ Intent Classification\nbilling/refund/bug/cancel..."]
        P4["④ Churn Risk Analysis\nKeyword + emotion threshold"]
        P5["⑤ Urgency Scoring\n0–100 composite score"]
        P6["⑥ Auto-Tagging (SLM)\nProduct area / platform / severity"]
        P7["⑦ 3-Line Summary (SLM)\nllama3.2:3b"]
        P8["⑧ RAG KB Search\nChromaDB top-3 matches"]

        P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8
    end

    P8 --> DUP["Duplicate Detector\nVector similarity check"]
    DUP -->|New ticket| DB[("SQLite DB\nSave ticket + all fields")]
    DUP -->|Similar found| WARN["Flag duplicate_of_id\n+ similarity score"]
    WARN --> DB

    DB --> QUEUE["Agent Queue\nUrgency sorted"]
```

---

## 3. Authentication Flow

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant FE as React Frontend
    participant G as Google OAuth
    participant M as Microsoft Azure AD
    participant AC as AuthContext.jsx

    U->>FE: Opens app
    FE->>AC: Check sessionStorage
    AC-->>FE: No session → show LoginPage

    alt Google Sign-In
        U->>FE: Click "Sign in with Google"
        FE->>G: OAuth2 redirect
        G-->>FE: ID token + user profile
        FE->>AC: Store user (any domain allowed)
    end

    alt Microsoft Sign-In
        U->>FE: Click "Sign in with Microsoft"
        FE->>M: OAuth2 redirect
        M-->>FE: ID token + email
        FE->>AC: Check email ends with @relanto.ai
        alt Valid domain
            AC-->>FE: Store user → grant access
        else Invalid domain
            AC-->>FE: Show error "Access restricted to Relanto employees"
        end
    end

    FE->>AC: Persist session in sessionStorage
    AC-->>FE: Render app with sidebar + routes
```

---

## 4. Voice Transcription Flow

```mermaid
flowchart LR
    A["🎤 Audio Upload\n.mp3 / .wav / .ogg\n.m4a / .webm / .flac"] --> B["Save temp file\ntempfile.NamedTemporaryFile"]
    B --> C["ffmpeg subprocess\nConvert → 16kHz mono WAV\n(auto-detected from WinGet)"]
    C --> D["numpy array\nfloat32 PCM"]
    D --> E["Whisper base model\nmodel.transcribe(audio)"]
    E --> F["Raw transcript\nfull customer speech text"]
    F --> G["Groq llama3-8b-8192\nExtract structured fields"]
    G --> H["name\nemail\nsubject (5-7 words)"]
    H --> I["Auto-fill form\nsource = 'voice'"]
    I --> J["AI Pipeline\n8 steps"]
    J --> K["Ticket saved\nappears in Voice filter"]
```

---

## 5. Spike Alerter Flow

```mermaid
flowchart TD
    T["⏰ APScheduler\nEvery 5 minutes"] --> Q["Query SQLite\nTickets in last 30 min\ngrouped by product_area"]
    Q --> AVG["Compute 7-day\nhourly baseline\nper category"]
    AVG --> CMP{Compare\nvolume}
    CMP -->|"> 2× baseline"| CRIT["🚨 CRITICAL Alert\nfire spike_alert"]
    CMP -->|"> 1.5× baseline"| WARN["⚠️ WARNING Alert\nfire spike_alert"]
    CMP -->|"Normal"| OK["✅ No alert"]
    CRIT --> STORE["Store in memory\nalert store"]
    WARN --> STORE
    STORE --> DASH["Manager Dashboard\nGET /manager/alerts"]
    STORE --> SOURCES["Data Sources Page\nGET /manager/alerts"]
    DASH --> DISMISS["Manager clicks Dismiss\nDELETE /manager/alerts/{id}"]
```

---

## 6. Solution Engine Flow

```mermaid
flowchart TD
    A["Agent clicks\nFind Solution"] --> B["POST /api/solution\n{ticket_id, description}"]
    B --> S1["ChromaDB Search\nInternal KB articles"]
    B --> S2["Reddit Search\nScraped complaint threads"]
    B --> S3["Stack Overflow\nTechnical answers"]
    S1 & S2 & S3 --> RANK["Rank by\nconfidence score"]
    RANK --> CONF{Confidence}
    CONF -->|"≥ 75%"| VERF["✅ Verified KB\nHigh confidence"]
    CONF -->|"< 75%"| GEN["⚠️ General AI Knowledge\nReview before sending"]
    VERF & GEN --> UI["Display results\n+ source chips + links"]
    UI --> FB{"Agent rates"}
    FB -->|"👍"| POS["POST /api/solution/feedback\npositive=true"]
    FB -->|"👎"| NEG["POST /api/solution/feedback\npositive=false"]
    UI --> DRAFT["Use as Draft\nInject into reply box"]
    DRAFT --> MAIL["Open in Mail Client\nmailto: pre-filled"]
```

---

## 7. Manager Q&A Bot Flow

```mermaid
sequenceDiagram
    participant M as Manager
    participant FE as Dashboard UI
    participant BE as /manager/ask
    participant DB as SQLite
    participant LLM as Ollama llama3.2:3b

    M->>FE: Types question\n"Why did CSAT drop this week?"
    FE->>BE: POST /manager/ask {question}
    BE->>DB: Run aggregate queries\n(tickets, emotion, SLA, CSAT)
    DB-->>BE: Raw stats + ticket data
    BE->>LLM: Prompt: question + data context
    LLM-->>BE: Narrative answer + insights
    BE-->>FE: {answer, evidence[], chart_data}
    FE-->>M: Display narrative\n+ evidence bullets\n+ inline bar chart
```

---

## 8. Data Flow Summary

```mermaid
graph LR
    subgraph SOURCES["Input Sources"]
        W["Web Form"]
        V["Voice Upload"]
        R["Reddit"]
        AS["App Store"]
        EM["Email"]
    end

    subgraph PROCESSING["Processing"]
        FFMPEG["ffmpeg\naudio decode"]
        WHISPER["Whisper\ntranscription"]
        GROQ["Groq\nmetadata"]
        PIPE["AI Pipeline\n8 steps"]
        CHROMA["ChromaDB\nRAG + Duplicate"]
        OLLAMA["Ollama\nSummary + Draft"]
    end

    subgraph STORAGE["Storage"]
        DB2[("SQLite")]
        VDB[("ChromaDB")]
    end

    subgraph CONSUMERS["Consumers"]
        AGENT["Agent Queue\nUrgency Sorted"]
        MANAGER["Manager Dashboard\nKPIs + Charts"]
        ANALYTICS["Analytics\n5 Tabs"]
        DIGEST["Weekly Digest\nLLM Narrative"]
        SPIKE2["Spike Alerter\nReal-time alerts"]
    end

    SOURCES --> PROCESSING
    V --> FFMPEG --> WHISPER --> GROQ
    PROCESSING --> STORAGE
    CHROMA --> VDB
    PIPE --> DB2
    STORAGE --> CONSUMERS
```

---

## 9. Component Responsibility Map

| Component | Responsibility |
|-----------|---------------|
| `main.py` | FastAPI app, startup (RAG index, APScheduler), CORS |
| `database.py` | SQLAlchemy models, session factory, SQLite connection |
| `models.py` | Pydantic request/response schemas |
| `spike_alerter.py` | APScheduler job, spike detection logic, alert store |
| `ai/pipeline.py` | Orchestrates all 8 pipeline steps |
| `ai/ollama_client.py` | LLM calls: summary, draft, digest, Q&A |
| `ai/rag_engine.py` | ChromaDB build + similarity search |
| `ai/pii_masker.py` | Regex PII detection and masking |
| `ai/duplicate_detector.py` | Vector similarity duplicate check |
| `routers/tickets.py` | Ticket CRUD, draft reply, KB suggestions |
| `routers/manager.py` | Dashboard data, Q&A bot, agent stats, alerts, digest |
| `routers/insights.py` | Heatmap, SLA breakdown, sentiment trend, CSAT forecast |
| `routers/voice.py` | Audio upload, ffmpeg conversion, Whisper, Groq extraction |
| `routers/ingest.py` | Reddit/AppStore/Email ingestion triggers + status |
| `routers/solution.py` | Solution search across KB/Reddit/SO + feedback |
| `scrapers/reddit_scraper.py` | PRAW Reddit fetcher |
| `scrapers/appstore_scraper.py` | Apple RSS + Google Play scraper |
| `scrapers/email_scraper.py` | IMAP email fetcher |
| `solution_engine.py` | Multi-source solution search + ranking |
| `ingest_docs.py` | Bulk KB article loader into ChromaDB |
| `inject_customer_360.py` | Customer history seeder for demo |

---

*SupportLens · Relanto Hackathon 2026*
