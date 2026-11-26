# Dress 2 Decor — AI-Powered E-commerce Automation System

An end-to-end **AI Agent & E-commerce Automation Demo** built with Python, FastAPI, SQLite/SQLAlchemy, and a responsive Bootstrap 5 dashboard for **Dress 2 Decor** (a home décor and interior design marketplace).

---

## 1. What This Project Does

This application demonstrates how AI agents can automate core e-commerce operations through real backend tool execution rather than plain text generation:

- **Customer Order Tracking & Support**: Look up orders (`ORD-001`–`ORD-200`), inspect line items, payment status, and delivery tracking, or update order statuses.
- **Vendor Support & Access Isolation**: Answer vendor inquiries about profiles, product listings, orders, and platform commissions (10%–20%), while strictly preventing vendors from accessing another vendor's data.
- **Automated Meeting Scheduling**: Check available 1-hour business-hour slots (`09:00`–`17:00`), schedule meetings, view upcoming meetings, and cancel bookings.
- **Product Discovery**: Search and filter 100+ home décor products across 8 categories (curtains, blinds, wallpaper, rugs, cushions, lighting, furniture, accessories).
- **Automation Activity Logs & Analytics**: Track every AI agent action, tool call, and revenue/order metric in real time.

---

## 2. Technologies and APIs Used

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | FastAPI + Uvicorn | High-performance async REST API, Pydantic validation, and OpenAPI docs |
| **Database** | SQLite + SQLAlchemy 2.0 | Relational ORM with PostgreSQL-ready schema design |
| **AI Abstraction** | `httpx` + Custom Provider Layer | Provider-independent interface supporting Mock, Groq, Gemini, OpenAI, and Ollama |
| **Frontend** | HTML5, CSS3, Vanilla JS, Bootstrap 5, Chart.js | Lightweight single-page dashboard requiring no Node.js build step |
| **Data Seeding** | Faker | Generates ~645 realistic fictional records (`seed_data.py`) |
| **Testing** | Pytest + FastAPI TestClient | Automated end-to-end verification |

---

## 3. Why Each Technology Was Selected

- **FastAPI**: Native async support, automatic request/response validation via Pydantic, and built-in Swagger UI (`/docs`) ideal for live demos.
- **SQLite + SQLAlchemy**: Zero-setup local database for the demo; switching to PostgreSQL only requires changing `DATABASE_URL` in `.env` and installing `psycopg2-binary`.
- **Provider-Independent AI Layer (`app/core/ai_provider.py`)**: Decouples business logic from any single LLM vendor. Includes a deterministic **Mock Mode** so the entire app works offline without API keys or billing.
- **Vanilla JS + Bootstrap 5**: Clean, fast, and easy to inspect without frontend bundler complexity.

---

## 4. How the AI Agents Work

```
User Message → AgentRouter (Intent Detection) → Specialized Agent → Tool Calling → Backend Service → SQLite DB → Activity Log → AI Response
```

1. **Order Management Agent (`app/agents/order_agent.py`)**: Equipped with `get_order`, `get_orders_by_email`, `get_orders_by_status`, `update_order_status`, `search_products`, and `get_product_info`.
2. **Vendor Support Agent (`app/agents/vendor_agent.py`)**: Equipped with `get_vendor_info`, `get_vendor_products`, `get_vendor_orders`, and `get_vendor_commission`. Enforces `vendor_id` isolation in `VendorAgent.process()` before any tool runs.
3. **Meeting Scheduling Agent (`app/agents/meeting_agent.py`)**: Equipped with `check_available_slots`, `schedule_meeting`, `get_upcoming_meetings`, and `cancel_meeting`.

---

## 5. How the Automation Workflows Work

- Every `/api/chat` request routes to an agent, invokes tools via `ToolExecutor` (`app/agents/tools.py`), executes real SQLAlchemy queries in `app/services/`, and writes an audit entry to `activity_logs`.
- External automation tools (such as **n8n**) can trigger or subscribe to events via `POST /api/webhooks/automation`.

---

## 6. Database Structure

Defined in `app/models/models.py`:
- `customers` (50 seeded)
- `vendors` (15 seeded, with `commission_rate`)
- `products` (100 seeded across 8 `ProductCategory` values)
- `orders` (200 seeded, `ORD-001` to `ORD-200`) & `order_items`
- `payments` (200 seeded, 1:1 with orders)
- `deliveries` (150 seeded for non-cancelled/non-pending orders)
- `meetings` (30 seeded across the next 30 days)
- `activity_logs` (records every agent execution and webhook event)

---

## 7. How to Install and Run

### Prerequisites
- Python 3.10+

