# SupportLens 🔍
### AI-Powered Support Intelligence & Agent Productivity Platform
*Relanto Hackathon 2026*

> **"Transforming support departments from cost centers into efficiency engines."**  
> SupportLens leverages local Small Language Models (SLMs) and modern web scrapers to intelligently prioritize tickets, automate drafted responses grounded in real-time documentation, and provide team leads with conversational data intelligence.

---

## 🚀 Interactive Quick Start

This repository contains a fully automated setup that will configure the backend SQLite database, seed the AI enrichment engine, scrape Stripe documentation, and launch the web server automatically.

### Prerequisites
- **Python 3.9+** (Fully compatible with Windows)
- **Node.js 18+**
- **Ollama** running locally (Ensure you have pulled `llama3.2:3b`)
- **Groq API Key** (A free API key from console.groq.com)

### Installation & Launch in 2 Steps

#### 1. Setup Environment
Create a `.env` file in `support-lens/backend/.env` with the following variables:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
DATABASE_URL=sqlite:///./support_lens_stripe.db
GROQ_API_KEY=your_groq_api_key_here
```

#### 2. Run the Automatic Installer & Server
We have created one-click installers at the root:
*   **Double-click `support-lens/install.bat`** (installs all python libraries, playwriters, and frontend npm packages)
*   **Double-click `support-lens/start.bat`** (launches both frontend on `http://localhost:5173` and backend on `http://localhost:8000` automatically)

---

## ✨ Features Engineered

### 🎯 1. Agent Workspace & Urgency Queue
*   **Intelligent Prioritization**: A live queue sorted by a compound, weighted **Urgency Score (0-100)** calculated using customer tier, intent (e.g., churn or billing issues), and real-time SLA deadlines.
*   **Live Countdown Timers**: Dynamic, visual SLA timers that update in real-time.
*   **Emotion Intensity Detection**: Analyzes customer frustration levels on a scale of `1-10` with emotional tagging.

### ✉️ 2. One-Click Native Mail Client Connector
*   **Seamless Hand-off**: Integrated a customized `mailto:` anchor. When agents hit **"Open in Mail Client"**, it launches their native system mail client (Outlook, Apple Mail, Gmail).
*   **Metadata Auto-Population**: Pre-fills the **To:** address with the customer's exact email, sets the subject to `Re: [Ticket Subject]`, and embeds the custom AI-grounded draft reply into the body instantly.

### 🧠 3. Live Web-Scraped RAG Engine (Stripe Integration)
*   **No General-Knowledge Hallucinations**: Standard RAG approaches suffer when documentation changes. We built an automated Playwright-based scraper (`ingest_docs.py`) that indexes live, public documentation pages directly into a local **ChromaDB vector store**.
*   **Dynamic Source Citing**: Grounded replies cite the exact web URL scraped at the bottom of the response card with a visual green confidence indicator.

### 📊 4. Manager Dashboard & Analytics
*   **Hourly Issue Heatmaps**: 7-day x 24-hour visual grids identifying hourly ticketing volume.
*   **SLA Trackers**: Visual breakdowns of Safe vs. At-Risk vs. Breached tickets, segmented per agent.
*   **CSAT Forecasts**: High-level sentiment predictive index factoring in active escalations and historical performance.
*   **Manager Q&A Bot**: An AI-powered assistant allowing managers to query complex statistics in plain English (e.g., *"Why did CSAT drop this week?"* or *"Who is our busiest agent?"*).

---

## 🛠️ The Technical Architecture

```
                    [ Live Customer Support Ticket ]
                                   │
                                   ▼
                   ┌──────────────────────────────┐
                   │  1. PII Regex & spaCy Mask   │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │  2. Emotion & Intent Tagging │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ 3. RAG ChromaDB Doc Match    │  ◄── [ Playwright Web Scraper ]
                   └──────────────┬───────────────┘       (Scrapes docs.stripe.com)
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ 4. Llama 3.1 & Groq LLM Path │
                   └──────────────┬───────────────┘
                                  │
                                  ▼
                    [ Grounded Draft Reply Card ]
                                  │
                                  ▼
                     [ Open in Mail Client Link ]
```

---

## 🛡️ Trust, Safety & Guardrails
1.  **PII Sanitization**: Completely redacts customer names, phone numbers, and emails using advanced spaCy NER before passing details to any third-party APIs.
2.  **Strict Confidence Check**: If document similarity drops below `0.35`, the system blocks the draft and flags it with an amber badge warning.
3.  **Autonomous Lockout**: High-anger, churn-risk, or Enterprise-tier issues trigger a "Human Gate" that automatically prevents auto-sending and routes straight to human intervention.
