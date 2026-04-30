# StockWise 📦
**AI Decision Copilot for Inventory Reordering and Waste Reduction**

StockWise is a web-based decision intelligence system for small cafes and kiosks. It converts structured inventory records into ranked actions, simulation-based trade-off analysis, and Z.AI GLM-powered explanations that help non-technical operators decide what to **restock now**, what to **buy less of**, and what to **delay**.

The MVP is grounded in a 100-day, 1,000-record sample dataset across 10 recurring inventory items, so it demonstrates practical decision support without claiming advanced forecasting or revenue prediction.

---

## ✨ Features

| Feature | What it does |
|---|---|
| **Decision Dashboard** | Latest snapshot of stock health: top urgent items, top waste-cost items, value-at-risk, average days of cover. |
| **Priority Action Board** | Ranks each item with explainable urgency and waste-risk scores and assigns one of `RESTOCK_NOW` / `BUY_LESS` / `DELAY_PURCHASE` / `MONITOR_CLOSELY`. |
| **What-If Reorder Simulator** | Test a proposed reorder quantity and see simulated coverage days, cash outlay, and risk change before placing the order. |
| **GLM Explanation Layer** | Z.AI GLM explains the recommendation in plain language using only structured metrics. JSON-validated; one strict retry; deterministic fallback if invalid. |
| **AI Decision Brief** | Asynchronously generated dashboard-level brief: Buy Today / Buy Less / Delay groups, estimated cash/waste/shortage impact, top trade-offs, and recommended order of action. |
| **AI Copilot Chat** | Grounded chat scoped to the current analysis (and optional simulation handoff). Refuses off-topic prompts. |
| **Manual Entry & CSV Upload** | Two converging input flows that share one canonical item contract before scoring. |
| **Records Management** | Review, edit, delete inventory records after upload/manual entry; recommendations refresh automatically. |
| **Persistent History** | Supabase persistence for source observations, import batches, items, suppliers, analysis runs, and snapshots. |
| **Entry History (browser)** | Local log of every CSV upload and manual entry submitted from the current browser. |

---

## 🧱 Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, pandas, httpx, Supabase Python client.
- **Frontend**: Next.js 14 (Pages Router), React 18, TypeScript, TailwindCSS, Axios, Supabase JS, Recharts, Lucide.
- **Persistence**: Supabase (Postgres + Auth). In-memory store as a fast cache, with snapshot fallback.
- **AI**: Z.AI GLM (`glm-4.5` by default) via `https://api.z.ai/api/paas/v4/chat/completions`. Mock provider available for demos without an API key.

---

## 📁 Repository Layout

```
StockWise/
├─ src/stockwise_api/            # FastAPI backend (factory: stockwise_api.api.app:create_app)
│  ├─ api/app.py                 # HTTP endpoints
│  ├─ services/                  # validation, metrics, recommendations, simulation, glm, parsing
│  ├─ contracts.py / schemas.py  # canonical input + response models
│  └─ store.py                   # InMemoryAnalysisStore + SupabaseAnalysisStore
├─ frontend/                     # Next.js app
│  ├─ src/pages                  # /, /login, /signup, /dashboard/[id], /records/[id],
│  │                             # /simulation/[id]/[itemId], /explanation/[id]/[itemId],
│  │                             # /export/[id], /history, /settings
│  ├─ src/components             # Dashboard nav, AICopilotPanel, AIDecisionBriefCard,
│  │                             # InventoryItemForm, ItemSimulation, ExplanationDrawer, common
│  └─ src/lib                    # auth, analysisSession, navigationTargets, supabase, ...
├─ supabase/migrations/          # SQL migrations for analysis snapshots and item ownership
├─ tests/                        # backend pytest suite
├─ pyproject.toml                # backend dependencies
└─ restaurant_inventory_100days.csv   # sample dataset
```

---

## ✅ Prerequisites

- **Python** ≥ 3.11
- **Node.js** ≥ 18 and **npm**
- A **Supabase project** with the migrations in `supabase/migrations/` applied (the dev project is shared via the team `.env`).
- Optional: a **Z.AI API key** if you want live GLM responses. Without it, set `GLM_MODE=mock` and the app uses a deterministic mock provider that still demonstrates the full UX.

---

## 🔐 Environment Files

Two env files are required. Both are gitignored.

### 1. Backend — `.env` (project root: `StockWise/.env`)

Loaded automatically by `load_dotenv()` in [src/stockwise_api/api/app.py](src/stockwise_api/api/app.py) when the backend starts.

```env
# ── Supabase (server-side; the SERVICE_ROLE_KEY bypasses RLS — never ship to browser) ──
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=<anon-jwt>
SUPABASE_SERVICE_ROLE_KEY=<service-role-jwt>

# Turn on Supabase persistence in the FastAPI app
STOCKWISE_SUPABASE_ENABLED=1

# ── Z.AI GLM ──
# mock = deterministic fixtures (default), live = call the real Z.AI API
GLM_MODE=mock
# Required only when GLM_MODE=live
ZAI_API_KEY=
# Optional overrides
# ZAI_BASE_URL=https://api.z.ai/api/paas/v4/chat/completions
# ZAI_MODEL=glm-4.5
# ZAI_MAX_TOKENS=1600
# ZAI_STREAM=true
# ZAI_CONNECT_TIMEOUT_SECONDS=10
# ZAI_READ_TIMEOUT_SECONDS=180

# ── Optional Supabase tuning ──
# STOCKWISE_SUPABASE_OPERATION_TIMEOUT_SECONDS=5
# STOCKWISE_SUPABASE_HTTP_TIMEOUT_SECONDS=5
```

