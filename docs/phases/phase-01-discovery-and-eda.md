# Phase 1: Discovery and Exploratory Data Analysis (EDA)

> **Status:** Not Started  
> **Depends on:** Phase 0 (Documentation) complete  
> **Blocks:** Phase 2 (ML Foundation) — no modeling begins without Phase 1 findings

---

## Purpose

Before writing a single line of model training code, we must deeply understand the data. The Ames Housing dataset is well-documented but still contains surprises: unusual missing-value semantics, outliers that can distort model training, target distribution skew, and near-duplicate features.

EDA is not optional polish — it is the foundation of every decision in Phase 2 and Phase 3. A model built on misunderstood data will perform poorly and be difficult to debug. Assumptions made without EDA lead to bugs that appear during model evaluation, not during training.

---

## Objectives

By the end of Phase 1, the following must be true:

1. You can describe the shape, structure, and quality of the Ames dataset without opening it
2. You know which features are the most predictive of `SalePrice`
3. You know exactly what "missing" means for each column that has missing values
4. You have decided whether `SalePrice` needs a log transform
5. You have identified outliers and made a documented decision about whether to remove them
6. You have a shortlist of 10–20 features for the `PropertyFeatures` schema
7. You have documented every decision in this file's checklist and exit criteria

---

## Inputs

| Input | Source | Notes |
|-------|--------|-------|
| Ames Housing dataset (train.csv / test.csv or full dataset) | Kaggle, OpenML, or `amesdataset` Python package | Download before starting; do not depend on live URL |
| Ames Housing data dictionary | PDF or text file from the dataset source | Read this before opening the data — many column names are ambiguous without it |

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| EDA Jupyter notebook | `ml/eda.ipynb` | All exploratory analysis, plots, and findings |
| Updated phase doc | This file | Fill in all checklist items and exit criteria below |
| Feature shortlist | `docs/context/assumptions-and-open-questions.md` | Check off U-01 through U-10 as they are resolved |
| Updated `PropertyFeatures` schema draft | `docs/context/project-brief.md` | List the final candidate features |

---

## Checklist

Work through these in order. Do not skip ahead.

### Dataset Loading and Initial Inspection
- [ ] Load the dataset and confirm shape (expected: ~1,460 rows training, 79 features)
- [ ] Print column names and data types
- [ ] Read the Ames data dictionary for every column you plan to use — do not guess column semantics
- [ ] Identify which columns are numeric vs. categorical

### Missing Value Analysis
- [ ] Count missing values per column
- [ ] Identify columns with >20% missing — document each one and decide: drop, impute, or keep with special encoding
- [ ] Distinguish "NA" values that are semantically meaningful (e.g., PoolQC = NA → no pool) from genuine data gaps
- [ ] Document the imputation strategy for every column that will be used in modeling

### Target Variable Analysis
- [ ] Plot histogram of `SalePrice`
- [ ] Plot Q-Q plot of `SalePrice` to assess normality
- [ ] Compute skewness of `SalePrice`
- [ ] Decide: should `SalePrice` be log-transformed? Document the decision here: ________________
- [ ] If log-transforming: confirm predictions will be exponentiated back to USD before returning to the user

### Feature Correlation and Importance
- [ ] Compute Pearson correlation of all numeric features with `SalePrice`
- [ ] Plot the top 20 most correlated features (bar chart or heatmap)
- [ ] Identify near-duplicate or redundant features (e.g., TotalBsmtSF vs BsmtFinSF sums)
- [ ] Fit a quick RandomForest or LightGBM model (no tuning) to get initial feature importances
- [ ] Confirm or revise the shortlist based on computed importances

### Outlier Analysis
- [ ] Plot `GrLivArea` vs `SalePrice` — identify any extreme outliers (very large area, very low price)
- [ ] Decide: remove outliers before training? Documented decision: ________________
- [ ] Check for any clearly erroneous values in numeric columns (e.g., negative year built)

### Categorical Feature Analysis
- [ ] Count unique values per categorical feature
- [ ] Identify high-cardinality features (>20 unique values) and decide: keep, bin, or encode
- [ ] Plot `SalePrice` by `Neighborhood` to assess neighborhood price effect
- [ ] Decide whether `Neighborhood` should be a required field in the `PropertyFeatures` schema

### Feature Selection for Schema
- [ ] Select 10–20 features to include in the `PropertyFeatures` schema
- [ ] For each selected feature, document: name, type, valid range, required vs. optional, rationale
- [ ] Confirm all selected features are ones a person could reasonably describe in plain English
- [ ] Identify which features will be "required" for the ML model to run

### Final Documentation
- [ ] Write a 1-page "EDA Summary" section at the top of the notebook explaining the key findings
- [ ] Update `docs/context/assumptions-and-open-questions.md` — check off all resolved unknowns (U-01 through U-10)
- [ ] Add any new unknowns discovered during EDA

---

## Exit Criteria

Phase 1 is complete only when ALL of the following are true:

1. [ ] The EDA notebook runs end-to-end without errors
2. [ ] `SalePrice` log-transform decision is documented with supporting plots
3. [ ] Outlier treatment decision is documented with supporting plots
4. [ ] Every feature in the final shortlist has a documented imputation strategy
5. [ ] Feature shortlist (10–20 features) is finalized in writing
6. [ ] Required vs. optional feature classification exists for all schema candidates
7. [ ] All unknowns U-01 through U-10 are answered or explicitly deferred with justification

---

## Mistakes to Avoid

**Mistake 1: Fitting preprocessors before splitting**  
Never compute means, medians, encodings, or scalers on the full dataset before splitting into train/test. This is data leakage by a different name. Split first. Always.

**Mistake 2: Treating "NA" as "missing" without reading the data dictionary**  
In the Ames dataset, many "NA" values in categorical columns mean *the feature does not apply* (no garage, no pool). Imputing these with the mode or a placeholder is wrong — they should be encoded as a distinct "None" category.

**Mistake 3: Skipping the baseline**  
Always compute a naive baseline (predict median `SalePrice` for every input) before any model. This is your reference point. Without it, you cannot know if your model is actually useful.

**Mistake 4: Selecting features based on full-dataset correlation**  
Correlation must be computed on the training set only. Computing it on the full dataset and using it to select features is a subtle form of leakage.

**Mistake 5: Choosing features the LLM cannot extract**  
Some Ames features are assessor-specific (e.g., `OverallQual` is a 1–10 subjective rating assigned by the assessor). Ask yourself: *Can a homeowner or buyer realistically describe this in plain English?* If not, it should probably be optional with a default, not required.

---

## Key Decisions That Must Come Out of Phase 1

> These answers are required inputs for Phase 2. Do not start modeling without them.

1. **Target transform:** Will `SalePrice` be log-transformed? *(answer: ________)*
2. **Outlier policy:** Which (if any) rows will be removed? *(answer: ________)*
3. **Final feature list:** Which 10–20 features are in the schema? *(answer: see notebook)*
4. **Imputation strategy per feature:** *(answer: see notebook + updated assumptions doc)*
5. **Required features:** Which schema features are mandatory for prediction to proceed? *(answer: ________)*
6. **Encoding strategy:** Target encoding, ordinal encoding, or one-hot for categorical features? *(answer: ________)*

---

*Phase 1 is the only phase where "exploration" is the goal. All other phases have specific deliverables. Take the time here — it pays for itself.*
