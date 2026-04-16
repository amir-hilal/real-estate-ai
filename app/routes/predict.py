"""
POST /predict — Full pipeline.

Runs the full pipeline: LLM extraction → Pydantic validation → ML prediction
→ LLM explanation.

Accepts an optional supplemental_features dict so the client can provide
values for fields that were missing from the initial extraction. This supports
the two-step UX flow (initial request → missing field collection → resubmit).

Route handler is thin: it validates inputs, calls service functions in sequence,
and maps results to HTTP responses.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.clients.llm import create_llm_client
from app.config import resolve_prompt_version, settings
from app.schemas.property_features import PropertyFeatures
from app.schemas.responses import ErrorResponse, PredictResponse
from app.services.explanation import ExplanationError, generate_explanation, load_explanation_prompt, build_explanation_prompt
from app.services.extraction import ExtractionError, extract_features, load_extraction_prompt
from app.services.prediction import predict

logger = logging.getLogger(__name__)

router = APIRouter()


class PredictRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Plain-English property description")
    supplemental_features: dict = Field(
        default_factory=dict,
        description="Feature values provided by user to fill gaps from extraction",
    )


@router.post(
    "/predict",
    response_model=PredictResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Extraction parse failure or validation error"},
        503: {"model": ErrorResponse, "description": "Model not loaded"},
    },
)
async def predict_route(request: Request, body: PredictRequest) -> PredictResponse:
    """
    Run the full pipeline on a property description.

    Returns:
    - status="complete": prediction and explanation returned
    - status="incomplete": required features still missing after extraction + supplemental merge
    """
    # Verify model is loaded (startup should have done this; 503 if not)
    if not hasattr(request.app.state, "pipeline") or request.app.state.pipeline is None:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error_code": "MODEL_NOT_LOADED",
                "message": "ML model is not available. Please retry in a moment.",
            },
        )

    logger.info(
        "POST /predict description_len=%d supplemental_keys=%s",
        len(body.description),
        list(body.supplemental_features.keys()),
    )

    pipeline = request.app.state.pipeline
    training_stats = request.app.state.training_stats

    # Load prompts (cached on app.state)
    if not hasattr(request.app.state, "extraction_prompt"):
        request.app.state.extraction_prompt = load_extraction_prompt(
            settings.prompts_dir, settings.extraction_prompt_version
        )
    if not hasattr(request.app.state, "explanation_prompt"):
        request.app.state.explanation_prompt = load_explanation_prompt(
            settings.prompts_dir, resolve_prompt_version(settings.prompt_version)
        )

    extraction_prompt = request.app.state.extraction_prompt
    explanation_prompt_template = request.app.state.explanation_prompt

    client = create_llm_client()

    # --- Stage 1: LLM extraction ---
    try:
        extraction = await extract_features(client, body.description, extraction_prompt)
    except ExtractionError as exc:
        logger.warning("Extraction failed: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "error_code": "EXTRACTION_PARSE_FAILURE",
                "message": "LLM did not return valid JSON. Please try again with a more detailed description.",
            },
        )

    if not extraction.is_property_description:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "error_code": "NOT_A_PROPERTY_DESCRIPTION",
                "message": extraction.message or "Input does not appear to be a property description.",
            },
        )

    # --- Merge supplemental features ---
    merged = {**(extraction.features or {}), **body.supplemental_features}

    # --- Pydantic validation on merged features ---
    try:
        validated_features = PropertyFeatures(**{k: v for k, v in merged.items() if v is not None})
    except Exception:
        # Re-check which required fields are still missing after merge
        from app.services.extraction import _REQUIRED_FIELDS
        missing = [f for f in _REQUIRED_FIELDS if merged.get(f) is None]
        if missing:
            return PredictResponse(
                status="incomplete",
                features=merged,
                missing_required_fields=missing,
                message="Please provide the missing fields to continue.",
            )
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "error_code": "VALIDATION_FAILURE",
                "message": "Feature values failed schema validation. Please check your inputs.",
            },
        )

    # Check required fields before attempting validation
    from app.services.extraction import _REQUIRED_FIELDS
    missing = [f for f in _REQUIRED_FIELDS if merged.get(f) is None]
    if missing:
        logger.info("POST /predict status=incomplete missing=%s", missing)
        return PredictResponse(
            status="incomplete",
            features=merged,
            missing_required_fields=missing,
            message="Please provide the missing fields to continue.",
        )

    # --- Stage 2: ML prediction ---
    predicted_price = predict(pipeline, validated_features)
    prediction_usd = int(round(predicted_price))

    # --- Stage 3: LLM explanation ---
    explanation: str | None = None
    try:
        prompt = build_explanation_prompt(
            explanation_prompt_template, validated_features, predicted_price, training_stats
        )
        explanation = await generate_explanation(
            client, validated_features, predicted_price, training_stats, prompt
        )
    except ExplanationError as exc:
        # Explanation failure is non-fatal — return prediction with fallback message
        logger.warning("Explanation generation failed: %s", exc)
        explanation = "Explanation temporarily unavailable."

    logger.info(
        "POST /predict status=complete prediction_usd=%d", prediction_usd
    )
    return PredictResponse(
        status="complete",
        features=validated_features.model_dump(),
        prediction_usd=prediction_usd,
        explanation=explanation,
    )
