"""
GET /insights — Market insights data for frontend visualizations.

Returns training statistics, neighborhood price comparisons,
feature importances, and model performance metrics.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.services.insights import build_insights_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/insights")
async def insights(request: Request) -> dict:
    """
    Return market insights data.

    Includes:
    - Price statistics (median, mean, percentiles, price per sqft)
    - Neighborhood median prices (sorted by price)
    - Feature importances (from the trained LightGBM model)
    - Model performance metrics (MAE, RMSE, R², baseline comparison)
    """
    if not hasattr(request.app.state, "pipeline") or request.app.state.pipeline is None:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error_code": "MODEL_NOT_LOADED",
                "message": "ML model is not available. Please retry in a moment.",
            },
        )

    if not hasattr(request.app.state, "training_stats") or request.app.state.training_stats is None:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error_code": "STATS_NOT_LOADED",
                "message": "Training statistics are not available.",
            },
        )

    return build_insights_response(
        request.app.state.pipeline,
        request.app.state.training_stats,
    )
