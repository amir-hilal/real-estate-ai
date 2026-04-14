# Phase 5: API and Containerization

> **Status:** Not Started  
> **Depends on:** Phases 1–4 complete (model serialized, prompts validated, schema locked)  
> **Blocks:** Phase 6 (UI integration)

---

## Purpose

This phase assembles all the components produced in Phases 1–4 into a deployable, testable FastAPI application. The API is the seam between the ML/LLM logic and the outside world. After this phase, the full pipeline runs end-to-end via HTTP requests.

The goal here is not to build a production-grade API. The goal is to build a clean, correct, and understandable one. Every endpoint has a clear responsibility. Every error returns a useful response. The system runs in Docker with one command.

---

## API Responsibilities

The API must:
- Accept a plain-English property description and run it through the full pipeline
- Validate inputs and return structured errors — never crash silently
- Load the model artifact at startup, not at request time
- Load prompts from files at startup or per-request with caching
- Return a structured JSON response for every outcome (success and failure)
- Expose a health check endpoint

The API must not:
- Perform training or fine-tuning
- Write to the model artifact
- Hardcode any prompt content
- Store user requests or responses (no persistence layer in MVP)

---

## Endpoint Design

### `GET /health`
**Purpose:** Liveness and readiness check  
**Returns:**
```json
{
  "status": "ok",
  "model_loaded": true,
  "stats_loaded": true
}
```
**Returns 503** if model is not loaded

---

### `POST /extract`
**Purpose:** Run Stage 1 only — extract features from text  
**Use case:** Testing Stage 1 in isolation; UI pre-validation  
**Request:**
```json
{ "description": "3-bedroom house built in 1995 with a 2-car garage..." }
```
**Response (success):**
```json
{
  "status": "complete",
  "features": { "bedroom_abv_gr": 3, "year_built": 1995, ... },
  "missing_required_fields": []
}
```
**Response (partial extraction):**
```json
{
  "status": "partial",
  "features": { "bedroom_abv_gr": 3, ... },
  "missing_required_fields": ["gr_liv_area", "neighborhood"]
}
```
**Response (parse failure):**
```json
{
  "status": "error",
  "error_code": "EXTRACTION_PARSE_FAILURE",
  "message": "LLM did not return valid JSON. Please try again with a more detailed description."
}
```

---

### `POST /predict`
**Purpose:** Run the full pipeline — extract → validate → predict → explain  
**Request (initial, text-only):**
```json
{ "description": "3-bedroom house built in 1995..." }
```
**Request (supplemented, after user fills missing fields):**
```json
{
  "description": "3-bedroom house built in 1995...",
  "supplemental_features": {
    "gr_liv_area": 1800,
    "neighborhood": "NridgHt"
  }
}
```
**Response (success):**
```json
{
  "status": "complete",
  "features": { ... },
  "prediction_usd": 243500,
  "explanation": "Based on the details you provided, this property is estimated at $243,500..."
}
```
**Response (requires supplemental input):**
```json
{
  "status": "incomplete",
  "features": { ... },
  "missing_required_fields": ["gr_liv_area", "neighborhood"],
  "message": "Please provide the missing fields to continue."
}
```

---

## Request / Response Contracts

- All request bodies are validated by Pydantic models
- All responses include a `status` field: `"complete"`, `"partial"`, `"incomplete"`, or `"error"`
- Error responses always include `error_code` (machine-readable) and `message` (human-readable)
- `prediction_usd` is always an integer (rounded to nearest dollar) — not a float
- Feature values in responses use the schema field names from `PropertyFeatures`

---

## Model Loading Expectations

- The serialized model pipeline (`model.pkl`) is loaded once at application startup via FastAPI's `lifespan` context
- The training statistics file (`training_stats.json`) is loaded at startup and held in memory
- If the model file is missing or corrupt at startup, the application raises a fatal error and does not start
- The model path must be configurable via environment variable `MODEL_PATH`
- The stats file path must be configurable via environment variable `STATS_PATH`

**Why not load per-request?**  
Model deserialization is expensive (100ms–500ms depending on model size). Loading once at startup amortizes this cost. This is a standard ML serving pattern.

---

## Containerization Expectations

### Docker requirements
- A `Dockerfile` at the project root
- A `docker-compose.yml` at the project root
- The application starts with: `docker-compose up`
- No manual pip install or environment activation required inside the container
- Model artifact and stats file must be available inside the container (either COPY'd into image or mounted)

### Environment variable handling
- `OPENAI_API_KEY` (or equivalent LLM key): passed via `.env` file referenced in `docker-compose.yml`
- `MODEL_PATH`: default to `/app/ml/artifacts/model.pkl`
- `STATS_PATH`: default to `/app/ml/artifacts/training_stats.json`
- `STAGE1_PROMPT_PATH`: default to `/app/prompts/stage1_extraction_v1.md`
- `STAGE2_PROMPT_PATH`: default to `/app/prompts/stage2_explanation_v1.md`

### Security note
- `.env` files must be listed in `.gitignore`
- API keys must never be hardcoded in the `Dockerfile` or `docker-compose.yml`

---

## Observability Basics

For MVP, observability means: structured logging, not metrics dashboards.

- Log every request: endpoint, timestamp, input length, response status
- Log every LLM call: prompt version, model used, response latency, success/failure
- Log every model inference: feature count, prediction value, latency
- All logs go to stdout — Docker captures them
- Use Python's `logging` module with a structured format (JSON preferred for production-readiness)

**Not required for MVP:**
- Prometheus metrics
- Distributed tracing (OpenTelemetry)
- Centralized log aggregation (Elasticsearch, Loki)

---

## Integration Testing Plan

Before Phase 5 is complete, run the following end-to-end tests:

| Test | Method | Expected Outcome |
|------|--------|-----------------|
| Health check | `GET /health` | 200 OK, `model_loaded: true` |
| Full happy path | `POST /predict` with a complete description | 200, prediction + explanation |
| Partial extraction → supplement | `POST /predict` → missing fields → supplement → complete | Two-step success |
| Empty input | `POST /predict` with `description: ""` | 422 validation error |
| Non-property input | `POST /predict` with `description: "hello"` | 422 or structured extraction failure |
| Model not found | Start app with wrong `MODEL_PATH` | App fails to start with clear error |

---

## Exit Criteria

Phase 5 is complete only when ALL of the following are true:

1. [ ] All endpoints are implemented and return documented response shapes
2. [ ] Model is loaded at startup; health check confirms it
3. [ ] All 6 integration tests pass
4. [ ] `docker-compose up` starts the application with no errors
5. [ ] All secrets are passed via environment variables, never hardcoded
6. [ ] Structured logs are emitted for requests and LLM calls
7. [ ] Full pipeline test (description → prediction + explanation) works end-to-end via curl

---

*The API is a contract. Every endpoint must be documented, tested, and consistent.*
