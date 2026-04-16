# Technical Process Overview

This document describes the end-to-end technical pipeline of the AI Real Estate Agent — from exploratory data analysis and model training through to the serving layer. It is written for a technical audience and traces each stage with enough detail to understand *why* each decision was made.

> **Dataset:** Ames Housing (1,460 rows × 81 columns)
> **Target variable:** `SalePrice` (continuous, USD)
> **Final model:** LightGBM regression pipeline (12 features → price prediction)

---

## Table of Contents

1. [Exploratory Data Analysis (EDA)](#1-exploratory-data-analysis)
   - [Train/Test Split](#11-traintestsplit)
   - [Missing Values Analysis](#12-missing-values-analysis)
   - [Target Variable Analysis](#13-target-variable-analysis)
   - [Feature Correlation and Importance](#14-feature-correlation-and-importance)
   - [Outlier Analysis](#15-outlier-analysis)
   - [Categorical Feature Analysis](#16-categorical-feature-analysis)
   - [Feature Selection](#17-feature-selection)
2. [Model Training](#2-model-training)
   - [Preprocessing Pipeline](#21-preprocessing-pipeline)
   - [Baseline Model](#22-baseline-model-dummyregressor)
   - [LightGBM Model](#23-lightgbm-model)
   - [Evaluation Results](#24-evaluation-results)
   - [Model Serialization](#25-model-serialization)
3. [API and Conversational Interface](#3-api-and-conversational-interface) *(next phase)*

---

## 1. Exploratory Data Analysis

**Implementation:** [`ml/eda.ipynb`](../ml/eda.ipynb)

The EDA phase resolves ten unknowns (U-01 through U-10) about the dataset before any model code is written. Every statistic, correlation, and visualization in this phase uses the **training set only** — the test set is never inspected until final model evaluation.

### 1.1 Train/Test Split

The very first operation on the raw data is an 80/20 split with `random_state=42`. This is done *before* any analysis, imputation, or encoding — violating this order is the most common source of data leakage.

```
1,460 rows → 1,168 train / 292 test
```

After the split, the training partition is used for all subsequent exploration. The test set is stored untouched for final evaluation in the training phase.

### 1.2 Missing Values Analysis

The Ames dataset has two fundamentally different kinds of missing values, and confusing them is a common error:

**Group A — "NA means the feature does not exist on this property"**

These are *not* data gaps. A `PoolQC = NaN` means the house has no pool; `FireplaceQu = NaN` means it has no fireplace. Dropping these columns or imputing the mode would destroy real signal.

| Column | Missing % | Meaning | Strategy |
|--------|-----------|---------|----------|
| `PoolQC` | ~99% | No pool | Encode as `"None"` category |
| `MiscFeature` | ~96% | No misc feature | Encode as `"None"` category |
| `Alley` | ~93% | No alley access | Encode as `"None"` / binary flag |
| `Fence` | ~80% | No fence | Encode as `"None"` category |
| `FireplaceQu` | ~47% | No fireplace | Encode as `"None"` — strong price signal |
| `GarageType/Finish/Qual/Cond` | ~5% | No garage | Encode as `"None"` category |
| `BsmtQual/Cond/Exposure/FinType` | ~2% | No basement | Encode as `"None"` category |
| `MasVnrType` | ~0.5% | No masonry veneer | Encode as `"None"` |
| `MasVnrArea` | ~0.5% | No masonry veneer | Fill with `0` |

**Group B — True missing values (data gaps)**

These are actual unknowns where a value exists but was not recorded.

| Column | Missing % | Strategy | Rationale |
|--------|-----------|----------|-----------|
| `LotFrontage` | ~17% | Median by Neighborhood (train only) | Lot sizes cluster by neighborhood |
| `GarageYrBlt` | ~5% | Fill with `YearBuilt` | Assume garage was built with the house |
| `Electrical` | 1 row | Mode (`SBrkr`) | Overwhelmingly most common value |

All imputation statistics (medians, modes) are computed on the training set only and stored inside the sklearn `Pipeline` — they are never recomputed on test data.

### 1.3 Target Variable Analysis

`SalePrice` exhibits strong right skew (skewness = 1.74): a long tail of luxury-priced homes compresses the majority of prices into the lower range. This is typical for real estate data.

**Log-transform decision:** Apply `np.log1p(SalePrice)` before training.

- Raw skewness: **1.74** (well above the 0.5 normality threshold)
- After `log1p`: **0.12** (near-normal)
- Q-Q plots confirm: the raw distribution has a heavy right tail curving away from the reference line; the log-transformed distribution is nearly linear end-to-end

The log transform compresses the luxury-price tail and produces better-calibrated proportional errors across the full price range. At inference time, predictions are converted back to USD with `np.expm1()`.

### 1.4 Feature Correlation and Importance

Two independent methods were used to rank feature importance, both on training data only:

1. **Pearson correlation** — linear association with `SalePrice`
2. **LightGBM feature importance** — non-linear/interaction signal from a quick 200-tree model

Both methods converge on the same top features, which indicates a mostly linear structure in the dataset — good news for model simplicity:

| Feature | \|Pearson r\| | LightGBM Rank | Notes |
|---------|--------------|---------------|-------|
| `OverallQual` | 0.80 | Top 1 | Strongest overall predictor |
| `GrLivArea` | 0.71 | Top 2 | Strongest numeric predictor |
| `GarageCars` | 0.64 | Top 5 | Kept over `GarageArea` (r=0.88 between them) |
| `TotalBsmtSF` | 0.61 | Top 4 | Kept over sub-components |
| `FullBath` | 0.54 | Present | — |
| `YearBuilt` | 0.52 | Top 8 | Users nearly always know this |
| `YearRemodAdd` | ~0.50 | Present | Correlated with `YearBuilt` but captures remodel signal |
| `Fireplaces` | ~0.47 | Present | — |
| `LotArea` | ~0.40 | Top 6 | — |
| `MasVnrArea` | ~0.40 | Present | Majority of homes have 0 |

**Near-duplicate features identified and resolved:**

- **Garage:** `GarageArea` and `GarageCars` are r=0.88 correlated → keep `GarageCars` (more natural to describe in English, higher target correlation)
- **Above-grade living:** `GrLivArea`, `1stFlrSF`, `TotRmsAbvGrd` overlap → keep `GrLivArea` (most precise)
- **Basement:** `TotalBsmtSF`, `BsmtFinSF1`, `BsmtUnfSF` → keep `TotalBsmtSF` (aggregate captures the price-relevant signal)

### 1.5 Outlier Analysis

The `GrLivArea` vs `SalePrice` scatter reveals 2 properties with very large living area (>4,000 sq ft) but abnormally low sale prices (<$200k). Both have `SaleCondition = "Partial"` — partial-interest transfers, not arms-length market transactions.

**Decision:** Remove these 2 rows from the training set only. The test set is not touched.

**Rationale:** Including partial-interest sales would teach the model an incorrect price-to-size relationship. The Ames dataset author (Dean De Cock) explicitly recommends removing these rows. All other columns (`YearBuilt`, `LotArea`, `GrLivArea`) pass bounds checks with no suspicious values.

### 1.6 Categorical Feature Analysis

Three categorical features have >10 unique values (high cardinality):

**Neighborhood (25 values) — Required feature**

The box plot reveals a ~$350k price spread across neighborhoods. Median sale prices range from ~$75k (Meadow Village) to ~$315k (Northridge Heights). This is too strong a signal to leave optional.

- **Encoding:** Target encoding, fit on training data only. `TargetEncoder` uses internal cross-validation to avoid leakage within the training fold.
- **Unseen values at inference:** The target encoder falls back to the global training mean.

**Exterior1st (~15 values) — Optional feature**

Standard siding materials (`VinylSd`, `HdBoard`, `MetalSd`, etc.). Values with <10 training rows (`BrkComm`, `ImStucc`, `CBlock`, `AsphShn`, `Stone`) are binned to `"Other"` before one-hot encoding to avoid near-empty columns.

**Exterior2nd (~15 values) — Dropped**

85% of rows have `Exterior2nd == Exterior1st`. Nearly no independent information — not worth including.

### 1.7 Feature Selection

The final schema uses **12 features** (4 required + 8 optional), selected by three criteria:

1. Strong signal (appears in both Pearson and LightGBM top lists)
2. A homeowner can describe it in plain English
3. Not redundant with a stronger feature already selected

| Feature | Ames Column | Type | Required | Default (if missing) |
|---------|------------|------|----------|---------------------|
| Above-grade living area | `GrLivArea` | int | **Yes** | — |
| Overall quality (1–10) | `OverallQual` | int | **Yes** | — |
| Year built | `YearBuilt` | int | **Yes** | — |
| Neighborhood | `Neighborhood` | categorical | **Yes** | — |
| Total basement area | `TotalBsmtSF` | int | No | `0` (no basement) |
| Garage capacity | `GarageCars` | int | No | `0` (no garage) |
| Full bathrooms | `FullBath` | int | No | `1` |
| Year remodeled | `YearRemodAdd` | int | No | `YearBuilt` |
| Fireplaces | `Fireplaces` | int | No | `0` |
| Lot area | `LotArea` | int | No | Neighborhood median (train) |
| Masonry veneer area | `MasVnrArea` | int | No | `0` (no veneer) |
| Exterior material | `Exterior1st` | categorical | No | `VinylSd` (mode from train) |

---

## 2. Model Training

**Implementation:** [`ml/model_training.ipynb`](../ml/model_training.ipynb)
**Artifacts:** [`ml/artifacts/model.joblib`](../ml/artifacts/model.joblib), [`ml/artifacts/training_stats.json`](../ml/artifacts/training_stats.json)

### 2.1 Preprocessing Pipeline

The preprocessing pipeline is built as a single `sklearn.Pipeline` + `ColumnTransformer` so that all fitted transformers are serialized together with the model. This is critical — at inference time, the pipeline must not depend on any external state or training data.

```
ColumnTransformer
├── num  (10 numeric features)  → SimpleImputer(strategy="median")
├── cat  (Exterior1st)          → SimpleImputer(strategy="most_frequent") → OneHotEncoder
└── nbhd (Neighborhood)         → SimpleImputer(strategy="most_frequent") → TargetEncoder
```

**Pre-pipeline steps** (applied before the `ColumnTransformer`):

1. **Rare exterior binning:** `Exterior1st` values with <10 training rows → replaced with `"Other"` (5 values: `BrkComm`, `ImStucc`, `CBlock`, `AsphShn`, `Stone`)
2. **Masonry veneer fill:** `MasVnrArea` NaN → `0` (Group A: no veneer means area is zero)
3. **Target log-transform:** `y_train_log = np.log1p(y_train)`

The pipeline is fit on training data only. The test set receives only `.transform()` — never `.fit_transform()`.

### 2.2 Baseline Model (DummyRegressor)

Before training any real model, a `DummyRegressor(strategy="median")` establishes the performance floor. It predicts the training-set median price for every input regardless of features.

| Metric | Baseline |
|--------|----------|
| Test MAE | **$59,568** |
| Test RMSE | $88,667 |
| Test R² | −0.025 |

The slightly negative R² is expected — `DummyRegressor` with `strategy="median"` does not optimize for variance explained (that would require `strategy="mean"`). This baseline defines the floor: any real model must beat $59,568 MAE by a meaningful margin.

### 2.3 LightGBM Model

#### What is LightGBM?

LightGBM (Light Gradient Boosting Machine) is a gradient-boosted decision tree framework developed by Microsoft. It builds an ensemble of decision trees sequentially — each new tree is trained to correct the errors of the ensemble built so far. The key innovations that distinguish LightGBM from earlier implementations (like XGBoost) are:

- **Histogram-based splitting:** Instead of evaluating every possible split point, LightGBM bins continuous features into discrete histograms and evaluates splits on the bins. This is faster and uses less memory.
- **Leaf-wise tree growth:** Most tree algorithms grow level-by-level (all nodes at the same depth). LightGBM grows leaf-wise — it picks the leaf with the highest loss reduction and splits that one. This produces deeper, more specialized trees that converge faster but can overfit more easily.
- **Native categorical support:** LightGBM can handle categoricals without one-hot encoding, though in this pipeline they are pre-encoded via `ColumnTransformer` for portability.

LightGBM was selected over alternatives (Ridge Regression, Random Forest, XGBoost) because the EDA showed the dataset has a structure with both linear and non-linear relationships. Both Pearson correlations and tree-based importance agreed on the top features, but the non-linear interactions (e.g., Neighborhood × OverallQual) benefit from a tree-based model. LightGBM was preferred over XGBoost for its faster training time on small-to-medium datasets.

#### Training Configuration

```python
LGBMRegressor(
    n_estimators=500,       # 500 boosting rounds
    learning_rate=0.05,     # conservative step size
    num_leaves=31,          # default leaf count
    random_state=42,        # reproducibility
)
```

No hyperparameter tuning was applied — this is a first run with sensible defaults. The model was fit on the log-transformed target (`y_train_log`) and predictions were inverted with `np.expm1()` before computing metrics in USD.

### 2.4 Evaluation Results

| Metric | Baseline | LightGBM | Target | Met? |
|--------|----------|----------|--------|------|
| Test MAE | $59,568 | **$17,936** | < $30,000 | Yes |
| Test RMSE | $88,667 | **$29,238** | — | — |
| Test R² | −0.025 | **0.8885** | > 0.85 | Yes |
| Train MAE | — | $5,029 | — | — |

**Improvement over baseline: 69.9%** (target was 49%).

#### Diagnostic Plots

Three evaluation plots are produced:

1. **Predicted vs Actual scatter** — Points cluster tightly around the diagonal with some spread at the high end (>$400k), which is expected given fewer luxury-price training examples.
2. **Residuals vs Predicted** — Residuals are randomly scattered around zero with no systematic pattern, confirming the model is not systematically biased in any price range.
3. **Feature Importance (gain)** — `OverallQual` and `GrLivArea` dominate, followed by `Neighborhood`, `TotalBsmtSF`, and `GarageCars`. This ranking matches the EDA correlation analysis, reinforcing confidence in the feature selection.

#### Overfitting Assessment

The train MAE ($5,029) is substantially lower than the test MAE ($17,936) — a 72% gap. This indicates some overfitting, as the model fits training-set noise that does not generalize. However, the test metrics still exceed all phase targets (MAE < $30k, R² > 0.85), so the model is accepted without regularization tuning. If production quality requires improvement, reducing `num_leaves` or increasing `min_child_samples` would help.

### 2.5 Model Serialization

The full `sklearn.Pipeline` (preprocessor + LightGBM model) is serialized together using `joblib.dump()` to `ml/artifacts/model.joblib`. This is critical: the serialized artifact must contain all fitted encoders, imputers, and scalers — not just the model weights.

**Verification step:** After saving, the artifact is loaded back and a prediction is run on one test row. The loaded pipeline's prediction must match the original pipeline's prediction exactly.

```
model.joblib → ~350 KB
Verification: original prediction == loaded prediction ✓
```

#### Training Statistics File

A separate `ml/artifacts/training_stats.json` is generated for the Stage 3 LLM explanation prompt. All values are computed from the **training set only**:

```json
{
  "median_sale_price": 165000,
  "mean_sale_price": 181457,
  "std_sale_price": 77327,
  "price_25th_percentile": 130000,
  "price_75th_percentile": 214975,
  "training_sample_size": 1166,
  "median_price_per_sqft": 120.09,
  "neighborhood_median_price": { ... },  // 25 neighborhoods
  "model_type": "LightGBM",
  "features_used": [ ... ],              // 12 features
  "required_features": [ ... ]           // 4 required
}
```

This file allows the explanation LLM to ground its output in real statistics (e.g., "this property is priced 20% above the neighborhood median") without accessing the model or training data directly.

---

## 3. API and Conversational Interface

*This section will be completed in the next phase of documentation, covering:*

- *FastAPI application structure and endpoint design*
- *LLM-based conversational feature extraction (Stage 1)*
- *ML prediction serving (Stage 2)*
- *LLM explanation generation with streaming responses (Stage 3)*
- *Chat interface and multi-turn conversation flow*
- *Docker containerization*
