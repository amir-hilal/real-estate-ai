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
| A-04 | ~~There are meaningful categorical features (neighborhood, building class, etc.) that require encoding — not just numeric features~~ **CONFIRMED** — `Neighborhood` (25 values) → target encoding fit on training set only; `Exterior1st` (~15 values) → one-hot after binning rare values (<10 rows) to `"Other"`; `Exterior2nd` → dropped (85% overlap with `Exterior1st`). All encoders fit inside `sklearn.Pipeline` on training data only. | Verified 2026-04-14 | N/A |
| A-05 | ~~Missing values exist in the dataset and are meaningful (e.g., "NA" for no garage, not a data error)~~ **CONFIRMED** — Two distinct groups identified: (1) ~19 columns where NA = feature doesn't exist on the property (PoolQC, Alley, FireplaceQu, Garage cols, Bsmt cols, etc.) — these are encoded as `"None"` or binary `Has___` columns, not imputed; (2) true data gaps (LotFrontage, GarageYrBlt, Electrical) — imputed with median/mode from training set only. | Verified 2026-04-14 | N/A |
| A-06 | ~~There are no obvious target-leaking features in the raw dataset that cannot be identified through careful EDA~~ **CONFIRMED** — EDA identified and removed the only problematic rows (2 partial-interest sales with anomalous price-to-size ratios). All preprocessing statistics are computed on training data only inside `sklearn.Pipeline`. Phase 2 leakage checklist passed. | Verified 2026-04-14 | N/A |

---

### About the ML Model

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-07 | ~~A gradient-boosted tree model (XGBoost or LightGBM) will outperform linear regression after proper featurization~~ **CONFIRMED** — LightGBM achieved test MAE = $17,936 (69.9% improvement over $59,568 baseline), test R² = 0.8885. Both targets exceeded. | Verified 2026-04-14 | N/A |
| A-08 | ~~Feature engineering beyond clean encoding and imputation will not be required for an acceptable baseline~~ **CONFIRMED** — Model met phase targets (MAE < $30,000, R² > 0.85) using only median imputation, target encoding for `Neighborhood`, one-hot encoding for `Exterior1st`, and log-transform on target. No interaction features needed. | Verified 2026-04-14 | N/A |
| A-09 | ~~`SalePrice` should be log-transformed to normalize the target distribution~~ **CONFIRMED** — Raw skewness = 1.74; log1p skewness = 0.12. Q-Q plot confirms log1p correction. `np.log1p()` applied before training; `np.expm1()` applied at inference. | Verified 2026-04-14 | N/A |
| A-10 | ~~scikit-learn Pipeline is sufficient for the preprocessing + model serialization combination~~ **CONFIRMED** — Full `sklearn.Pipeline` (preprocessor + LGBMRegressor) serialized to `ml/artifacts/model.joblib` via `joblib.dump()`. Round-trip verification passed (prediction match). | Verified 2026-04-14 | N/A |

---