| Variable | Required | Notes |
|---|---|---|
| `SUPABASE_URL` | ✅ | Project URL. |
| `SUPABASE_ANON_KEY` | ✅ | Public anon key. |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Server-only; bypasses RLS. **Never put this in the frontend.** |
| `STOCKWISE_SUPABASE_ENABLED` | recommended | `1` to persist; `0` to run in-memory only. |
| `GLM_MODE` | optional | `mock` (default) or `live`. |
| `ZAI_API_KEY` | required if `GLM_MODE=live` | Bearer token for Z.AI. |
| `ZAI_BASE_URL` / `ZAI_MODEL` / `ZAI_MAX_TOKENS` / `ZAI_STREAM` | optional | Override the live provider defaults. |

### 2. Frontend — `frontend/.env.local`

Read at build/dev time by Next.js. Only `NEXT_PUBLIC_*` variables ship to the browser.

```env
# Supabase (frontend - public anon key only; never include the service role key here)
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-jwt>

# Point the frontend at the local FastAPI backend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | Same project as backend. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | Public anon key only. |
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | URL of the FastAPI backend (defaults to `http://localhost:8000` if unset). |

> ⚠️ **Security**: The service role key is privileged. Keep it in the backend `.env` only. If it ever leaks, rotate it from the Supabase dashboard → Settings → API.

---

## 🛠 Installation

Clone the repo, then install backend and frontend dependencies.

### Backend

From the project root (`StockWise/`):

```bash
# create a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# install backend dependencies
pip install -e .
```

This installs `fastapi`, `uvicorn`, `pandas`, `pydantic`, `python-dotenv`, `supabase`, and `httpx` per [pyproject.toml](pyproject.toml).

### Frontend

```bash
cd frontend
npm install
```

---

## ▶️ Running the App

Run the backend and the frontend in **two separate terminals**.

### Run the backend

From the project root, with the venv activated and `.env` in place:

```bash
python -m uvicorn --factory --app-dir src stockwise_api.api.app:create_app --host 0.0.0.0 --port 8000
```

The API will be live at **http://localhost:8000** with OpenAPI docs at **http://localhost:8000/docs**.

### Run the frontend

In another terminal:

```bash
cd frontend
npm run dev
# or, if port 3000 is busy:
# npm run dev -- -p 3001
```

Open **http://localhost:3000**, sign up / log in, then either upload the bundled CSV ([restaurant_inventory_100days.csv](restaurant_inventory_100days.csv)) or use Manual Entry.

---

## 🧪 Tests & Type Checks

### Backend

```bash
pytest
```

### Frontend

```bash
cd frontend
npx tsc --noEmit   # type check
npm test            # jest unit tests
```

---

## 🌐 API Endpoints (current surface)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/analyses` | Upload a CSV; create an analysis. |
| `POST` | `/api/v1/manual-analyses` | Submit owner-friendly manual entries; create an analysis. |
| `GET`  | `/api/v1/analyses/latest` | Latest persisted analysis for the user. |
| `GET`  | `/api/v1/analyses/{analysis_id}` | Read an analysis (in-memory cache → Supabase fallback). |
| `GET`  | `/api/v1/analyses/{analysis_id}/records` | Editable records view. |
| `PATCH`| `/api/v1/analyses/{analysis_id}/items/{item_id}` | Update one record; refresh recommendations. |
| `DELETE`| `/api/v1/analyses/{analysis_id}/items/{item_id}` | Delete one record; recompute remaining set. |
| `POST` | `/api/v1/analyses/{analysis_id}/items/{item_id}/simulate` | Run a what-if reorder. |
| `POST` | `/api/v1/analyses/{analysis_id}/items/{item_id}/explanation` | GLM explanation, validated and retried, with deterministic fallback. |
| `POST` | `/api/v1/analyses/{analysis_id}/ai-chat` | Grounded AI Copilot chat. |
| `GET`  | `/api/v1/analyses/{analysis_id}/decision-brief` | Async dashboard-level AI Decision Brief. |

---

## 🚦 Daily Workflow

1. **Daily Overview** — open the Decision Dashboard for stock health, KPI cards, and the AI Decision Brief.
2. **Action Board** — sort by Date / Urgency / Waste Risk and follow `RESTOCK_NOW`, `BUY_LESS`, `DELAY_PURCHASE` recommendations.
3. **Test a Reorder** — click **Simulate** on any row to compare aggressive vs conservative quantities.
4. **Ask the Copilot** — open the AI Copilot panel for grounded follow-ups; hand off a simulation result to ask "what changed?"
5. **Review Records** — fix any data issues at `/records/{id}`; recommendations refresh automatically.
6. **Export / History** — download CSV/JSON or print to PDF from `/export/{id}`; revisit past entries at `/history`.

---

## 🔒 Out of Scope (per PRD)

- Supplier ordering automation / PO execution
- Revenue or profit forecasting
- Enterprise ERP integration
- Multi-branch stock synchronization
- IoT real-time stock sensing
- Native mobile app

---

## 🤝 Contributing

1. Create a branch off `main`.
2. Run `pytest` and `npm test` before opening a PR.
3. Keep validation, metric computation, recommendation logic, simulation, and AI integration in their existing modules — that separation is part of the maintainability requirements in the PRD.
