# Progress Log

> **Format:** Most recent entry first.  
> **When to add an entry:** At the end of any work session, at the completion of a phase, or when a significant decision is made.  
> **Rule:** Each entry is immutable. Do not edit past entries.

---

## Log Entry Format

```
---
### [DATE] — [BRIEF TITLE]

**Phase:** Phase X — Name  
**Duration:** ~X hours  
**Status change:** [previous status] → [new status]

**What was done:**
- Bullet list of concrete outputs

**Decisions made:**
- Any decision with its rationale

**Discoveries / surprises:**
- Anything unexpected found

**Next session should start with:**
- The first concrete action for the next work session

**Blockers:**
- Any active blockers (or "None")
---
```

---

### 2026-04-14 — Phase 0 Documentation Foundation Complete

**Phase:** Phase 0 — Planning and Documentation  
**Duration:** ~1 session  
**Status change:** Project initialized → Phase 0 complete

**What was done:**
- Created `README.md` with full project overview, scope, architecture, and definition of done
- Created `docs/context/project-brief.md` — full engineering description of the two-stage LLM + ML pipeline
- Created `docs/context/requirements.md` — complete requirements across 8 categories (functional, non-functional, validation, UI, ML, prompt-chain, deployment, error-handling)
- Created `docs/context/assumptions-and-open-questions.md` — 21 registered assumptions, 10 open unknowns, 16 required questions before coding
- Created `docs/context/future-considerations.md` — 9 post-MVP features clearly separated with signals for when to add them
- Created all 7 phase documents in `docs/phases/` — each with objectives, checklists, exit criteria, and mistakes to avoid
- Created `docs/decisions/architecture-decision-records.md` — ADR-001 through ADR-005
- Created `docs/checklists/mvp-master-checklist.md` — full end-to-end verifiable checklist
- Created `docs/status/current-status.md` — active blockers and next actions
- Created `docs/roadmap.md` — phased execution roadmap table
- Created 5 `.github/instructions/` files for Copilot code generation guidance
- Created 5 `.copilot/skills/` files for persistent project context and guardrails

**Decisions made:**
- ADR-001: Documentation-first planning before any implementation
- ADR-002: Synchronous request handling for MVP
- ADR-003: Auth and background jobs excluded from MVP
- ADR-004: Form-based UI preferred over chat-first UI for MVP
- ADR-005: Ames Housing dataset chosen as training data

**Discoveries / surprises:**
- The two-stage LLM chain has a critical "Stage 1.5" (missing field collection) that is not an LLM call — it is a validation-driven UI interaction. This distinction matters for the API design.
- The Ames dataset's use of "NA" as a meaningful category (not a data error) is a significant imputation challenge. Must be addressed explicitly in Phase 1.
- Several Ames features that are highly predictive (e.g., `OverallQual`) are assessor-assigned ratings that users cannot naturally describe. These need careful required/optional classification.

**Next session should start with:**
1. Download the Ames Housing dataset and read the data dictionary
2. Open `docs/phases/phase-01-discovery-and-eda.md` and begin working through the checklist
3. Create `ml/eda.ipynb` — start with dataset loading, shape inspection, and column types

**Blockers:**
- Ames Housing dataset not yet downloaded (B-01)
- LLM API key not yet configured (B-02) — not needed until Phase 3

---

### [TEMPLATE FOR FUTURE ENTRIES]

---
### [DATE] — [BRIEF TITLE]

**Phase:** Phase X — Name  
**Duration:** ~X hours  
**Status change:** [previous status] → [new status]

**What was done:**
- 

**Decisions made:**
- 

**Discoveries / surprises:**
- 

**Next session should start with:**
- 

**Blockers:**
- 
---

---

*The progress log is your engineering journal. Entries written the same day they happen are dramatically more useful than entries reconstructed from memory a week later.*

---

### 2026-04-14 — Phase 2 Complete + App Structure Started

**Phase:** Phase 2 → Phase 3  
**Duration:** ~1 session  
**Status change:** Phase 2 In Progress → Phase 3 In Progress

**What was done:**
- Built `ml/model_training.ipynb` end-to-end (7 sections)
- Outlier removal: 2 rows from train only (`GrLivArea > 4000 AND SalePrice < $200k`)
- Preprocessing pipeline: `TargetEncoder` for Neighborhood, `OneHotEncoder` for Exterior1st (5 rare values → "Other"), `SimpleImputer(median)` for numeric
- DummyRegressor baseline: MAE = $59,568, RMSE = $88,667, R² = -0.025
- LightGBM (default params): Test MAE = $17,936 (69.9% improvement), RMSE = $29,238, R² = 0.8885
- All evaluation plots generated (predicted vs actual, residuals, feature importance)
- `ml/artifacts/model.joblib` serialized and round-trip verified (`Match: True`, 1438 KB)
- `ml/artifacts/training_stats.json` saved (training-set only stats)
- Leakage checklist fully cleared; all phase-02 exit criteria met
- App structure creation begun: `app/schemas/`, `app/services/`, `app/config.py`, `app/main.py`

**Decisions made:**
- LightGBM selected as final model (ADR-006 to be added)
- Train/test MAE gap (72%) noted but accepted — test metrics exceed both phase targets
- Feature-name warning from LightGBM/sklearn TargetEncoder interplay: cosmetic only, no action needed

**Discoveries / surprises:**
- `OverallQual` dominates feature importance by a wide margin (gain ~875 vs next best ~250) — consistent with EDA Pearson r = 0.79
- Exterior1st one-hot columns all near-zero importance — confirms it is a marginal feature
- Residuals show slight heteroscedasticity at high predicted prices (>$400K) — expected given sparse data at that range, no action needed for MVP

**Next session should start with:**
1. Add ADR-006 (LightGBM selection rationale)
2. Complete `app/schemas/property_features.py`
3. Complete `app/services/prediction.py`
4. Start Stage 1 extraction prompt (`prompts/stage1_extraction_v1.md`)

**Blockers:**
- B-02: LLM API key still needed for Phase 3 extraction/explanation stages
