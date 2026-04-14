"""
Stage 2: ML price prediction.

Loads the serialized sklearn Pipeline (preprocessor + LightGBM) at startup
and runs inference on a validated PropertyFeatures instance.

The pipeline handles all preprocessing internally — this service
only needs to convert PropertyFeatures to a DataFrame row.
"""

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.schemas.property_features import PropertyFeatures

logger = logging.getLogger(__name__)

# Rare Exterior1st values that were binned to "Other" during training.
# Must stay in sync with what was used in model_training.ipynb Section 3.
_RARE_EXTERIORS = {"BrkComm", "ImStucc", "CBlock", "AsphShn", "Stone"}

# Derived from the schema definition order, which must match training column order.
# Do not hardcode this list — let the schema be the single source of truth.
_FEATURE_COLUMNS = list(PropertyFeatures.model_fields.keys())


def load_pipeline(model_path: Path):
    """Load the serialized sklearn Pipeline from disk. Called once at startup."""
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model artifact not found at {model_path}. "
            "Run ml/model_training.ipynb to generate it."
        )
    pipeline = joblib.load(model_path)
    logger.info("Model pipeline loaded from %s", model_path)
    return pipeline


def load_training_stats(stats_path: Path) -> dict:
    """Load training summary statistics used by Stage 3 explanation prompt."""
    if not stats_path.exists():
        raise FileNotFoundError(
            f"Training stats not found at {stats_path}. "
            "Run ml/model_training.ipynb to generate it."
        )
    with open(stats_path) as f:
        return json.load(f)


def predict(pipeline, features: PropertyFeatures) -> float:
    """
    Run ML inference on a validated PropertyFeatures instance.

    Returns the predicted SalePrice in USD (log-transform inverted).
    The pipeline internally handles imputation and encoding —
    None values for optional fields are passed through as NaN,
    which the SimpleImputer handles.
    """
    row = _features_to_dataframe(features)
    log_pred = pipeline.predict(row)[0]
    price = float(np.expm1(log_pred))
    logger.debug("Prediction: $%.0f (log-scale: %.4f)", price, log_pred)
    return price


def _features_to_dataframe(features: PropertyFeatures) -> pd.DataFrame:
    """Convert PropertyFeatures to a single-row DataFrame matching the training schema."""
    data = features.model_dump()

    # Bin rare Exterior1st values — must match training-time preprocessing
    if data.get("Exterior1st") in _RARE_EXTERIORS:
        data["Exterior1st"] = "Other"

    # MasVnrArea: None → 0 (Group A: no veneer means area is 0)
    if data["MasVnrArea"] is None:
        data["MasVnrArea"] = 0.0

    # Build DataFrame in the exact column order used during training
    return pd.DataFrame([data])[_FEATURE_COLUMNS]
