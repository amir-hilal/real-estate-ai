# Current Project Status

> **Update this file whenever you start or complete a phase, make a major decision, or hit a blocker.**  
> **This is the first file a returning engineer (including future-you) should read.**

---

## Current Phase

**Phase 6 — UI**  
Status: **In Progress**

---

## What Is Done

- [x] Project concept defined and summarized
- [x] `README.md` created with full overview, scope, and definition of done
- [x] `docs/context/project-brief.md` — engineering description of the full pipeline
- [x] `docs/context/requirements.md` — all functional, non-functional, and operational requirements
- [x] `docs/context/assumptions-and-open-questions.md` — all current assumptions and unknowns
- [x] `docs/context/future-considerations.md` — post-MVP features clearly separated
- [x] `docs/phases/` — all 7 phase documents created with objectives, checklists, and exit criteria
- [x] `docs/decisions/architecture-decision-records.md` — ADR-001 through ADR-007 recorded
- [x] `docs/checklists/mvp-master-checklist.md` — full end-to-end checklist created
- [x] `docs/roadmap.md` — phased execution roadmap table created
- [x] `.github/instructions/` — Copilot instruction files created for all categories
- [x] `.copilot/skills/` — project skill/context files created
- [x] **Phase 1 complete** — `ml/eda.ipynb` fully executed; all 10 unknowns (U-01–U-10) resolved; 12-feature schema finalized (4 required + 8 optional); all key decisions documented
- [x] **Phase 2 complete** — `ml/model_training.ipynb` fully executed; LightGBM trained (Test MAE $17,936, R² 0.8885); `ml/artifacts/model.joblib` and `ml/artifacts/training_stats.json` saved and verified; ADR-006 (LightGBM) added
- [x] **Phase 3 complete** — All extraction components built, tested, and passing:
  - [x] `prompts/extraction_v1.md` — Stage 1 prompt with guardrail, enum mappings, 3 few-shot examples
  - [x] `app/clients/llm.py` — async LLM client factory (Ollama dev / Groq prod via `openai` SDK)
  - [x] `app/services/extraction.py` — full validation chain with retry logic
  - [x] `app/schemas/property_features.py` — Pydantic model with `Literal` enum types for `Neighborhood` and `Exterior1st`
  - [x] `app/schemas/responses.py` — `ExtractionResult`, `ErrorResponse`, `PredictionResponse`
  - [x] `app/services/prediction.py` — ML inference service
  - [x] `app/config.py` — dual-provider settings (Ollama/Groq)
  - [x] `app/main.py` — FastAPI app with lifespan, `/health` endpoint
  - [x] `tests/test_extraction.py` — 26 unit tests (mocked LLM, <1s)
  - [x] `tests/test_extraction_integration.py` — 11 integration tests (T01–T10 against Ollama, all passing)
  - [x] `pyproject.toml` — pytest config with `asyncio_mode = "auto"`
  - [x] ADR-007 (Ollama + Groq providers) added
- [x] **Phase 4 complete** — All explanation components built, tested, and passing:
  - [x] `prompts/explanation_v1.md` — Stage 3 prompt with grounding, anti-hallucination rules, vocabulary restriction, price-bracket instructions
  - [x] `app/services/explanation.py` — `generate_explanation()`, `build_explanation_prompt()`, `_format_property_lines()`; `ExplanationError` fallback
  - [x] `ml/artifacts/training_stats.json` — extended with `top_features` (LightGBM gain importance ranking)
  - [x] `tests/test_explanation.py` — 20 unit tests (mocked LLM, <1s)
  - [x] `tests/test_explanation_integration.py` — 5 evaluation scenarios E01–E05 against Ollama, all passing
  - [x] Total test suite: 62 tests passing (46 unit + 16 integration)

- [x] **Phase 5 in progress** — Routes, Dockerfile, docker-compose created; 61 unit tests passing:
  - [x] `app/routes/extract.py` — `POST /extract` handler (Stage 1 only)
  - [x] `app/routes/predict.py` — `POST /predict` handler (full pipeline)
  - [x] `app/main.py` — updated to register routes; `/health` returns `stats_loaded` too
  - [x] `app/schemas/responses.py` — `ExtractResponse`, `PredictResponse` added; `PredictionResponse` replaced
  - [x] `app/services/prediction.py` — `_FEATURE_COLUMNS` derived from schema (R-06 resolved)
  - [x] `tests/test_routes.py` — 15 route unit tests (mocked services, <1s)
  - [x] `tests/test_api_integration.py` — 6 HTTP integration tests (full pipeline via ASGITransport + real Ollama + real model, all passing)
  - [x] `Dockerfile` — multi-stage build (builder + runtime), non-root user
  - [x] `docker-compose.yml` — single container, env_file, healthcheck
  - [x] Structured logs added — request entry/exit in routes, LLM call latency in clients/llm.py
  - [x] Docker build verified — `docker compose build` succeeded; `docker compose up -d` started container; `GET /health` → `{"status":"ok","model_loaded":true}`; `POST /predict` returned `prediction_usd: 256855` with full LLM explanation

- [x] **Phase 5 complete** — all 7 exit criteria satisfied

