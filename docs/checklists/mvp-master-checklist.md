# MVP Master Checklist

> **Purpose:** A single, verifiable end-to-end checklist for the entire MVP.  
> **Rule:** Every item must be independently verifiable — not "seems done" but "is demonstrably done."  
> **Format:** Check off items as they are completed. Never remove an unchecked item; add a note if blocked.

---

## Phase 0 — Planning and Documentation

- [x] `README.md` created with overview, scope, and definition of done
- [x] `docs/context/project-brief.md` written and reviewed
- [x] `docs/context/requirements.md` written with all requirement categories
- [x] `docs/context/assumptions-and-open-questions.md` written with full assumption registry
- [x] `docs/context/future-considerations.md` written — post-MVP items clearly separated
- [x] `docs/phases/phase-01-discovery-and-eda.md` written with checklist and exit criteria
- [x] `docs/phases/phase-02-ml-foundation.md` written with leakage checklist
- [x] `docs/phases/phase-03-llm-extraction-design.md` written with test query plan
- [x] `docs/phases/phase-04-prediction-interpretation.md` written with evaluation checklist
- [x] `docs/phases/phase-05-api-and-containerization.md` written with endpoint definitions
- [x] `docs/phases/phase-06-ui-flow.md` written with UI states documented
- [x] `docs/phases/phase-07-testing-demo-and-delivery.md` written with review questions
- [x] `docs/decisions/architecture-decision-records.md` written with ADR-001 through ADR-005
- [x] `docs/checklists/mvp-master-checklist.md` created (this file)
- [x] `docs/status/current-status.md` created
- [x] `docs/status/progress-log.md` created
- [x] `docs/roadmap.md` created
- [x] `.github/instructions/` files created
- [x] `.copilot/skills/` files created

---

## Phase 1 — Discovery and EDA

- [x] Ames Housing dataset downloaded and stored locally (not fetched from live URL at runtime)
- [x] Ames data dictionary read and understood (not skimmed)
- [x] EDA notebook (`ml/eda.ipynb`) runs end-to-end without errors
- [x] Dataset shape confirmed: ~1,460 training rows, ~79 features — actual: 1,460 × 81 (79 features + Id + SalePrice)
- [x] Missing value analysis complete: every high-missing column has a documented decision
- [x] `SalePrice` histogram plotted; skewness computed
- [x] Log-transform decision made and documented: *(answer: `np.log1p()` applied — raw skewness 1.74 → 0.12 after transform; `np.expm1()` used at inference)*
- [x] Outlier scatter plot (`GrLivArea` vs `SalePrice`) reviewed; outlier removal decision documented — 2 partial-interest sales removed from training set
- [x] Top 20 features by Pearson correlation with `SalePrice` identified
- [x] Quick baseline feature importance (RandomForest or LightGBM) computed
- [x] Final feature shortlist (10–20 features) documented — 12 features selected
- [x] Required vs. optional feature classification documented for each schema candidate
- [x] All unknowns U-01 through U-10 in assumptions doc are resolved
- [x] EDA summary section written at top of notebook
- [x] Phase 1 exit criteria all checked in `docs/phases/phase-01-discovery-and-eda.md`

---

## Phase 2 — ML Foundation

- [x] Train/test split performed on raw data before any preprocessing
- [x] Imputation strategy documented per feature (from EDA findings)
- [x] Encoding strategy documented per categorical feature
- [x] Scikit-learn preprocessing pipeline constructed
- [x] `DummyRegressor` baseline trained and evaluated; baseline MAE documented: *(MAE: $59,568)*
- [x] At least two model candidates trained and compared
- [x] Final model selected; selection rationale in ADR — LightGBM, ADR-006
- [x] Leakage-prevention checklist in `docs/phases/phase-02-ml-foundation.md` fully checked
- [x] Test-set metrics documented: MAE: $17,936, RMSE: $29,238, R²: 0.8885
- [x] Predicted vs. actual scatter plot reviewed
- [x] Feature importances computed and plotted
- [x] Model pipeline serialized to `ml/artifacts/model.joblib`
- [x] Serialized model loads successfully in a fresh Python process
- [x] Training statistics computed from training data only
- [x] Training statistics file saved to `ml/artifacts/training_stats.json`
- [x] Training notebook (`ml/model_training.ipynb`) runs end-to-end without errors
- [x] Phase 2 exit criteria all checked in `docs/phases/phase-02-ml-foundation.md`

---

## Phase 3 — LLM Extraction Design (Stage 1)

- [x] `PropertyFeatures` Pydantic model created with all schema fields, types, and constraints
- [x] Tier 1 (required) vs Tier 2/3 (optional) fields finalized and documented in schema
- [x] Stage 1 extraction prompt written and stored in `prompts/extraction_v1.md`
- [x] Prompt includes: role, task, schema/format instructions, anti-hallucination instruction, examples
- [x] All 10 test queries from `docs/phases/phase-03-llm-extraction-design.md` run and results documented
- [x] T01 (full description) extracts ≥8 Tier 1 fields correctly — 11/12 fields extracted
- [x] T07 (no basement) returns `TotalBsmtSF: null` without error — schema uses `TotalBsmtSF`, not `bsmt_qual`
- [x] T10 (non-property input) returns a valid structured error/empty response
- [x] JSON → Pydantic → required field check validation chain implemented and tested
- [x] All failure modes documented in Phase 3 doc have implemented handling paths
- [x] Prompt version 1 committed to version control
- [x] Phase 3 exit criteria all checked in `docs/phases/phase-03-llm-extraction-design.md`

