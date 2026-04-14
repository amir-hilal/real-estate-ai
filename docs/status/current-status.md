# Current Project Status

> **Update this file whenever you start or complete a phase, make a major decision, or hit a blocker.**  
> **This is the first file a returning engineer (including future-you) should read.**

---

## Current Phase

**Phase 3 — LLM Extraction + App Structure**  
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
- [x] `docs/decisions/architecture-decision-records.md` — ADR-001 through ADR-005 recorded
- [x] `docs/checklists/mvp-master-checklist.md` — full end-to-end checklist created
- [x] `docs/roadmap.md` — phased execution roadmap table created
- [x] `.github/instructions/` — Copilot instruction files created for all categories
- [x] `.copilot/skills/` — project skill/context files created
- [x] **Phase 1 complete** — `ml/eda.ipynb` fully executed; all 10 unknowns (U-01–U-10) resolved; 12-feature schema finalized (4 required + 8 optional); all key decisions documented
- [x] **Phase 2 complete** — `ml/model_training.ipynb` fully executed; LightGBM trained (Test MAE $17,936, R² 0.8885); `ml/artifacts/model.joblib` and `ml/artifacts/training_stats.json` saved and verified

---

## What Is Not Started

- [ ] Stage 1 LLM extraction prompt (`prompts/extraction_v1.md`)
- [ ] Stage 3 LLM explanation prompt (`prompts/explanation_v1.md`)
- [ ] LLM client (`app/clients/llm.py`)
- [ ] Extraction service (`app/services/extraction.py`)
- [ ] Explanation service (`app/services/explanation.py`)
- [ ] API routes (`app/routes/`)
- [ ] Docker setup (`Dockerfile`, `docker-compose.yml`)
- [ ] UI (Phase 6)

---

## Active Blockers

| ID | Blocker | Impact | Resolution Path |
|----|---------|--------|----------------|
| B-02 | LLM API key not yet configured | Phase 3 cannot start | Obtain OpenAI or Anthropic API key; configure `.env` file |

---

## Next Actions (in order)

1. **Add ADR-006** — LightGBM model selection rationale
2. **Create `app/` structure** — `main.py`, `config.py`, `schemas/`, `services/`, `routes/`, `clients/`
3. **Create `app/schemas/property_features.py`** — Pydantic `PropertyFeatures` model (schema locked from Phase 2)
4. **Create `app/services/prediction.py`** — loads `model.joblib`, runs inference
5. **Create `prompts/extraction_v1.md`** — Stage 1 LLM extraction prompt
6. **Create `app/clients/llm.py`** — async OpenAI client wrapper
7. **Create `app/services/extraction.py`** — Stage 1 service
8. **Wire routes and main.py**

---

## Decisions Pending

| ID | Decision | Required By | Status |
|----|----------|------------|--------|
| D-01 | Log-transform `SalePrice` or not | Phase 2 (training) | ✅ **Resolved** — `np.log1p()` before training; `np.expm1()` on predictions |
| D-02 | Final feature shortlist (10–20 features) | Phase 2 (schema) | ✅ **Resolved** — 12 features: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`, `TotalBsmtSF`, `GarageCars`, `FullBath`, `YearRemodAdd`, `Fireplaces`, `LotArea`, `MasVnrArea`, `Exterior1st` |
| D-03 | Required vs. optional feature classification | Phase 3 (schema lock) | ✅ **Resolved** — Required: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`. Optional: remaining 8. |
| D-04 | Which LLM provider and model to use | Phase 3 | Open — defaulting to OpenAI GPT-4o; confirm availability |
| D-05 | Baseline model MAE target | Phase 2 evaluation | ✅ **Resolved** — Baseline MAE = $59,568 (`DummyRegressor` median). Final model target: MAE < $30,000. |
| D-06 | Final endpoint structure: one combined `/predict` or separate stage endpoints | Phase 5 | Open — leaning toward one combined endpoint |

---

## Recent Activity

| Date | Activity |
|------|----------|
| 2026-04-14 | Phase 2 complete — LightGBM model trained, serialized, evaluated; `training_stats.json` saved; all leakage checks passed |
| 2026-04-14 | Phase 3 started — `app/` structure, `PropertyFeatures` schema, and prediction service under construction |
| 2026-04-14 | Phase 0 documentation foundation completed — all planning docs, instruction files, and skill files created |
| 2026-04-14 | Project initialized — workspace structure established |

---

*Keep this file current. If it is out of date, it is useless.*
