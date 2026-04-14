# Assumptions and Open Questions

> **Purpose:** Make every assumption explicit. An unstated assumption is a hidden risk.  
> **Status:** Active — update continuously throughout the project  
> **Rule:** If an assumption here turns out to be wrong, open a new ADR entry.

---

## 1. Current Assumptions

### About the Dataset

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-01 | ~~The Ames Housing dataset is available in full from a public source (Kaggle, OpenML, or equivalent)~~ **CONFIRMED** — Downloaded from OpenML ID 42165, saved locally at `ml/data/ames.csv`. No live URL dependency. | Verified 2026-04-14 | N/A |
| A-02 | ~~The target variable is `SalePrice` (continuous, USD)~~ **CONFIRMED** — `SalePrice` present, range $34,900–$755,000, median $163,000. | Verified 2026-04-14 | N/A |
| A-03 | ~~The dataset contains approximately 2,900 rows and 79+ features~~ **CORRECTED** — Actual shape is 1,460 rows × 81 columns (79 features + `Id` + `SalePrice`). The 2,900-row figure refers to the combined train+test split used in some Kaggle versions; we have the training portion only. | Verified 2026-04-14 | Feature plan unchanged — 1,460 rows is sufficient for the MVP model. |
| A-04 | There are meaningful categorical features (neighborhood, building class, etc.) that require encoding — not just numeric features | Dataset documentation | Encoding strategy must be revisited |
| A-05 | ~~Missing values exist in the dataset and are meaningful (e.g., "NA" for no garage, not a data error)~~ **CONFIRMED** — Two distinct groups identified: (1) ~19 columns where NA = feature doesn't exist on the property (PoolQC, Alley, FireplaceQu, Garage cols, Bsmt cols, etc.) — these are encoded as `"None"` or binary `Has___` columns, not imputed; (2) true data gaps (LotFrontage, GarageYrBlt, Electrical) — imputed with median/mode from training set only. | Verified 2026-04-14 | N/A |
| A-06 | There are no obvious target-leaking features in the raw dataset that cannot be identified through careful EDA | General knowledge | Could invalidate model metrics if leakage is later discovered |

---

### About the ML Model

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-07 | A gradient-boosted tree model (XGBoost or LightGBM) will outperform linear regression after proper featurization | Common result on Ames dataset in public benchmarks | Simpler model may suffice; over-engineering gradient boosting for marginal gain |
| A-08 | Feature engineering beyond clean encoding and imputation will not be required for an acceptable baseline | Ames is relatively well-behaved | May need to create interaction features or apply log transforms for acceptable performance |
| A-09 | `SalePrice` should be log-transformed to normalization the target distribution | Common in Ames benchmarks | Must be confirmed by EDA — if distribution is already well-behaved, log transform complicates interpretation |
| A-10 | scikit-learn Pipeline is sufficient for the preprocessing + model serialization combination | Standard ML practice | If model requires non-sklearn primitives, serialization approach must change |

---

### About the LLM

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-11 | GPT-4o (or an equivalent capable LLM with structured output support) is available and accessible via API key | OpenAI / Anthropic API access assumed | If only open-source models are available, JSON-mode reliability and instruction-following quality may drop significantly |
| A-12 | Structured JSON output mode (e.g., OpenAI response_format=json, function calling, or Pydantic AI) is reliable enough for Stage 1 extraction | Documented capability | May require retry logic or more rigid prompting if JSON errors occur |
| A-13 | Stage 1 LLM can reliably extract the 10–15 most important Ames features from a user's plain-English description | Based on LLM instruction-following capability | Some features may require more explicit prompting; test cases will validate this |
| A-14 | Stage 2 LLM will not hallucinate statistics if the prompt explicitly provides the correct values in context | Grounding via in-context data reduces hallucination | Must be validated in Phase 4; spot-checking explanations against actual stats is required |
| A-15 | Two separate LLM calls (extraction + explanation) will be more maintainable than a single combined prompt | Separation of concerns | If combined prompt is tested and reliably more accurate, consolidation can be considered post-MVP |

---

### About Architecture & Deployment

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-16 | Synchronous HTTP request handling is acceptable for MVP given expected latency of 3–8 seconds | MVP scope decision (ADR-002) | If users need faster responses, an async polling approach would be required |
| A-17 | FastAPI + Uvicorn is sufficient for serving this system in a single-process, single-container setup | Well-established | Multi-process or load balancing not needed at MVP |
| A-18 | Docker + docker-compose is sufficient for local deployment; no Kubernetes is required | MVP scope | Cloud deployment would require Helm or similar; not in scope |
| A-19 | The LLM API key will be available via environment variable; no secrets manager is needed | MVP simplicity | If security requirements change, AWS Secrets Manager or Vault would be needed |

