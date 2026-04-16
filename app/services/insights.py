"""
Market insights service.

Extracts feature importances from the loaded pipeline and combines them
with training statistics to produce data for frontend visualizations.
"""

import logging

from app.constants import NEIGHBORHOOD_NAMES

logger = logging.getLogger(__name__)

# Human-readable display names for model features
_DISPLAY_NAMES = {
    "OverallQual": "Overall Quality",
    "GrLivArea": "Living Area (sq ft)",
    "Neighborhood": "Neighborhood",
    "TotalBsmtSF": "Basement Area (sq ft)",
    "GarageCars": "Garage Capacity",
    "LotArea": "Lot Size (sq ft)",
    "YearRemodAdd": "Year Remodeled",
    "YearBuilt": "Year Built",
    "Fireplaces": "Fireplaces",
    "MasVnrArea": "Masonry Veneer Area",
    "FullBath": "Full Bathrooms",
}

# Numeric features in column order (must match training pipeline)
_NUMERIC_FEATURES = [
    "GrLivArea", "OverallQual", "YearBuilt",
    "TotalBsmtSF", "GarageCars", "FullBath", "YearRemodAdd",
    "Fireplaces", "LotArea", "MasVnrArea",
]


def extract_feature_importances(pipeline) -> list[dict]:
    """
    Extract feature importances (gain) from the LightGBM model inside the pipeline.

    Returns a list of {feature, display_name, importance} dicts sorted by importance desc.
    Exterior1st one-hot columns are aggregated into a single "Exterior Material" entry.
    """
    lgbm_model = pipeline.named_steps["model"]
    booster = lgbm_model.booster_

    # Reconstruct feature names after ColumnTransformer
    cat_enc = pipeline.named_steps["preprocessor"].named_transformers_["cat"]
    ext_feature_names = cat_enc.named_steps["onehot"].get_feature_names_out(
        ["Exterior1st"]
    ).tolist()
    feature_names = _NUMERIC_FEATURES + ext_feature_names + ["Neighborhood"]

    importances = booster.feature_importance(importance_type="gain")

    # Aggregate Exterior1st one-hot columns into a single entry
    results = []
    exterior_total = 0.0
    for name, imp in zip(feature_names, importances):
        if name.startswith("Exterior1st_"):
            exterior_total += float(imp)
        else:
            results.append({
                "feature": name,
                "display_name": _DISPLAY_NAMES.get(name, name),
                "importance": float(imp),
            })
    if exterior_total > 0:
        results.append({
            "feature": "Exterior1st",
            "display_name": "Exterior Material",
            "importance": exterior_total,
        })

    results.sort(key=lambda x: x["importance"], reverse=True)
    return results


def build_insights_response(pipeline, training_stats: dict) -> dict:
    """
    Build the full market insights payload for the frontend.

    Combines training statistics, neighborhood price data,
    feature importances, and model performance metrics.
    """
    # Feature importances from the loaded pipeline
    feature_importances = extract_feature_importances(pipeline)

    # Neighborhood prices sorted by median price (descending)
    nbhd_prices = training_stats.get("neighborhood_median_price", {})
    neighborhoods = sorted(
        [
            {
                "code": code,
                "name": NEIGHBORHOOD_NAMES.get(code, code),
                "median_price": price,
            }
            for code, price in nbhd_prices.items()
        ],
        key=lambda x: x["median_price"],
        reverse=True,
    )

    return {
        "price_statistics": {
            "median": training_stats["median_sale_price"],
            "mean": round(training_stats["mean_sale_price"]),
            "std": round(training_stats["std_sale_price"]),
            "percentile_25": training_stats["price_25th_percentile"],
            "percentile_75": training_stats["price_75th_percentile"],
            "median_price_per_sqft": round(training_stats["median_price_per_sqft"], 2),
            "sample_size": training_stats["training_sample_size"],
        },
        "neighborhoods": neighborhoods,
        "feature_importances": feature_importances,
        "model_performance": training_stats.get("model_performance", {}),
    }