### About the LLM

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-11 | ~~GPT-4o (or an equivalent capable LLM with structured output support) is available and accessible via API key~~ **REVISED** — Using Ollama (`phi4-mini`) for development (local, free) and Groq (`llama-3.3-70b-versatile`) for production. Both expose OpenAI-compatible APIs; the `openai` Python SDK works with both. See ADR-007. | ADR-007, 2026-04-14 | If Groq's free tier has insufficient quota, switch to another OpenAI-compatible provider via env vars only |
| A-12 | ~~Structured JSON output mode (e.g., OpenAI response_format=json, function calling, or Pydantic AI) is reliable enough for Stage 1 extraction~~ **CONFIRMED** — `response_format={"type": "json_object"}` with few-shot examples produces parseable JSON reliably. Retry logic (1 attempt with stricter instruction) handles occasional malformed responses. 11 integration tests (T01–T10) pass without parse failures. See `tests/test_extraction_integration.py`. | Verified 2026-04-14 | N/A |
| A-13 | ~~Stage 1 LLM can reliably extract the 10–15 most important Ames features from a user's plain-English description~~ **CONFIRMED** — 11 integration tests (T01–T10) pass against Ollama `phi4-mini`. T01 extracted 11/12 fields correctly. JSON mode + few-shot examples + `Literal` enum validation = reliable extraction. See `tests/test_extraction_integration.py`. | Verified 2026-04-14 | N/A |
| A-14 | ~~Stage 2 LLM will not hallucinate statistics if the prompt explicitly provides the correct values in context~~ **CONFIRMED** — E05 integration test asserts every dollar amount in the explanation is within $1,000 of an allowed value from the injected context (`training_stats.json`). All 5 evaluation scenarios pass. Grounding instruction + vocabulary restriction prevents statistic invention in both `phi4-mini` (dev) and expected to generalize to `llama-3.3-70b-versatile` (prod). | Verified 2026-04-14 | N/A |
| A-15 | ~~Two separate LLM calls (extraction + explanation) will be more maintainable than a single combined prompt~~ **REVISED** — This is not a maintainability tradeoff. The two LLM calls sandwich a trained ML model inference step (`pipeline.predict()`), which is a deterministic mathematical function, not an LLM capability. Consolidating to a single LLM call would remove the ML model from the pipeline entirely, producing hallucinated prices with no reproducibility and no evaluatable MAE. The three-step architecture (LLM → ML → LLM) is a fundamental constraint, not a stylistic choice. Post-MVP consolidation is architecturally impossible without abandoning the ML model. | Verified 2026-04-15 | N/A |

---

### About Architecture & Deployment

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-16 | ~~Synchronous HTTP request handling is acceptable for MVP given expected latency of 3–8 seconds~~ **CONFIRMED** — SSE streaming eliminates perceived latency. Reply tokens stream immediately; explanation tokens stream word-by-word. Total pipeline time ~10–20s but user sees content within 2–3s. | ADR-002, verified 2026-04-15 | N/A |
| A-17 | ~~FastAPI + Uvicorn is sufficient for serving this system in a single-process, single-container setup~~ **CONFIRMED** — Single container serves all endpoints (health, extract, predict, chat). Handles 1 concurrent user without issue. Docker image runs on local machine and AWS. | Verified 2026-04-15 | N/A |
| A-18 | ~~Docker + docker-compose is sufficient for local deployment; no Kubernetes is required~~ **CONFIRMED** — `docker compose up` runs the full system locally. AWS deployment uses a single container (ECS Fargate or EC2). No orchestration needed at this scale. | Verified 2026-04-15 | N/A |
| A-19 | ~~The LLM API key will be available via environment variable; no secrets manager is needed~~ **CONFIRMED** — `.env` file locally; environment variables in AWS (ECS task definition or EC2 environment). Groq API key passed as `GROQ_API_KEY` env var. No secrets manager needed for MVP. | Verified 2026-04-15 | N/A |

---

### About the UI

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-20 | ~~A simple browser-based form UI is sufficient for MVP demonstration~~ **SUPERSEDED** — Replaced by conversational chat UI (ADR-008). Form-based UI could not handle arbitrary input (greetings, questions) or the missing-field conversation loop naturally. | ADR-008, 2026-04-15 | N/A |
| A-21 | ~~Form-based missing-field collection is adequate — no conversational back-and-forth is needed~~ **SUPERSEDED** — Missing fields are collected via natural-language conversation in the chat UI. Testing confirmed >50% of descriptions require follow-up — conversational collection is necessary. | ADR-008, 2026-04-15 | N/A |

### About Deployment (Post-MVP)

