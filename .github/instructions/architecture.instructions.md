---
applyTo: "**"
---

# Architecture Instructions

These instructions define the architectural principles and structural rules for all code in this project.

---

## Architecture Philosophy

**Prefer the simplest design that correctly solves the defined problem.**

Complexity is a cost, not a feature. Every additional service, abstraction layer, or framework is a maintenance burden. Add complexity only when a specific, documented problem demands it.

---

## System Architecture (MVP)

The MVP is a single-process FastAPI application:

```
FastAPI (one process, one container)
├── POST /predict     ← full pipeline
├── POST /extract     ← Stage 1 only
└── GET /health       ← liveness check

Pipeline stages (called in sequence within a request):
1. Stage 1: LLM extraction (external API call)
2. Pydantic validation
3. Missing-field check
4. Stage 2: ML prediction (local model loaded at startup)
5. Stage 3: LLM explanation (external API call)
```

---

## Structural Rules

### Dependency Rules
- No circular imports
- Dependency direction: routes → services → model/LLM clients → schemas
- No business logic in route handlers — route handlers call service functions
- No direct model loading in route handlers — model is loaded at startup and injected

### Service Layer Design
- Each pipeline stage should be implemented as a discrete function or class
- Stage 1 (extraction), Stage 2 (prediction), and Stage 3 (explanation) must be independently testable
- Functions that call external services (LLM API) must accept the client as a parameter for testability

### Configuration
- All configuration comes from environment variables via a `Settings` class (Pydantic BaseSettings)
- No configuration in code — no hardcoded paths, model names, or prompt file names
- Defaults are acceptable only for non-secret, non-sensitive settings (e.g., default port = 8000)

### Model Loading
- The serialized ML model pipeline is loaded once at application startup
- Use FastAPI's `lifespan` async context manager for startup/shutdown
- If the model file is missing at startup, the application must fail immediately with a clear error message
- The model must not be loaded inside a request handler

### Error Handling Architecture
- All expected failure modes return structured JSON responses (never expose raw tracebacks)
- Use a consistent error response schema: `{ "status": "error", "error_code": "...", "message": "..." }`
- HTTP status codes must be semantically correct:
  - 200 for success or partial success (with status field distinguishing)
  - 422 for validation errors or unparseable LLM output
  - 500 for unexpected server errors
  - 503 if model is not loaded

---

## What Is Explicitly Not in the Architecture

| Component | Why excluded | Document |
|-----------|-------------|---------|
| Database / ORM | No persistence needed for MVP | ADR-003 |
| Celery / Redis / task queue | Sync processing is acceptable for MVP | ADR-002 |
| Authentication middleware | No external users in MVP | ADR-003 |
| Message bus / event streaming | No fan-out requirements | future-considerations.md |
| Separate microservices | One service is correct at this scale | future-considerations.md |
| Object storage (S3) | Local filesystem is sufficient for MVP | future-considerations.md |

---

## File Organization (When Code Is Written)

```
real-estate-ai/
├── app/                       ← FastAPI application (created in Phase 5)
│   ├── main.py                ← App factory + lifespan
│   ├── config.py              ← Pydantic BaseSettings
│   ├── routes/                ← Route handlers only (thin)
│   ├── services/              ← Pipeline stage implementations
│   ├── schemas/               ← Pydantic models (PropertyFeatures, response models)
│   └── clients/               ← LLM client wrappers
├── prompts/                   ← Versioned prompt files (not source code)
├── ml/
│   ├── eda.ipynb
│   ├── model_training.ipynb
│   └── artifacts/             ← model.pkl, training_stats.json
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Synchronous- vs Async-Aware FastAPI

FastAPI supports both sync and async route handlers. For this project:
- Use `async def` for route handlers (FastAPI standard)
- LLM API calls should use async clients if available (e.g., `openai.AsyncOpenAI`)
- ML model inference is synchronous (scikit-learn is not async-capable) — run it via `asyncio.run_in_executor` if necessary to avoid blocking the event loop on long inference

---

## Docker Architecture

Single-container MVP:
- One `Dockerfile` builds a Python image with all dependencies
- One `docker-compose.yml` runs it with environment variables from `.env`
- Model artifact is either COPY'd into the image at build time or mounted via a volume
- No separate containers for ML, LLM, API, or UI

---

## When to Add an ADR

Add a new ADR entry (`docs/decisions/architecture-decision-records.md`) when:
- You choose one technology over one or more alternatives
- You decide to exclude a typically present component (auth, database, etc.)
- A previous decision is being revisited or reversed
- A significant structural change is made to the codebase

Do not add ADRs for trivial decisions (e.g., variable naming, minor refactors).
