# Phase 2: ML Foundation

> **Status:** Complete  
> **Depends on:** Phase 1 EDA complete + feature shortlist finalized  
> **Blocks:** Phase 3 (LLM Extraction) — the schema is locked after this phase

---

## Purpose

This phase produces a trained, evaluated, and serialized regression model that can predict `SalePrice` from the features in the `PropertyFeatures` schema. The model must be:

- Trained without data leakage
- Evaluated on a held-out test set
- Serialized in a way that preserves the preprocessing pipeline exactly as trained
- Documented well enough that every design decision can be explained from first principles

This phase also produces the training statistics file used in Stage 3 (LLM explanation). Those statistics must come from the training set only.

---

## Model Training Plan

### Step 1: Lock the Feature List
Before any code is written, confirm the feature list from Phase 1. The ML model will be trained only on these features. Adding features later requires re-running this phase.

### Step 2: Split the Dataset
- Split before any preprocessing
- Use a stratified split if `SalePrice` is transformed (e.g., stratify on price quantile)
- Use `random_state=42` (or document your chosen seed)
- Standard split: 80% train / 20% test
- Do not look at the test set until final evaluation

### Step 3: Build the Preprocessing Pipeline
Define a `sklearn.pipeline.Pipeline` that includes:
- Imputation (median for numeric, mode or constant for categorical)
- Encoding (ordinal or one-hot for categorical features — decided in Phase 1)
- Optional: Scaling (tree-based models generally do not require scaling; linear models do)

The pipeline will be fit on training data only, then applied to both train and test.

### Step 4: Baseline Model
Before any complex model, implement a `DummyRegressor(strategy="median")` baseline.
- Record: Baseline MAE, RMSE, R²
- This is the floor. Any real model must beat this clearly.

### Step 5: Train Candidate Models
Suggested sequence:
1. Linear Regression (L2 regularized / Ridge) — establishes linear baseline
2. Random Forest Regressor — non-linear, robust to outliers, gives feature importances
3. Gradient Boosted Trees (XGBoost or LightGBM) — likely best performer

For each model:
- Train on training set only
- Evaluate on held-out test set
- Record MAE, RMSE, R² for both train and test sets
- Check for significant train/test gap (overfitting signal)

### Step 6: Basic Hyperparameter Tuning (Optional for MVP)
For the best-performing model:
- Use cross-validation on training data only
- Limit grid search to 2–3 parameters; do not over-tune
- Confirm test metrics after tuning (do not tune on test set)

### Step 7: Select the Final Model
Choose the model based on test-set performance AND explainability.
Document the selection rationale in `docs/decisions/architecture-decision-records.md`.

### Step 8: Compute Training Summary Statistics
Extract from the training set (after preprocessing, before splitting if possible):
- Median, mean, std, 25th/75th percentile of `SalePrice`
- Price statistics by `Neighborhood` (if used as a feature)
- Median price per square foot (if GrLivArea is a feature)
- Sample size used for training

Save this as a structured JSON or YAML file. This file is injected into the Stage 3 explanation prompt.

### Step 9: Serialize the Model
Save the full scikit-learn pipeline (preprocessor + model) using `joblib.dump()`.
- Save to `ml/artifacts/model.joblib` (or configured path)
- Save the training statistics to `ml/artifacts/training_stats.json`
- Do NOT save the model inside the source code directory — it is a runtime artifact, not source

---

## Leakage Prevention Checklist

> Every item on this list must be checked before any evaluation metrics are reported.  
> A failed item invalidates the metrics. Start over from the split if any item fails.

- [x] The train/test split was performed on the raw dataset, before any transformation
- [x] No preprocessing statistics (e.g., imputation values, encoding mappings) were computed using test data
- [x] Feature selection (if any) was performed using training data only
- [x] No feature was constructed using the target variable (`SalePrice`) or any proxy of it
- [x] The test set was not inspected for outliers or anomalies before evaluation
- [x] Cross-validation was performed on training data only; test data was never used in CV folds
- [x] No hyperparameter was tuned using test-set metrics
- [x] The final model was evaluated on the test set exactly once (not iteratively)
- [x] Log-transform of target (if applied) was applied consistently: during training and inverted at inference

---

## Preprocessing Decisions

Document these decisions here once Phase 1 EDA is complete:

| Feature | Missing Value Strategy | Encoding Strategy | Notes |
|---------|----------------------|-------------------|-------|
| `GrLivArea` | None (no missing) | Numeric — no encoding | Required |
| `OverallQual` | None (no missing) | Numeric — no encoding | Required; 1–10 integer |
| `YearBuilt` | None (no missing) | Numeric — no encoding | Required |
| `Neighborhood` | `most_frequent` imputer (0 missing) | `TargetEncoder` (fit on train only) | Required; 25 values |
| `TotalBsmtSF` | `median` imputer | Numeric — no encoding | Default 0 (no basement) |
| `GarageCars` | `median` imputer | Numeric — no encoding | Default 0 (no garage) |
| `FullBath` | `median` imputer | Numeric — no encoding | Default 1 |
| `YearRemodAdd` | `median` imputer | Numeric — no encoding | Default = YearBuilt at inference |
| `Fireplaces` | `median` imputer | Numeric — no encoding | Default 0 |
| `LotArea` | `median` imputer | Numeric — no encoding | Default = neighborhood median |
| `MasVnrArea` | Fill `0` before pipeline (Group A) | Numeric — no encoding | NA = no veneer → area is 0 |
| `Exterior1st` | `most_frequent` imputer | `OneHotEncoder` after binning rares (<10 rows → `"Other"`) | Optional; ~10 clean levels after binning |

### Guiding principles:
- Choose imputation values (median/mode) from training data only
- For ordinal-quality features (e.g., OverallQual: 1–10), use ordinal encoding, not one-hot
- For low-cardinality nominal features (e.g., CentralAir: Y/N), one-hot is fine
- For high-cardinality features (e.g., Neighborhood), consider target encoding on training data only or ordinal encoding by median price

---

## Model Comparison Plan

| Model | Expected Strengths | Expected Weaknesses | MVP Candidate? |
|-------|-------------------|--------------------|--------------------|
| DummyRegressor (median) | Zero complexity; baseline reference | Terrible predictions | Yes (baseline) |
| Ridge Regression | Fast, interpretable, good regularization | Linear only; can't capture interactions | Yes |
| Random Forest | Non-linear, handles missing well | Slower, less interpretable | Yes |
| XGBoost / LightGBM | State-of-the-art for tabular | Requires tuning | Yes (final candidate) |

---

## Evaluation Plan

### Primary Metrics

| Metric | Interpretation | Target (aspirational for Ames) |
|--------|---------------|-------------------------------|
| MAE (Mean Absolute Error) | Average absolute prediction error in USD | < $20,000 |
| RMSE (Root Mean Squared Error) | Penalizes large errors more heavily | < $30,000 |
| R² Score | Proportion of variance explained | > 0.85 |

> *Note: These targets are aspirational. Revise them after seeing the baseline.*

### Secondary Checks
- [x] Plot predicted vs. actual `SalePrice` scatter — look for systematic bias
- [x] Plot residuals distribution — should be approximately normal around zero
- [x] Compute feature importances and plot top 15 — used to validate schema decisions and inform Stage 3 prompt
- [x] Check for heteroscedasticity (residuals growing with predicted price) — may indicate missing features or the need for log-transform

---

## Expected Outputs

| Output | Path | Description |
|--------|------|-------------|
| Training notebook | `ml/model_training.ipynb` | Full training pipeline with documented decisions |
| Serialized model | `ml/artifacts/model.joblib` | Pipeline (preprocessor + model) via joblib |
| Training statistics | `ml/artifacts/training_stats.json` | Statistics from training set for Stage 3 prompt |
| Evaluation metrics | Documented in notebook + this phase doc | MAE, RMSE, R² on test set |
| Feature importance plot | Embedded in notebook | Top 15 features |

---

## Exit Criteria

Phase 2 is complete only when ALL of the following are true:

1. [x] The leakage-prevention checklist is fully checked
2. [x] Baseline MAE is documented — **$59,568**
3. [x] Final model MAE is meaningfully lower than baseline (by at least 30%) — **69.9% improvement**
4. [x] Test-set MAE, RMSE, and R² are documented in this file:
   - MAE: **$17,936**
   - RMSE: **$29,238**
   - R²: **0.8885**
5. [x] The model is serialized and loads correctly in a fresh Python process — verified `Match: True`
6. [x] Training statistics file exists and contains at minimum: median SalePrice, mean SalePrice, std SalePrice
7. [x] Feature importance analysis is complete and documented — Section 5 of `ml/model_training.ipynb`
8. [ ] Model selection rationale has an ADR entry — *add ADR-006 next*

---

## Common Pitfalls in This Phase

1. **Fitting a scaler on the full dataset** — always fit on train split only
2. **Using cross-validation results as the final reported metric** — CV is for model selection; final metrics come from the held-out test set
3. **Persisting the model without the preprocessor** — if preprocessing is not serialized, inference will fail or produce wrong results
4. **Reporting only train-set metrics** — high train R² with low test R² means overfitting, not success
5. **Using `OverallQual` or `OverallCond` without considering whether the LLM can provide them** — if these are important features but users can't describe them, they should be optional with sensible defaults or UI-collected fields

---

*This phase is not complete until you can explain every modeling decision out loud without notes.*