| ID | Assumption | Basis | Risk if Wrong |
|----|-----------|-------|---------------|
| A-22 | Google Cloud Run is suitable for hosting the FastAPI Docker container in production | Generous free tier (2M req/month); runs Docker natively; auto HTTPS; SSE works; `ENVIRONMENT=production` switches to Groq LLM. Supersedes original AWS assumption — see ADR-011. | If Cloud Run free tier is exhausted, AWS (see `docs/deployment/aws-guide.md`) or Railway are alternatives |
| A-23 | Vercel is suitable for hosting the standalone React frontend | Static site / serverless hosting; free tier adequate for demo; automatic deployments from Git | If Vercel free tier is insufficient, Netlify or Cloudflare Pages are equivalent alternatives |
| A-24 | The Ollama LLM provider is not available in cloud deployment — production must use Groq or another hosted LLM | Ollama requires a local GPU or CPU-heavy server; not practical on standard cloud VMs | If a GPU instance is provisioned, Ollama could run alongside the API container |

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
| U-06 | ~~Which 10–15 features will the LLM schema focus on?~~ **RESOLVED** — 12 features selected. **Required (4):** `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`. **Optional (8):** `TotalBsmtSF` (default 0), `GarageCars` (default 0), `FullBath` (default 1), `YearRemodAdd` (default = YearBuilt; UI hints when YearBuilt < 1990), `Fireplaces` (default 0), `LotArea` (default: neighborhood median), `MasVnrArea` (default 0), `Exterior1st` (default VinylSd). Full schema table in `ml/eda.ipynb` Section 9. | Phase 1 ✅ |
| U-07 | ~~What Ames-specific missing value codes mean semantically (e.g., NA = no garage)?~~ **RESOLVED** — NA in quality/condition/type columns means the feature is absent from the property, not a data recording error. These values carry predictive signal and must be preserved as a distinct `"None"` category or binary `Has___` column. See `ml/eda.ipynb` Section 4 decision table. | Phase 1 ✅ |
| U-08 | ~~Does neighborhood have a strong price effect? Is it a required feature in the schema?~~ **RESOLVED** — Yes, very strong. Box plot shows ~$350k spread between cheapest and most expensive neighborhoods (median range ~$75k–$320k). `Neighborhood` is a **required** schema field. Encoding: target encoding fit on training set only inside `sklearn.Pipeline`. | Phase 1 ✅ |
| U-09 | ~~Are there features that are near-duplicates (e.g., TotalBsmtSF vs BsmtFinSF1 + BsmtFinSF2)?~~ **RESOLVED** — Three redundant groups identified: (1) `GarageArea` vs `GarageCars` → keep `GarageCars`; (2) `GrLivArea` vs `1stFlrSF` vs `TotRmsAbvGrd` → keep `GrLivArea`; (3) `TotalBsmtSF` vs `BsmtFinSF1`/`BsmtUnfSF` → keep `TotalBsmtSF`. See `ml/eda.ipynb` Section 6 decision table. | Phase 1 ✅ |
| U-10 | ~~What should the imputation strategy be for each category of missing values?~~ **RESOLVED** — Group A (NA = no feature): encode as `"None"` or binary `Has___` — no imputation. Group B (true gaps): `LotFrontage` → median by Neighborhood; `GarageYrBlt` → fill with `YearBuilt`; `Electrical` (1 row) → mode. All statistics computed on training set only inside a `sklearn.Pipeline`. | Phase 1 ✅ |

---

## 3. Risks and Dependencies

### Technical Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-01 | ~~LLM JSON extraction is unreliable for complex schemas~~ **MITIGATED** — 12-field schema tested with 10+ queries (T01–T10); all pass. JSON mode + few-shot examples + retry logic handles edge cases. `Literal` enum types catch invalid values at validation. | Low | High | ✅ Schema simplified to 12 fields; tested with 11 integration tests |
| R-02 | ~~Data leakage is introduced silently during preprocessing~~ **MITIGATED** — Phase 2 leakage checklist fully passed. All preprocessing statistics computed inside `sklearn.Pipeline` on training data only. Outlier removal applied to training set before fitting. | Low | High | ✅ Leakage checklist enforced; all encoders/imputers inside Pipeline |
| R-03 | ~~Model performs poorly due to insufficient feature engineering~~ **MITIGATED** — LightGBM test MAE = $17,936 (69.9% improvement over $59,568 baseline), R² = 0.8885. Both targets exceeded without interaction features. | Low | Medium | ✅ Baseline documented; targets exceeded |
| R-04 | ~~Stage 2 LLM generates confident but incorrect statistics~~ **MITIGATED** — All statistics are injected from `ml/artifacts/training_stats.json` at prompt render time. E05 integration test asserts every dollar amount in the explanation is within $1,000 of an allowed value from the injected context. LLM is never asked to generate or recall a number. | Low | High | ✅ Grounding enforced by prompt; validated by E05 |
| R-05 | ~~LLM API cost becomes significant during development~~ **MITIGATED** — Dev uses Ollama (local, free). Prod uses Groq free tier. No cost observed. | Low | Low | ✅ Ollama for dev; Groq free tier for prod |
| R-06 | ~~Pydantic schema becomes out of sync with actual ML model features~~ **MITIGATED** — `_FEATURE_COLUMNS` in `prediction.py` is derived directly from `PropertyFeatures.model_fields.keys()` — the schema is the single source of truth. Any field name change in the schema automatically propagates to the DataFrame column order. Note: column *order* in the schema must still match training; this is enforced by a comment in `property_features.py` and would be caught by integration tests at runtime. | Low | High | ✅ Schema is single source of truth; no hardcoded column list |