---

### About the UI

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-20 | A simple browser-based form UI is sufficient for MVP demonstration | ADR-004 | If stakeholders require a polished UI, this requires significant additional scope |
| A-21 | Form-based missing-field collection is adequate — no conversational back-and-forth is needed | MVP scope | If user testing shows confusion, a multi-step wizard UI may be needed |

---

## 2. Unknowns to Resolve Through EDA

These are not assumptions — they are open questions that only the data can answer. They must be answered in Phase 1 before modeling begins.

| ID | Unknown | How to Resolve | Phase |
|----|---------|----------------|-------|
| U-01 | ~~Which features have the strongest correlation with `SalePrice`?~~ **RESOLVED** — Top features by Pearson \|r\| > 0.5 (training set): `OverallQual`, `GrLivArea`, `GarageCars`, `GarageArea`, `TotalBsmtSF`, `1stFlrSF`, `FullBath`, `TotRmsAbvGrd`, `YearBuilt`. Also notable at \|r\| > 0.4: `GarageYrBlt`, `MasVnrArea`, `Fireplaces`. Confirmed by LightGBM: `OverallQual`, `GrLivArea`, `GarageCars`, `TotalBsmtSF`, `YearBuilt`, `FullBath` appear in both. | Phase 1 ✅ |
| U-02 | ~~How severe is the missing-value problem? Which columns have >20% missing?~~ **RESOLVED** — 5 columns exceed 20% missing: `PoolQC` (~99%), `MiscFeature` (~96%), `Alley` (~93%), `Fence` (~80%), `FireplaceQu` (~47%). All are Group A (NA = no feature) — none are dropped. | Phase 1 ✅ |
| U-03 | ~~Is `SalePrice` normally distributed or does it need a log transform?~~ **RESOLVED** — Raw skewness = 1.74 (strong right skew); log1p skewness = 0.12 (near-normal). Q-Q plot confirms the upper tail deviates significantly from the reference line in raw form; log1p corrects it. Decision: apply `np.log1p()` before training, `np.expm1()` to convert predictions back to USD. | Phase 1 ✅ |
| U-04 | ~~Which categorical features have high cardinality (>10 unique values)?~~ **RESOLVED** — 3 features exceed 10 unique values: `Neighborhood` (25), `Exterior1st` (~15), `Exterior2nd` (~15). Decision: keep `Neighborhood` (target encoding), keep `Exterior1st` (one-hot after binning rares <10 rows to `"Other"`), **drop `Exterior2nd`** (85% overlap with `Exterior1st` — no independent information). | Phase 1 ✅ |
| U-05 | ~~Are there outlier properties in the dataset that should be excluded from training?~~ **RESOLVED** — 2 rows identified: `GrLivArea > 4,000 sq ft AND SalePrice < $200k`. Both have `SaleCondition = "Partial"` — partial-interest transfers, not market sales. Decision: **remove from training set only** (drop before fitting any pipeline). No other erroneous values found in key numeric columns. | Phase 1 ✅ |
| U-06 | Which 10–15 features will the LLM schema focus on? | Determined after U-01 and U-02 are resolved | Phase 1 → Phase 3 |
| U-07 | ~~What Ames-specific missing value codes mean semantically (e.g., NA = no garage)?~~ **RESOLVED** — NA in quality/condition/type columns means the feature is absent from the property, not a data recording error. These values carry predictive signal and must be preserved as a distinct `"None"` category or binary `Has___` column. See `ml/eda.ipynb` Section 4 decision table. | Phase 1 ✅ |
| U-08 | ~~Does neighborhood have a strong price effect? Is it a required feature in the schema?~~ **RESOLVED** — Yes, very strong. Box plot shows ~$350k spread between cheapest and most expensive neighborhoods (median range ~$75k–$320k). `Neighborhood` is a **required** schema field. Encoding: target encoding fit on training set only inside `sklearn.Pipeline`. | Phase 1 ✅ |
| U-09 | ~~Are there features that are near-duplicates (e.g., TotalBsmtSF vs BsmtFinSF1 + BsmtFinSF2)?~~ **RESOLVED** — Three redundant groups identified: (1) `GarageArea` vs `GarageCars` → keep `GarageCars`; (2) `GrLivArea` vs `1stFlrSF` vs `TotRmsAbvGrd` → keep `GrLivArea`; (3) `TotalBsmtSF` vs `BsmtFinSF1`/`BsmtUnfSF` → keep `TotalBsmtSF`. See `ml/eda.ipynb` Section 6 decision table. | Phase 1 ✅ |
| U-10 | ~~What should the imputation strategy be for each category of missing values?~~ **RESOLVED** — Group A (NA = no feature): encode as `"None"` or binary `Has___` — no imputation. Group B (true gaps): `LotFrontage` → median by Neighborhood; `GarageYrBlt` → fill with `YearBuilt`; `Electrical` (1 row) → mode. All statistics computed on training set only inside a `sklearn.Pipeline`. | Phase 1 ✅ |