---

## Phase 4 — Prediction Interpretation (Stage 2)

- [x] Stage 2 explanation prompt written and stored in `prompts/explanation_v1.md`
- [x] Prompt includes: grounding instruction, statistics injection block, feature injection block, format instruction
- [x] All 5 evaluation scenarios from `docs/phases/phase-04-prediction-interpretation.md` run and documented
- [x] At least 4 of 5 scenarios produce explanations that pass the evaluation checklist — all 5 pass
- [x] No scenario produces a hallucinated statistic (manually verified) — E05 grounding test asserts all dollar amounts within ±$1,000 of injected context
- [x] Explanation always mentions the predicted price explicitly
- [x] Explanation always includes ≥2 numeric comparisons from injected statistics
- [x] Fallback behavior for Stage 2 failure tested (prediction returned with fallback message)
- [x] Prompt version 1 committed to version control
- [x] Phase 4 exit criteria all checked in `docs/phases/phase-04-prediction-interpretation.md`

---

## Phase 5 — API and Containerization

- [x] FastAPI application created with `GET /health`, `POST /extract`, `POST /predict` endpoints
- [x] Model artifact loaded at startup via `lifespan` context
- [x] Training statistics loaded at startup and held in memory
- [x] All API error responses are structured JSON with `status`, `error_code`, `message`
- [x] `GET /health` returns 200 with `model_loaded: true` when model is loaded
- [x] `POST /extract` returns partial extraction correctly (status: "partial" with missing_fields)
- [x] `POST /predict` runs full pipeline successfully on a complete description
- [x] `POST /predict` returns "incomplete" status with missing fields on partial description
- [x] `POST /predict` handles invalid/empty input without crashing (returns structured error)
- [x] All 6 integration tests from Phase 5 doc pass
- [x] All secrets passed via environment variables only (no hardcoded keys)
- [x] Structured logging implemented for requests and LLM calls
- [x] `Dockerfile` created and image builds successfully — multi-stage build, 2s rebuild with layer cache
- [x] `docker-compose.yml` created; `docker-compose up` starts the application — verified with curl
- [x] `.env.example` created with all required variable names
- [x] Phase 6 — UI checklist items reflect Phase 6 in progress (see Phase 6 section)
- [x] Phase 5 exit criteria all checked in `docs/phases/phase-05-api-and-containerization.md`

---

## Phase 6 — UI Flow

- [x] `POST /chat` SSE endpoint created and returns events (reply, prediction, token, done, error) — verified with curl
- [x] Chat orchestration service (`app/services/chat.py`) handles intent routing, feature merging, prediction, and streamed explanation
- [x] Chat prompt (`prompts/chat_v1.md`) covers intent classification + feature extraction with anti-hallucination rules
- [x] Backend SSE streaming verified: each explanation token arrives as a separate `event: token` line — confirmed with curl
- [ ] CORS middleware added to FastAPI backend for cross-origin frontend requests
- [ ] Standalone React app (Vite + React 18 + TypeScript + plain CSS) created and running
- [ ] Greeting input ("Hello") receives a conversational reply, not an error — verified in React app
- [ ] Vague property description triggers follow-up question for missing required fields — verified in React app
- [ ] Conversation accumulates features across turns until all required fields are known — verified in React app
- [ ] Prediction card renders inline in the chat thread when all required fields are present — verified in React app
- [ ] Explanation streams token-by-token into the chat bubble (not popping in all at once) — verified in React app
- [ ] Error bubbles appear in the thread for LLM failure and model-not-ready scenarios — verified in React app
- [ ] Full end-to-end flow works from browser: greeting → property → missing fields → prediction + streamed explanation
- [ ] `/predict` endpoint still passes all existing tests (no regression)
- [ ] Phase 6 exit criteria all checked in `docs/phases/phase-06-ui-flow.md`

---

## Phase 7 — Testing, Demo, and Delivery

- [ ] All 3 demo inputs (happy path, partial, invalid) tested and produce correct outcomes
- [ ] All artifacts from the artifact table in Phase 7 doc are present and verified
- [ ] All review questions in Phase 7 doc can be answered from memory
- [ ] `docker-compose up` starts the full system cleanly on a clean pull
- [ ] `docs/status/current-status.md` updated to reflect completion
- [ ] `docs/status/progress-log.md` has a final entry
- [ ] Master checklist (this file) is 100% checked ✅

---

## Definition of Done: Complete Checklist

The project is done when:
1. Every item above is checked
2. The full pipeline runs end-to-end via Docker in a live demo
3. You can explain every decision, from EDA to deployment, from memory

---

*A checklist item that cannot be verified is not a checklist item — it is a wish.*