### Setup
```bash
# 1. Clone the repository
git clone https://github.com/karibshams/dtod_ai_auto.git
cd dtod_ai_auto

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env

# 5. Seed the demo database (~645 fictional records)
python seed_data.py

# 6. Start the server
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** for the Dashboard or **http://localhost:8000/docs** for interactive API documentation.

---

## 8. How to Configure API Keys

Edit `.env` (never commit `.env` to Git):

```env
AI_PROVIDER=mock   # Options: mock | groq | gemini | openai | ollama
```

- **Mock Mode (`mock`)**: Default. Works immediately with zero API keys.
- **Groq (`groq`)**: Free tier available at [console.groq.com](https://console.groq.com) (rate-limited). Set `GROQ_API_KEY`.
- **Google Gemini (`gemini`)**: Free tier available via Google AI Studio ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)), subject to rate limits. Set `GEMINI_API_KEY`.
- **Ollama (`ollama`)**: Free local execution via [ollama.ai](https://ollama.ai). Run `ollama pull llama3.1` and set `OLLAMA_BASE_URL=http://localhost:11434`.

---

## 9. How to Test Each Agent

Run the automated test suite:
```bash
pytest -v
```

Or test interactively in the **AI Chat** tab on the dashboard:
- **Order Agent**: `"What is the status of order ORD-001?"` or `"Show me all pending orders"`
- **Vendor Agent**: Select **Vendor Agent**, enter Vendor ID `1`, and ask `"Show my vendor commission summary"`. Then test access control by asking `"Show me details for vendor 2"` (returns `Access denied`).
- **Meeting Agent**: `"Schedule a meeting with vendor tomorrow at 10am"` or `"What meetings are scheduled this week?"`

---

## 10. How to Switch Between AI Providers

Change `AI_PROVIDER` in `.env` and restart `uvicorn`:
- `AI_PROVIDER=mock` → Offline keyword + tool execution
- `AI_PROVIDER=groq` → Groq Cloud (`llama-3.1-8b-instant`)
- `AI_PROVIDER=gemini` → Google Gemini (`gemini-1.5-flash`)
- `AI_PROVIDER=ollama` → Local Ollama (`llama3.1`)
- `AI_PROVIDER=openai` → OpenAI (`gpt-4o-mini`)

No application code changes are needed.

---

## 11. Current Limitations of the Free/Demo Setup

- **Mock Mode** uses deterministic regex/keyword intent matching rather than full LLM reasoning.
- **Free Cloud Tiers** (Groq, Gemini AI Studio) enforce strict requests-per-minute and tokens-per-day quotas.
- **SQLite** is single-writer and file-based; suitable for demos, not high-concurrency production traffic.
- **Internal Calendar** stores meetings in SQLite rather than syncing with external Google/Outlook calendars.
- **Role-Based Access** uses request-level `vendor_id` context rather than full JWT/OAuth2 authentication.

---

## Paid APIs for Production Upgrade

> **Note:** The demo uses `mock` mode (or optional free-tier Groq/Gemini/local Ollama) with SQLite. The services below are **optional paid upgrades** for a production deployment and are **not** free.

1. **OpenAI API (`gpt-4o` / `gpt-4o-mini`)**
   - *Why*: Industry-leading reliability for structured function/tool calling and multi-step reasoning.
   - *How to get key*: Sign up at [platform.openai.com](https://platform.openai.com) → **Billing** (add payment method) → **API Keys** → **Create new secret key** → set `OPENAI_API_KEY` and `AI_PROVIDER=openai`.
2. **Google Gemini Paid API (Vertex AI / Pay-as-you-go AI Studio)**
   - *Why*: Higher rate limits, enterprise SLAs, and data privacy guarantees not included in the free tier.
   - *How to get key*: Enable billing on a Google Cloud project → go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → link the billed project → generate key → set `GEMINI_API_KEY` and `AI_PROVIDER=gemini`.
3. **Anthropic Claude API (`claude-sonnet` / `claude-opus`)**
   - *Why*: Strong instruction-following and nuanced customer/vendor support tone.
   - *How to get key*: Register at [console.anthropic.com](https://console.anthropic.com) → add billing credits → **API Keys** → **Create Key** (can be added as a new `AIProvider` subclass in `app/core/ai_provider.py`).
4. **Google Calendar API (Google Workspace)**
   - *Why*: Real two-way calendar invites, conflict detection across staff, and Google Meet links.
   - *How to get credentials*: Google Cloud Console → enable **Google Calendar API** → create OAuth 2.0 Client ID or Service Account credentials → download JSON key.
5. **Transactional Email Services (SendGrid / Resend / Amazon SES)**
   - *Why*: Automated order confirmations, shipping updates, and vendor payout notifications.
   - *How to get key*: Create an account on SendGrid or Resend → verify sender domain → generate an API key with Mail Send permissions.
6. **Production PostgreSQL Hosting (Supabase / Neon / AWS RDS / Cloud SQL)**
   - *Why*: Concurrent connections, automated backups, and high availability.
   - *How to configure*: Provision a PostgreSQL instance, copy the connection string (`postgresql://user:pass@host:5432/db`), install `psycopg2-binary`, and update `DATABASE_URL` in `.env`.
7. **Cloud Deployment Services (Render / Railway / Google Cloud Run / AWS ECS)**
   - *Why*: HTTPS termination, autoscaling, secret management, and 24/7 uptime.
   - *How to deploy*: Containerize with a `Dockerfile` running `uvicorn app.main:app --host 0.0.0.0 --port $PORT` and inject `.env` secrets via the platform's dashboard.