---

## 3. Risks and Dependencies

### Technical Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-01 | LLM JSON extraction is unreliable for complex schemas | Medium | High | Simplify schema to 10–15 fields; test with 10+ real property descriptions before finalizing |
| R-02 | Data leakage is introduced silently during preprocessing | Medium | High | Enforce the leakage-prevention checklist before any evaluation metrics are reported |
| R-03 | Model performs poorly due to insufficient feature engineering | Medium | Medium | Start with a documented baseline; iterate on features only if the baseline is substantially below target |
| R-04 | Stage 2 LLM generates confident but incorrect statistics | Medium | High | Always inject real statistics from training data into the prompt; never let LLM generate numbers |
| R-05 | LLM API cost becomes significant during development | Low | Low | Use GPT-3.5 or local models during iteration; switch to GPT-4o only for final testing |
| R-06 | Pydantic schema becomes out of sync with actual ML model features | Medium | High | Schema and model feature list are co-maintained; any change to one requires updating the other |

### External Dependencies

| Dependency | Required By | Risk | Fallback |
|------------|------------|------|---------|
| OpenAI / Anthropic API access | Phase 3, Phase 4 | API key invalid or quota exceeded | Use Ollama (local models) with a JSON-schema prompt |
| Ames Housing dataset availability | Phase 1 | Dataset pulled from Kaggle/OpenML | Mirror locally; do not depend on live URL |
| scikit-learn, XGBoost, Pydantic | Phase 2, 3 | Version incompatibilities via pip | Pin all versions in requirements.txt from the start |

---

## 4. Questions That Must Be Answered Before Coding

> These are the gates. No implementation begins until these are answered.

### Before Phase 2 (ML Foundation)

- [ ] **Q1:** Which features will be included in the schema? (Requires EDA — Phase 1 must complete first)
- [ ] **Q2:** What is the baseline MAE on Ames using only the top 10 features? (Establishes the target model must beat)
- [ ] **Q3:** How will we handle categorical features with rare values that may not appear in production input?
- [x] **Q4:** Will `SalePrice` be log-transformed? **Yes** — `np.log1p()` before training; `np.expm1()` on predictions. Raw skewness = 1.74, log1p skewness = 0.12. Confirmed via histogram and Q-Q plot in `ml/eda.ipynb` Section 5.
- [x] **Q5:** What imputation strategy will be used for numeric vs. categorical missing values? **ANSWERED** — Group A (NA = no feature): encode as `"None"` / binary. Group B: numeric → median (train only); categorical → mode (train only). All inside `sklearn.Pipeline`.

### Before Phase 3 (LLM Extraction Design)

- [ ] **Q6:** What is the final set of features in the `PropertyFeatures` schema? (Locked after Phase 2)
- [ ] **Q7:** Which features are "required" (prediction cannot proceed without them) vs "optional"?
- [ ] **Q8:** What is the exact JSON structure the Stage 1 prompt must return?
- [ ] **Q9:** How do we handle a property description that contains no extractable structured data?
- [ ] **Q10:** Which LLM provider and model will be used? Is structured output mode available?

### Before Phase 4 (Prediction Interpretation)

- [ ] **Q11:** What statistics from the training data are most useful for grounding the explanation?
- [ ] **Q12:** What is the format and location of the persisted training statistics file?
- [ ] **Q13:** How should the explanation handle predictions that are at the extremes (very low or very high)?

### Before Phase 5 (API & Containerization)

- [ ] **Q14:** Will there be one combined endpoint (`POST /predict`) or separate stage endpoints?
- [ ] **Q15:** What is the final directory structure for the application code?
- [ ] **Q16:** How will the model artifact and prompts be loaded into the Docker container?

---

## 5. How to Use This Document

1. When an assumption turns out to be wrong, strike it through and add a note referencing the ADR or decision that superseded it.
2. When an unknown is resolved via EDA, move it to its phase document with the answer recorded.
3. When a question is answered, check it off and document the answer inline.
4. This document is never "done" — it evolves throughout all phases.

---

*This document is a first-class engineering artifact. Vague comfort with assumptions is how projects fail.*
