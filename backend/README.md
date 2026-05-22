# AI Chatbot — Backend

FastAPI backend for the AI chatbot. Uses LangChain + LangGraph for RAG and
multi-step reasoning, ChromaDB for vector storage, Supabase for persistence,
and Firebase Authentication for identity.

---

## Folder structure

```
backend/
├── app/
│   ├── main.py               # App factory, middleware wiring, exception handlers
│   ├── api/
│   │   └── v1/
│   │       └── health.py     # GET /api/v1/health
│   ├── core/
│   │   ├── config.py         # Pydantic settings — reads .env
│   │   └── logging.py        # Structured stdout logging
│   ├── middleware/
│   │   ├── error_handler.py  # Catches unhandled exceptions → JSON 500
│   │   └── request_logger.py # Logs method / path / status / duration
│   ├── models/               # SQLModel / ORM table definitions (Phase 3+)
│   ├── schemas/
│   │   ├── base.py           # Generic ApiResponse[T] envelope
│   │   └── health.py         # HealthData schema
│   ├── services/
│   │   └── base.py           # AbstractBaseService (Phase 3+)
│   └── utils/
│       ├── exceptions.py     # Typed HTTP exceptions (AppException subclasses)
│       └── responses.py      # success() / error() JSONResponse helpers
├── .env                      # Local secrets (git-ignored)
├── .env.example              # Committed template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Quick start

### 1. Prerequisites

- Python 3.11+
- Git

### 2. Clone and enter directory

```bash
cd d:\CHATBOT\backend
```

### 3. Create and activate virtual environment

```bash
# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate

# Windows (Git Bash / WSL)
python -m venv .venv
source .venv/Scripts/activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment

```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS / Linux
```

Edit `.env` and fill in the required values (see table below).

### 6. Run the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Verify

| URL | Expected |
|-----|----------|
| `http://localhost:8000/api/v1/health` | `{"success":true,"data":{"status":"ok",...}}` |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc UI |

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_ENV` | no | `development` / `production` |
| `APP_HOST` | no | Bind host (default `0.0.0.0`) |
| `APP_PORT` | no | Bind port (default `8000`) |
| `LOG_LEVEL` | no | `debug` / `info` / `warning` |
| `CORS_ORIGINS` | no | Comma-separated allowed origins |
| `SUPABASE_URL` | Phase 3 | Supabase project URL |
| `SUPABASE_ANON_KEY` | Phase 3 | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Phase 3 | Supabase service role key |
| `FIREBASE_PROJECT_ID` | Phase 4 | Firebase project ID |
| `FIREBASE_PRIVATE_KEY` | Phase 4 | Firebase service account private key |
| `FIREBASE_CLIENT_EMAIL` | Phase 4 | Firebase service account email |
| `OPENAI_API_KEY` | Phase 5 | OpenAI API key |
| `LANGCHAIN_API_KEY` | Phase 5 | LangSmith tracing key |
| `CHROMA_PERSIST_DIR` | Phase 5 | Directory for ChromaDB data |

---

## Response envelope

Every endpoint returns the same JSON shape:

```json
// success
{ "success": true, "data": { ... }, "error": null }

// failure
{ "success": false, "data": null, "error": { "code": "NOT_FOUND", "message": "..." } }
```

Use `success()` / `error()` from `app.utils.responses` in route handlers.
Raise `NotFoundException`, `UnauthorizedException`, etc. from `app.utils.exceptions` — the
global handler converts them automatically.

---

## Phases

| Phase | Scope |
|-------|-------|
| 1 | FastAPI skeleton, config, health route |
| **2** | **Clean architecture: middleware, schemas, utils, services** |
| 3 | Supabase integration, database models |
| 4 | Firebase Auth middleware, protected routes |
| 5 | ChromaDB + LangChain RAG pipeline, document ingestion |
| 6 | LangGraph multi-step chat workflow |
| 7 | Frontend (Next.js) |
| 8 | Production deployment (Vercel + Render) |
