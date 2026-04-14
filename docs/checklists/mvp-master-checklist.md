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

- [ ] Ames Housing dataset downloaded and stored locally (not fetched from live URL at runtime)
- [ ] Ames data dictionary read and understood (not skimmed)
- [ ] EDA notebook (`ml/eda.ipynb`) runs end-to-end without errors
- [ ] Dataset shape confirmed: ~1,460 training rows, ~79 features
- [ ] Missing value analysis complete: every high-missing column has a documented decision
- [ ] `SalePrice` histogram plotted; skewness computed
- [ ] Log-transform decision made and documented: *(answer: ________)*
- [ ] Outlier scatter plot (`GrLivArea` vs `SalePrice`) reviewed; outlier removal decision documented
- [ ] Top 20 features by Pearson correlation with `SalePrice` identified
- [ ] Quick baseline feature importance (RandomForest or LightGBM) computed
- [ ] Final feature shortlist (10–20 features) documented
- [ ] Required vs. optional feature classification documented for each schema candidate
- [ ] All unknowns U-01 through U-10 in assumptions doc are resolved
- [ ] EDA summary section written at top of notebook
- [ ] Phase 1 exit criteria all checked in `docs/phases/phase-01-discovery-and-eda.md`

---

## Phase 2 — ML Foundation

- [ ] Train/test split performed on raw data before any preprocessing
- [ ] Imputation strategy documented per feature (from EDA findings)
- [ ] Encoding strategy documented per categorical feature
- [ ] Scikit-learn preprocessing pipeline constructed
- [ ] `DummyRegressor` baseline trained and evaluated; baseline MAE documented: *(MAE: ________)*
- [ ] At least two model candidates trained and compared
- [ ] Final model selected; selection rationale in ADR
- [ ] Leakage-prevention checklist in `docs/phases/phase-02-ml-foundation.md` fully checked
- [ ] Test-set metrics documented: MAE: ________, RMSE: ________, R²: ________
- [ ] Predicted vs. actual scatter plot reviewed
- [ ] Feature importances computed and plotted
- [ ] Model pipeline serialized to `ml/artifacts/model.pkl`
- [ ] Serialized model loads successfully in a fresh Python process
- [ ] Training statistics computed from training data only
- [ ] Training statistics file saved to `ml/artifacts/training_stats.json`
- [ ] Training notebook (`ml/model_training.ipynb`) runs end-to-end without errors
- [ ] Phase 2 exit criteria all checked in `docs/phases/phase-02-ml-foundation.md`

---

## Phase 3 — LLM Extraction Design (Stage 1)

- [ ] `PropertyFeatures` Pydantic model created with all schema fields, types, and constraints
- [ ] Tier 1 (required) vs Tier 2/3 (optional) fields finalized and documented in schema
- [ ] Stage 1 extraction prompt written and stored in `prompts/stage1_extraction_v1.md`
- [ ] Prompt includes: role, task, schema/format instructions, anti-hallucination instruction, examples
- [ ] All 10 test queries from `docs/phases/phase-03-llm-extraction-design.md` run and results documented
- [ ] T01 (full description) extracts ≥8 Tier 1 fields correctly
- [ ] T07 (no basement) returns `bsmt_qual: null` without error
- [ ] T10 (non-property input) returns a valid structured error/empty response
- [ ] JSON → Pydantic → required field check validation chain implemented and tested
- [ ] All failure modes documented in Phase 3 doc have implemented handling paths
- [ ] Prompt version 1 committed to version control
- [ ] Phase 3 exit criteria all checked in `docs/phases/phase-03-llm-extraction-design.md`

---

## Phase 4 — Prediction Interpretation (Stage 2)

- [ ] Stage 2 explanation prompt written and stored in `prompts/stage2_explanation_v1.md`
- [ ] Prompt includes: grounding instruction, statistics injection block, feature injection block, format instruction
- [ ] All 5 evaluation scenarios from `docs/phases/phase-04-prediction-interpretation.md` run and documented
- [ ] At least 4 of 5 scenarios produce explanations that pass the evaluation checklist
- [ ] No scenario produces a hallucinated statistic (manually verified)
- [ ] Explanation always mentions the predicted price explicitly
- [ ] Explanation always includes ≥2 numeric comparisons from injected statistics
- [ ] Fallback behavior for Stage 2 failure tested (prediction returned with fallback message)
- [ ] Prompt version 1 committed to version control
- [ ] Phase 4 exit criteria all checked in `docs/phases/phase-04-prediction-interpretation.md`

---

## Phase 5 — API and Containerization

- [ ] FastAPI application created with `GET /health`, `POST /extract`, `POST /predict` endpoints
- [ ] Model artifact loaded at startup via `lifespan` context
- [ ] Training statistics loaded at startup and held in memory
- [ ] All API error responses are structured JSON with `status`, `error_code`, `message`
- [ ] `GET /health` returns 200 with `model_loaded: true` when model is loaded
- [ ] `POST /extract` returns partial extraction correctly (status: "partial" with missing_fields)
- [ ] `POST /predict` runs full pipeline successfully on a complete description
- [ ] `POST /predict` returns "incomplete" status with missing fields on partial description
- [ ] `POST /predict` handles invalid/empty input without crashing (returns structured error)
- [ ] All 6 integration tests from Phase 5 doc pass
- [ ] All secrets passed via environment variables only (no hardcoded keys)
- [ ] Structured logging implemented for requests and LLM calls
- [ ] `Dockerfile` created and image builds successfully
- [ ] `docker-compose.yml` created; `docker-compose up` starts the application
- [ ] `.env.example` created with all required variable names
- [ ] Phase 5 exit criteria all checked in `docs/phases/phase-05-api-and-containerization.md`

---

## Phase 6 — UI Flow

- [ ] Input form renders in browser with text area and submit button
- [ ] Missing fields form renders correctly for at least one real missing-field scenario
- [ ] Prediction and explanation display correctly after full pipeline
- [ ] Extracted features panel is displayed (even if collapsed by default)
- [ ] All error states from Phase 6 doc are tested and render correctly
- [ ] "Estimate Another Property" reset button works
- [ ] UI runs inside Docker container and is accessible from the browser
- [ ] Full end-to-end flow tested from browser: describe → (fill gaps) → see prediction + explanation
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