### External Dependencies

| Dependency | Required By | Risk | Fallback |
|------------|------------|------|---------|
| OpenAI / Anthropic API access | Phase 3, Phase 4 | API key invalid or quota exceeded | **Revised** — Using Ollama (dev, no key) + Groq (prod). If Groq is unavailable, switch to another OpenAI-compatible provider via env vars. |
| Ames Housing dataset availability | Phase 1 | Dataset pulled from Kaggle/OpenML | Mirror locally; do not depend on live URL |
| scikit-learn, LightGBM, Pydantic | Phase 2, 3 | Version incompatibilities via pip | All versions pinned in `requirements.txt` |

---

## 4. Questions That Must Be Answered Before Coding

> These are the gates. No implementation begins until these are answered.

### Before Phase 2 (ML Foundation)

- [x] **Q1:** Which features will be included in the schema? **ANSWERED** — 12 features: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood`, `TotalBsmtSF`, `GarageCars`, `FullBath`, `YearRemodAdd`, `Fireplaces`, `LotArea`, `MasVnrArea`, `Exterior1st`. See `ml/eda.ipynb` Section 9 for full schema table.
- [x] **Q2:** What is the baseline MAE? **ANSWERED** — `DummyRegressor(strategy="median")` on the 12-feature schema: MAE = **$59,568**, RMSE = $88,667, R² = -0.025. Final model target: MAE < $30,000 (>49% reduction), R² > 0.85.
- [x] **Q3:** How will we handle categorical features with rare values that may not appear in production input? **ANSWERED** — `Exterior1st`: values with <10 training rows → binned to `"Other"` before one-hot encoding. `Neighborhood`: unseen values at inference → target encoder falls back to global training mean.
- [x] **Q4:** Will `SalePrice` be log-transformed? **Yes** — `np.log1p()` before training; `np.expm1()` on predictions. Raw skewness = 1.74, log1p skewness = 0.12. Confirmed via histogram and Q-Q plot in `ml/eda.ipynb` Section 5.
- [x] **Q5:** What imputation strategy will be used for numeric vs. categorical missing values? **ANSWERED** — Group A (NA = no feature): encode as `"None"` / binary. Group B: numeric → median (train only); categorical → mode (train only). All inside `sklearn.Pipeline`.

### Before Phase 3 (LLM Extraction Design)

- [x] **Q6:** What is the final set of features in the `PropertyFeatures` schema? **ANSWERED — LOCKED** — 12 features: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood` (required); `TotalBsmtSF`, `GarageCars`, `FullBath`, `YearRemodAdd`, `Fireplaces`, `LotArea`, `MasVnrArea`, `Exterior1st` (optional). Schema implemented in `app/schemas/property_features.py`. Model trained on this exact feature set.
- [x] **Q7:** Which features are "required" (prediction cannot proceed without them) vs "optional"? **ANSWERED** — Required: `GrLivArea`, `OverallQual`, `YearBuilt`, `Neighborhood` (no sensible default exists for these). Optional: remaining 8 features — each has a documented default value. UI shows accuracy hint for missing optionals; context-aware hint for `YearRemodAdd` when `YearBuilt < 1990`.
- [x] **Q8:** What is the exact JSON structure the Stage 1 prompt must return? **ANSWERED** — Wrapper object with guardrail: `{"is_property_description": bool, "features": {12 keys matching PropertyFeatures, null for unextractable} | null, "message": string | null}`. If `is_property_description` is false, `features` is null and `message` contains a redirect. If true, `features` contains the 12-key object.
- [x] **Q9:** How do we handle a property description that contains no extractable structured data? **ANSWERED** — Two cases: (1) Off-topic input → LLM returns `is_property_description: false` with a redirect message (guardrail). (2) Vague property text → LLM returns `is_property_description: true` with most features as `null` → required field check catches it → `PartialExtraction` response lists missing fields for UI collection.
- [x] **Q10:** Which LLM provider and model will be used? Is structured output mode available? **ANSWERED** — Ollama `phi4-mini` (dev) + Groq `llama-3.3-70b-versatile` (prod). Both expose OpenAI-compatible APIs. JSON mode available via `response_format={"type": "json_object"}`. See ADR-007.

