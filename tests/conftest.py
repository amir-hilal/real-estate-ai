"""Shared fixtures for the test suite."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.property_features import PropertyFeatures


@pytest.fixture
def mock_llm_client():
    """A mock AsyncOpenAI client whose chat.completions.create() is an AsyncMock."""
    client = AsyncMock()
    return client


def make_llm_response(content: str):
    """Build a fake ChatCompletion response object with the given content string."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def extraction_prompt():
    """Load the real extraction_v1.md prompt from disk."""
    path = Path("prompts/extraction_v1.md")
    return path.read_text(encoding="utf-8")


def make_extraction_json(
    features: dict | None = None,
    is_property: bool = True,
    message: str | None = None,
) -> str:
    """Build a JSON string mimicking the LLM extraction response format."""
    payload = {"is_property_description": is_property}
    if is_property:
        base = {field: None for field in PropertyFeatures.model_fields}
        if features:
            base.update(features)
        payload["features"] = base
        payload["message"] = message
    else:
        payload["features"] = None
        payload["message"] = message or "I'm a real estate pricing assistant."
    return json.dumps(payload)
