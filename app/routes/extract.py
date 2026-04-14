"""
POST /extract — Stage 1 only.

Accepts a plain-English property description and returns extracted features.
Does not run prediction or explanation. Used for UI pre-validation and
for testing Stage 1 in isolation.

Route handler is thin: it validates the request body, calls the service,
and maps the service result to the appropriate HTTP response.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.clients.llm import create_llm_client
from app.config import settings
from app.schemas.responses import ErrorResponse, ExtractResponse
from app.services.extraction import ExtractionError, extract_features, load_extraction_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


class ExtractRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Plain-English property description")


@router.post(
    "/extract",
    response_model=ExtractResponse,
    responses={
        422: {"model": ErrorResponse, "description": "LLM parse failure or Pydantic validation error"},
        503: {"model": ErrorResponse, "description": "Model not loaded"},
    },
)
async def extract(request: Request, body: ExtractRequest) -> ExtractResponse:
    """
    Run Stage 1 (LLM feature extraction) on a property description.

    Returns:
    - status="complete": all required features extracted
    - status="partial": some required features missing (listed in missing_required_fields)
    - status="not_a_property": input was not a property description
    """
    logger.info("POST /extract description_len=%d", len(body.description))

    # Load prompt (cached on app.state to avoid disk reads per-request)
    if not hasattr(request.app.state, "extraction_prompt"):
        request.app.state.extraction_prompt = load_extraction_prompt(
            settings.prompts_dir, settings.extraction_prompt_version
        )
    system_prompt = request.app.state.extraction_prompt

    client = create_llm_client()

    try:
        result = await extract_features(client, body.description, system_prompt)
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

    if not result.is_property_description:
        logger.info("POST /extract status=not_a_property")
        return ExtractResponse(
            status="not_a_property",
            message=result.message,
        )

    if result.missing_required:
        logger.info(
            "POST /extract status=partial missing=%s", result.missing_required
        )
        return ExtractResponse(
            status="partial",
            features=result.features,
            missing_required_fields=result.missing_required,
        )

    logger.info("POST /extract status=complete")
    return ExtractResponse(
        status="complete",
        features=result.features,
        missing_required_fields=[],
    )
