# Current Project Status

> **Update this file whenever you start or complete a phase, make a major decision, or hit a blocker.**  
> **This is the first file a returning engineer (including future-you) should read.**

---

## Current Phase

**Phase 0 — Planning and Documentation**  
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

---

## What Is Not Started

- [ ] Phase 1: EDA notebook (`ml/eda.ipynb`) — first hands-on phase
- [ ] Ames Housing dataset download
- [ ] `PropertyFeatures` Pydantic schema
- [ ] All ML training code
- [ ] All prompt files
- [ ] All API code
- [ ] Docker setup
- [ ] UI

---

## Active Blockers

| ID | Blocker | Impact | Resolution Path |
|----|---------|--------|----------------|
| B-01 | Ames Housing dataset not yet downloaded | Phase 1 cannot start | Download from Kaggle or use `openml` Python package |
| B-02 | LLM API key not yet configured | Phase 3 cannot start | Obtain OpenAI or Anthropic API key; configure `.env` file |

---

## Next Actions (in order)

1. **Download the Ames Housing dataset** — Kaggle: [House Prices - Advanced Regression Techniques](https://www.kaggle.com/c/house-prices-advanced-regression-techniques/data) or via `openml.datasets.get_dataset(42165)`
2. **Save dataset to `ml/data/`** (directory to be created when implementation begins)
3. **Read the Ames data dictionary** — critical before any EDA code is written
4. **Open `docs/phases/phase-01-discovery-and-eda.md`** — work through its checklist methodically
5. **Create `ml/eda.ipynb`** notebook

---

## Decisions Pending

| ID | Decision | Required By | Status |
|----|----------|------------|--------|
| D-01 | Log-transform `SalePrice` or not | Phase 2 (training) | Open — awaiting EDA histogram |
| D-02 | Final feature shortlist (10–20 features) | Phase 2 (schema) | Open — awaiting EDA importances |
| D-03 | Required vs. optional feature classification | Phase 3 (schema lock) | Open — awaiting D-02 |
| D-04 | Which LLM provider and model to use | Phase 3 | Open — defaulting to OpenAI GPT-4o; confirm availability |
| D-05 | Baseline model MAE target | Phase 2 evaluation | Open — awaiting D-02 and baseline run |
| D-06 | Final endpoint structure: one combined `/predict` or separate stage endpoints | Phase 5 | Open — leaning toward one combined endpoint |

---

## Recent Activity

| Date | Activity |
|------|----------|
| 2026-04-14 | Phase 0 documentation foundation completed — all planning docs, instruction files, and skill files created |
| 2026-04-14 | Project initialized — workspace structure established |

---

*Keep this file current. If it is out of date, it is useless.*