### Before Phase 4 (Prediction Interpretation)

- [x] **Q11:** What statistics from the training data are most useful for grounding the explanation? **ANSWERED** — Overall median ($165,000), 25th/75th percentile ($130k / $215k), median price-per-sqft ($120.09), neighborhood median (lookup by `Neighborhood` field), and `top_features` ranked by LightGBM gain importance. All present in `ml/artifacts/training_stats.json`.
- [x] **Q12:** What is the format and location of the persisted training statistics file? **ANSWERED** — `ml/artifacts/training_stats.json`: flat JSON with fields `median_sale_price`, `mean_sale_price`, `std_sale_price`, `price_25th_percentile`, `price_75th_percentile`, `training_sample_size`, `median_price_per_sqft`, `neighborhood_median_price` (dict of 25 entries), `top_features` (ranked list), `model_type`, `features_used`, `required_features`.
- [x] **Q13:** How should the explanation handle predictions at the extremes? **ANSWERED** — Price bracket instructions injected into the prompt at render time: above 75th percentile → highlight premium factors; below 25th percentile → acknowledge limiting factors; otherwise → use overall median as anchor. Implemented in `build_explanation_prompt()` in `app/services/explanation.py`.

### Before Phase 5 (API & Containerization)

- [x] **Q14:** Will there be one combined endpoint (`POST /predict`) or separate stage endpoints? **ANSWERED** — Two endpoints: `POST /predict` runs the full pipeline (extract → validate → predict → explain); `POST /extract` runs Stage 1 only (for UI pre-validation and testing Stage 1 in isolation). No separate `/explain` endpoint — the explanation is always bundled with the prediction. Per architecture.instructions.md.
- [x] **Q15:** What is the final directory structure for the application code? **ANSWERED** — `app/main.py` (factory + lifespan), `app/config.py` (Settings), `app/routes/` (thin handlers), `app/services/` (pipeline stages), `app/schemas/` (Pydantic models), `app/clients/` (LLM client). Matches architecture.instructions.md file organization.
- [x] **Q16:** How will the model artifact and prompts be loaded into the Docker container? **ANSWERED** — `ml/artifacts/` and `prompts/` are COPY'd into the image at build time. `MODEL_PATH` and `STATS_PATH` env vars configure the paths inside the container, defaulting to `/app/ml/artifacts/`. No volume mounts required for the artifact — the image is self-contained.

---

## 5. How to Use This Document

1. When an assumption turns out to be wrong, strike it through and add a note referencing the ADR or decision that superseded it.
2. When an unknown is resolved via EDA, move it to its phase document with the answer recorded.
3. When a question is answered, check it off and document the answer inline.
4. This document is never "done" — it evolves throughout all phases.

---

*This document is a first-class engineering artifact. Vague comfort with assumptions is how projects fail.*
