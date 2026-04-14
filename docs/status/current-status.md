# Current Project Status

> **Update this file whenever you start or complete a phase, make a major decision, or hit a blocker.**  
> **This is the first file a returning engineer (including future-you) should read.**

---

## Current Phase

**Phase 4 — Prediction Interpretation (Stage 3 LLM Explanation)**  
Status: **Not Started**

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

---

## What Is Not Started

- [ ] Stage 3 LLM explanation prompt (`prompts/explanation_v1.md`)
- [ ] Explanation service (`app/services/explanation.py`)
- [ ] API routes (`app/routes/`) — wiring extraction + prediction + explanation into endpoints
- [ ] Docker setup (`Dockerfile`, `docker-compose.yml`)
- [ ] UI (Phase 6)

---

## Active Blockers

| ID | Blocker | Impact | Resolution Path |
|----|---------|--------|----------------|
| — | None | — | — |

---

## Next Actions (in order)

1. **Review Phase 4 document** — `docs/phases/phase-04-prediction-interpretation.md`
2. **Create `prompts/explanation_v1.md`** — Stage 3 LLM explanation prompt (grounded with `training_stats.json`)
3. **Create `app/services/explanation.py`** — Stage 3 service
4. **Wire API routes** — `/predict` (full pipeline), `/extract` (Stage 1 only)
5. **Write tests for explanation service**
6. **Docker setup** — `Dockerfile`, `docker-compose.yml`

---

## Decisions Pending

| ID | Decision | Required By | Status |
|----|----------|------------|--------|
| D-01 | Log-transform `SalePrice` or not | Phase 2 (training) | ✅ **Resolved** — `np.log1p()` before training; `np.expm1()` on predictions |
| D-02 | Final feature shortlist (10–20 features) | Phase 2 (schema) | ✅ **Resolved** — 12 features: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`, `TotalBsmtSF`, `GarageCars`, `FullBath`, `YearRemodAdd`, `Fireplaces`, `LotArea`, `MasVnrArea`, `Exterior1st` |
| D-03 | Required vs. optional feature classification | Phase 3 (schema lock) | ✅ **Resolved** — Required: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`. Optional: remaining 8. |
| D-04 | Which LLM provider and model to use | Phase 3 | ✅ **Resolved** — Ollama `phi4-mini` (dev) + Groq `llama-3.3-70b-versatile` (prod). See ADR-007. |
| D-05 | Baseline model MAE target | Phase 2 evaluation | ✅ **Resolved** — Baseline MAE = $59,568 (`DummyRegressor` median). Final model target: MAE < $30,000. |
| D-06 | Final endpoint structure: one combined `/predict` or separate stage endpoints | Phase 5 | Open — leaning toward one combined endpoint |

---

## Recent Activity

| Date | Activity |
|------|----------|
| 2026-04-14 | Phase 3 complete — extraction prompt, LLM client, extraction service, 37 tests (26 unit + 11 integration), all passing; `PropertyFeatures` schema hardened with `Literal` enum types; bug caught and fixed by tests |
| 2026-04-14 | Phase 2 complete — LightGBM model trained, serialized, evaluated; `training_stats.json` saved; all leakage checks passed |
| 2026-04-14 | Phase 3 started — `app/` structure, `PropertyFeatures` schema, prediction service, LLM provider decision (ADR-007) |
| 2026-04-14 | Phase 0 documentation foundation completed — all planning docs, instruction files, and skill files created |
| 2026-04-14 | Project initialized — workspace structure established |

---

*Keep this file current. If it is out of date, it is useless.*