- [x] **Phase 6 in progress** — React CDN UI built and running in Docker:
  - [x] `app/static/index.html` — React 18 + Babel CDN + Tailwind Play CDN; single self-contained file, no npm/build step
  - [x] `app/routes/ui.py` — `GET /` returns the HTML file as HTMLResponse; no new Python dependencies
  - [x] `app/main.py` — UI router registered
  - [x] Conversational UI feel — natural-language copy, 3-stage loading ("Thinking...", "Studying the market...", "Interpreting results...")
  - [x] Happy path verified in browser: describe → stage loader → prediction card + explanation + collapsible details
  - [x] UI verified inside Docker container at http://localhost:8000
  - [ ] Missing fields form not yet explicitly tested with a partial description
  - [ ] Error states not yet all explicitly triggered in browser

## What Is Not Started

- [ ] Missing fields + error state UI testing (Phase 6 remaining)
- [ ] Phase 6b — streaming explanation via SSE

---

| ID | Blocker | Impact | Resolution Path |
|----|---------|--------|----------------|
| — | None | — | — |

---

## Next Actions (in order)

1. **Test missing fields flow** — submit a partial description (omit neighborhood and GrLivArea) to trigger Step 2a, verify form renders and second submission completes
2. **Test all error states** — empty submit, non-property description, and simulate 500 to check error cards
3. **Complete Phase 6 exit criteria** — check off items 2 and 4 once tested
4. **Phase 6b** — implement `/predict/stream` SSE endpoint + streaming UI component

---

## Decisions Pending

| ID | Decision | Required By | Status |
|----|----------|------------|--------|
| D-01 | Log-transform `SalePrice` or not | Phase 2 (training) | ✅ **Resolved** — `np.log1p()` before training; `np.expm1()` on predictions |
| D-02 | Final feature shortlist (10–20 features) | Phase 2 (schema) | ✅ **Resolved** — 12 features: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`, `TotalBsmtSF`, `GarageCars`, `FullBath`, `YearRemodAdd`, `Fireplaces`, `LotArea`, `MasVnrArea`, `Exterior1st` |
| D-03 | Required vs. optional feature classification | Phase 3 (schema lock) | ✅ **Resolved** — Required: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`. Optional: remaining 8. |
| D-04 | Which LLM provider and model to use | Phase 3 | ✅ **Resolved** — Ollama `phi4-mini` (dev) + Groq `llama-3.3-70b-versatile` (prod). See ADR-007. |
| D-05 | Baseline model MAE target | Phase 2 evaluation | ✅ **Resolved** — Baseline MAE = $59,568 (`DummyRegressor` median). Final model target: MAE < $30,000. |
| D-06 | Final endpoint structure: one combined `/predict` or separate stage endpoints | Phase 5 | ✅ **Resolved** — Two endpoints: `POST /predict` (full pipeline) and `POST /extract` (Stage 1 only). No separate `/explain` endpoint. |

---

## Recent Activity

| Date | Activity |
|------|----------|
| 2026-04-15 | Phase 6 in progress — React CDN UI built (`app/static/index.html`); `GET /` route added; conversational UI with 3-stage loading (Thinking / Studying market / Interpreting); happy path verified in browser and in Docker container |
| 2026-04-15 | Phase 5 complete — Docker image built (`real-estate-ai-api`); `docker compose up -d` started container; `GET /health` confirmed model loaded; `POST /predict` returned full pipeline result (`prediction_usd: 256855` + LLM explanation); all 7 exit criteria checked off; `OLLAMA_BASE_URL` override added to `docker-compose.yml` for host.docker.internal routing |
| 2026-04-16 | Phase 5 substantially complete — 6 HTTP integration tests passing (A1–A6 in `tests/test_api_integration.py`); structured logging added to routes; phase-05 exit criteria 1–3 and 5–6 checked; Docker verification deferred (WSL2 Docker Desktop not enabled) |
| 2026-04-15 | A-12 confirmed (JSON mode reliable); A-15 revised (three-step architecture is a fundamental constraint, not a maintainability preference); R-04 MITIGATED; R-06 MITIGATED |
| 2026-04-14 | Phase 4 complete — explanation prompt, explanation service, 20 unit + 5 integration tests (E01–E05), all passing; `training_stats.json` extended with `top_features`; E05 grounding check validates no hallucinated statistics |
| 2026-04-14 | Phase 3 complete — extraction prompt, LLM client, extraction service, 37 tests (26 unit + 11 integration), all passing; `PropertyFeatures` schema hardened with `Literal` enum types; bug caught and fixed by tests |
| 2026-04-14 | Phase 2 complete — LightGBM model trained, serialized, evaluated; `training_stats.json` saved; all leakage checks passed |
| 2026-04-14 | Phase 3 started — `app/` structure, `PropertyFeatures` schema, prediction service, LLM provider decision (ADR-007) |
| 2026-04-14 | Phase 0 documentation foundation completed — all planning docs, instruction files, and skill files created |
| 2026-04-14 | Project initialized — workspace structure established |

---

*Keep this file current. If it is out of date, it is useless.*
