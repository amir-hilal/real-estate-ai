---
applyTo: "ml/**,app/services/**,app/schemas/**"
---

# ML Instructions

These instructions govern all machine learning code, notebooks, and model artifacts in this project.

---

## The Most Important ML Rule

**Never touch the test set until final evaluation.**

The test set exists to give you an honest estimate of how the model performs on unseen data. Every time you look at the test set and make a decision based on it — even an indirect one like modifying a feature — you corrupt that estimate. The test set is read-only until you are done with model development.

---

## Data Splitting Rules

1. **Always split before preprocessing.** The first operation on the raw dataset is splitting into train and test. No exceptions.
2. **Use a fixed random seed.** Set `random_state=42` (or document your chosen seed in the phase document). Training must be reproducible.
3. **Standard split: 80% train / 20% test.** Do not change this without an ADR entry.
4. **Never re-split.** The split is made once. Changing the split invalidates all evaluation metrics.

---

## Leakage Prevention Rules

Data leakage produces models with inflated metrics that fail in production. These rules are the enforcement mechanism:

1. **Preprocessing statistics (mean, median, mode, std) must be computed on training data only.** Never compute them on the full dataset and apply to train/test separately.
2. **Encoders (OrdinalEncoder, OneHotEncoder, TargetEncoder) must be fit on training data only.**
3. **Feature selection decisions must be based on training-set correlations and importances, not full-dataset statistics.**
4. **Cross-validation is performed on training data only.** The test set never participates in CV folds.
5. **Hyperparameter tuning is performed on training data (via CV) only.** Do not tune against the test set.
6. **The final model is evaluated on the test set exactly once.** Iterative tuning against test metrics is leakage.

Before reporting any evaluation metrics, run through the full leakage checklist in `docs/phases/phase-02-ml-foundation.md`.

---

## Pipeline Serialization Rules

1. **The preprocessing pipeline and model must be serialized together.** Never serialize the model alone. The sklearn `Pipeline` object wrapping both preprocessor and estimator is the artifact.
2. **Use `joblib.dump()` to serialize.** Use a fixed filename: `ml/artifacts/model.joblib`.
3. **Test the serialized artifact in a fresh process.** Load `model.joblib` in a new Python session (no existing variables), call `predict()`, and confirm it runs without errors before considering serialization complete.
4. **The serialized pipeline must not depend on training data at inference time.** All fitted encoders, scalers, and imputers must be inside the pickle.
5. **If the feature schema changes, the model must be re-trained.** A model trained on a different feature set than the current `PropertyFeatures` schema is broken — not just suboptimal.

---

## Baseline First Rule

Before training any complex model:
1. Implement `DummyRegressor(strategy="median")` as the baseline
2. Record baseline MAE, RMSE, and R² on the test set
3. All subsequent models must beat the baseline meaningfully (not marginally)
4. If a complex model barely beats the baseline, it is not justified — document this

---

## Target Variable Rules

1. **Check the distribution of `SalePrice` before assuming normality.**
2. **If log-transforming: apply `np.log1p()` to the target before training.**
3. **If log-transforming: predictions must be converted back with `np.expm1()` before returning to the user.** Never return log-scale predictions.
4. **Document the transform decision in the phase document.** Do not silently apply transforms.

---

## Feature Engineering Rules

1. **Prefer clean encoding over invented features for MVP.** Do not create interaction features unless EDA shows a specific, documented need.
2. **Ordinal features (e.g., quality ratings 1–10) should use ordinal encoding, not one-hot.** One-hot encoding a 1–10 scale discards the ordering information.
3. **Ames "NA" values in categorical columns are meaningful categories, not missing data.** Encode them as a distinct "None" or "No feature" category — do not impute them with the mode.
4. **High-cardinality categories (e.g., Neighborhood) require careful encoding.** Target encoding must be fit on training data only. Document the choice.

---

## Evaluation Rules

1. Report MAE, RMSE, and R² for both train and test sets.
2. A large train/test gap (e.g., train R²=0.96, test R²=0.82) signals overfitting — document it.
3. Always plot predicted vs. actual scatter for qualitative residual check.
4. Feature importance analysis is required, not optional — it informs the LLM explanation design.

---

## Training Statistics File

After training is complete, compute and save `ml/artifacts/training_stats.json`:
- This file is used by the Stage 3 LLM explanation prompt
- It must come from the **training set only** (never full dataset or test set)
- Required keys at minimum: `median_sale_price`, `mean_sale_price`, `std_sale_price`, `price_25th_percentile`, `price_75th_percentile`, `training_sample_size`
- If `Neighborhood` is a feature: include median price per neighborhood
- If `GrLivArea` is a feature: include median price per square foot

---

## Notebook Discipline

ML notebooks are not scratch pads. They are documentation:
1. Add a markdown summary section at the top of each notebook explaining the goals and key findings
2. Number cells logically; ensure the notebook runs top-to-bottom without errors
3. Document each significant decision as a markdown cell, not just as code comments
4. Keep cells small and focused — one action per cell
5. Do not leave debug output (raw stack traces, half-completed exploratory code) in committed notebooks

---

## What Not to Do in ML Code

- Do not use `fit_transform()` on the test set — only `transform()`
- Do not compute metrics on training data only and present them as model quality
- Do not add features to the model without adding them to the `PropertyFeatures` Pydantic schema
- Do not use `random_state=None` (non-reproducible)
- Do not ignore convergence warnings without investigating them
- Do not silently catch and swallow `ValueError` from sklearn — surface them
