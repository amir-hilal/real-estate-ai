"""
Stage 1: LLM feature extraction.

Reads a plain-English property description, sends it to the LLM with the
extraction prompt, parses the JSON response, validates it against the
PropertyFeatures schema, and checks for missing required fields.

Implements the full validation chain from llm.instructions.md:
  LLM response → JSON parse → Pydantic validation → required field check
"""

import json
import logging
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.clients.llm import chat_completion
from app.config import settings
from app.schemas.property_features import PropertyFeatures
from app.schemas.responses import ExtractionResult

logger = logging.getLogger(__name__)

# Required fields that must be non-null for Stage 2 to proceed.
_REQUIRED_FIELDS = ["GrLivArea", "OverallQual", "YearBuilt", "Neighborhood"]


class ExtractionError(Exception):
    """Raised when the LLM response cannot be parsed into a valid extraction."""

    def __init__(self, message: str, raw_output: str | None = None):
        super().__init__(message)
        self.raw_output = raw_output


def load_extraction_prompt(prompts_dir: Path, version: str) -> str:
    """Load the extraction prompt file content."""
    prompt_path = prompts_dir / f"extraction_{version}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Extraction prompt not found at {prompt_path}. "
            f"Expected file: extraction_{version}.md in {prompts_dir}/"
        )
    return prompt_path.read_text(encoding="utf-8")


async def extract_features(
    client: AsyncOpenAI,
    description: str,
    system_prompt: str,
) -> ExtractionResult:
    """
    Run Stage 1: extract structured features from a property description.

    Returns an ExtractionResult with:
    - is_property_description: False if the input was off-topic (guardrail)
    - features: validated feature dict (null values preserved for missing fields)
    - missing_required: list of required field names that are null
    - message: redirect message if guardrail triggered, or None

    Raises ExtractionError if the LLM output cannot be parsed after one retry.
    """
    # First attempt
    raw = await chat_completion(
        client,
        system_prompt=system_prompt,
        user_message=description,
        json_mode=True,
    )

    result = _parse_extraction_response(raw)
    if result is not None:
        return result

    # Retry once with stricter instruction (per retry policy)
    logger.warning("First extraction attempt failed to parse. Retrying with stricter instruction.")
    retry_suffix = (
        "\n\nIMPORTANT: Your previous response was not valid JSON. "
        "Return ONLY a raw JSON object with no markdown, no commentary, no code fences."
    )
    raw = await chat_completion(
        client,
        system_prompt=system_prompt + retry_suffix,
        user_message=description,
        json_mode=True,
    )

    result = _parse_extraction_response(raw)
    if result is not None:
        return result

    raise ExtractionError(
        "LLM output could not be parsed as valid JSON after 2 attempts.",
        raw_output=raw,
    )


def _parse_extraction_response(raw: str) -> ExtractionResult | None:
    """
    Parse the LLM's raw string response into an ExtractionResult.

    Returns None if JSON parsing fails (caller should retry).
    Returns ExtractionResult on success (even with validation issues).
    """
    # Step 1: strip whitespace
    raw = raw.strip()

    # Step 2: JSON parse
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed. Raw output length: %d", len(raw))
        return None

    if not isinstance(data, dict):
        logger.warning("Parsed JSON is not a dict. Type: %s", type(data).__name__)
        return None

    # Step 3: check guardrail flag
    is_property = data.get("is_property_description", True)
    if not is_property:
        return ExtractionResult(
            is_property_description=False,
            features=None,
            message=data.get("message", "Please describe a property you'd like evaluated."),
        )

    # Step 4: extract features dict
    features_data = data.get("features")
    if features_data is None:
        # LLM said it's a property description but gave no features — treat as empty
        features_data = {}

    # Step 5: Pydantic validation — set invalid fields to null
    validated_features = _validate_features(features_data)

    # Step 6: check required fields
    missing = [
        field for field in _REQUIRED_FIELDS
        if validated_features.get(field) is None
    ]

    return ExtractionResult(
        is_property_description=True,
        features=validated_features,
        missing_required=missing,
    )


def _validate_features(features_data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate feature values against the PropertyFeatures schema.

    Valid fields are kept. Invalid fields (wrong type, out of range, bad enum)
    are set to None. This allows partial results to proceed.
    """
    # First, try full validation
    try:
        validated = PropertyFeatures(**features_data)
        return validated.model_dump()
    except ValidationError:
        pass

    # Field-by-field validation: keep valid, null-out invalid
    result: dict[str, Any] = {}
    field_info = PropertyFeatures.model_fields

    for field_name in field_info:
        value = features_data.get(field_name)
        if value is None:
            result[field_name] = None
            continue

        # Try validating just this field by constructing a minimal dict
        # with required fields filled with dummy values, then checking the target field
        try:
            # Build a test dict with this one real value + dummies for required fields
            test_data = _build_test_dict(field_name, value)
            obj = PropertyFeatures(**test_data)
            result[field_name] = getattr(obj, field_name)
        except (ValidationError, TypeError):
            logger.info(
                "Field %s failed validation (value=%r), setting to null",
                field_name,
                value,
            )
            result[field_name] = None

    return result


def _build_test_dict(target_field: str, target_value: Any) -> dict[str, Any]:
    """Build a minimal valid dict for PropertyFeatures with one real field value."""
    # Dummy values that pass validation for required fields
    defaults = {
        "GrLivArea": 1500,
        "OverallQual": 5,
        "YearBuilt": 2000,
        "Neighborhood": "NAmes",
    }
    # Set all optional fields to None
    optional_fields = [
        "TotalBsmtSF", "GarageCars", "FullBath", "YearRemodAdd",
        "Fireplaces", "LotArea", "MasVnrArea", "Exterior1st",
    ]
    test_data: dict[str, Any] = {f: None for f in optional_fields}
    test_data.update(defaults)
    test_data[target_field] = target_value
    return test_data
