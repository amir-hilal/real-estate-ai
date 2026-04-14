"""Unit tests for Stage 1 extraction service.

All tests mock the LLM client — no external service required.
Tests cover: JSON parsing, Pydantic validation, guardrail detection,
required field checks, retry logic, and error raising.
"""

import json

import pytest

from app.services.extraction import (
    ExtractionError,
    _parse_extraction_response,
    _validate_features,
    extract_features,
    load_extraction_prompt,
)
from tests.conftest import make_extraction_json, make_llm_response


# ---------------------------------------------------------------------------
# load_extraction_prompt
# ---------------------------------------------------------------------------

class TestLoadExtractionPrompt:

    def test_loads_existing_prompt(self, tmp_path):
        prompt_file = tmp_path / "extraction_v1.md"
        prompt_file.write_text("You are an assistant.", encoding="utf-8")
        result = load_extraction_prompt(tmp_path, "v1")
        assert result == "You are an assistant."

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="extraction_v99.md"):
            load_extraction_prompt(tmp_path, "v99")


# ---------------------------------------------------------------------------
# _parse_extraction_response — guardrail
# ---------------------------------------------------------------------------

class TestGuardrail:

    def test_off_topic_returns_not_property(self):
        raw = make_extraction_json(is_property=False, message="Please describe a property.")
        result = _parse_extraction_response(raw)
        assert result is not None
        assert result.is_property_description is False
        assert result.features is None
        assert "property" in result.message.lower()

    def test_off_topic_with_default_message(self):
        raw = json.dumps({"is_property_description": False})
        result = _parse_extraction_response(raw)
        assert result.is_property_description is False
        assert result.message is not None  # default message provided


# ---------------------------------------------------------------------------
# _parse_extraction_response — JSON parsing
# ---------------------------------------------------------------------------

class TestJsonParsing:

    def test_invalid_json_returns_none(self):
        assert _parse_extraction_response("not json at all") is None

    def test_non_dict_json_returns_none(self):
        assert _parse_extraction_response("[1, 2, 3]") is None

    def test_empty_string_returns_none(self):
        assert _parse_extraction_response("") is None

    def test_whitespace_wrapped_json_parses(self):
        raw = "  \n" + make_extraction_json(features={"GrLivArea": 1500, "OverallQual": 5, "YearBuilt": 2000, "Neighborhood": "NAmes"}) + "\n  "
        result = _parse_extraction_response(raw)
        assert result is not None
        assert result.is_property_description is True


# ---------------------------------------------------------------------------
# _parse_extraction_response — full happy path
# ---------------------------------------------------------------------------

class TestHappyPath:

    def test_all_required_fields_present(self):
        raw = make_extraction_json(features={
            "GrLivArea": 1800,
            "OverallQual": 7,
            "YearBuilt": 2005,
            "Neighborhood": "CollgCr",
            "TotalBsmtSF": 1200,
            "GarageCars": 2,
        })
        result = _parse_extraction_response(raw)
        assert result.is_property_description is True
        assert result.missing_required == []
        assert result.features["GrLivArea"] == 1800
        assert result.features["OverallQual"] == 7
        assert result.features["Neighborhood"] == "CollgCr"
        assert result.features["TotalBsmtSF"] == 1200
        assert result.features["GarageCars"] == 2

    def test_optional_fields_default_to_none(self):
        raw = make_extraction_json(features={
            "GrLivArea": 1500,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
        })
        result = _parse_extraction_response(raw)
        assert result.features["TotalBsmtSF"] is None
        assert result.features["Fireplaces"] is None
        assert result.features["MasVnrArea"] is None


# ---------------------------------------------------------------------------
# _parse_extraction_response — missing required fields
# ---------------------------------------------------------------------------

class TestMissingRequired:

    def test_missing_one_required(self):
        """OverallQual missing → appears in missing_required."""
        raw = make_extraction_json(features={
            "GrLivArea": 1100,
            "YearBuilt": 1960,
            "Neighborhood": "NAmes",
        })
        result = _parse_extraction_response(raw)
        assert "OverallQual" in result.missing_required
        assert len(result.missing_required) == 1

    def test_missing_all_required(self):
        """No features at all → all 4 required are missing."""
        raw = make_extraction_json(features={})
        result = _parse_extraction_response(raw)
        assert set(result.missing_required) == {"GrLivArea", "OverallQual", "YearBuilt", "Neighborhood"}

    def test_features_key_none_treated_as_empty(self):
        """features: null in response → all required missing."""
        raw = json.dumps({"is_property_description": True, "features": None})
        result = _parse_extraction_response(raw)
        assert len(result.missing_required) == 4


# ---------------------------------------------------------------------------
# _validate_features — field-level validation
# ---------------------------------------------------------------------------

class TestValidateFeatures:

    def test_valid_features_pass_through(self):
        data = {
            "GrLivArea": 1500,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
        }
        result = _validate_features(data)
        assert result["GrLivArea"] == 1500
        assert result["Neighborhood"] == "NAmes"

    def test_out_of_range_int_nullified(self):
        """GrLivArea = 99999 exceeds max 6000 → set to None."""
        data = {
            "GrLivArea": 99999,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
        }
        result = _validate_features(data)
        assert result["GrLivArea"] is None

    def test_invalid_neighborhood_nullified(self):
        """Unknown neighborhood code → set to None."""
        data = {
            "GrLivArea": 1500,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "FakeHood",
        }
        result = _validate_features(data)
        assert result["Neighborhood"] is None

    def test_invalid_exterior_nullified(self):
        """Unknown exterior value → set to None."""
        data = {
            "GrLivArea": 1500,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
            "Exterior1st": "GoldPlated",
        }
        result = _validate_features(data)
        assert result["Exterior1st"] is None

    def test_wrong_type_nullified(self):
        """String where int is expected → set to None."""
        data = {
            "GrLivArea": "big",
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
        }
        result = _validate_features(data)
        assert result["GrLivArea"] is None

    def test_negative_optional_nullified(self):
        """GarageCars = -1 is below minimum 0 → set to None."""
        data = {
            "GrLivArea": 1500,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
            "GarageCars": -1,
        }
        result = _validate_features(data)
        assert result["GarageCars"] is None

    def test_valid_optional_preserved(self):
        data = {
            "GrLivArea": 1500,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
            "Fireplaces": 2,
            "MasVnrArea": 150.0,
        }
        result = _validate_features(data)
        assert result["Fireplaces"] == 2
        assert result["MasVnrArea"] == 150.0


# ---------------------------------------------------------------------------
# extract_features — async with mocked LLM
# ---------------------------------------------------------------------------

class TestExtractFeaturesAsync:

    async def test_successful_extraction(self, mock_llm_client):
        response_json = make_extraction_json(features={
            "GrLivArea": 1800,
            "OverallQual": 8,
            "YearBuilt": 2010,
            "Neighborhood": "NridgHt",
            "GarageCars": 3,
        })
        mock_llm_client.chat.completions.create.return_value = make_llm_response(response_json)

        result = await extract_features(mock_llm_client, "A large home...", "system prompt")
        assert result.is_property_description is True
        assert result.features["GrLivArea"] == 1800
        assert result.missing_required == []
        mock_llm_client.chat.completions.create.assert_called_once()

    async def test_guardrail_triggered(self, mock_llm_client):
        response_json = make_extraction_json(is_property=False, message="Not a property.")
        mock_llm_client.chat.completions.create.return_value = make_llm_response(response_json)

        result = await extract_features(mock_llm_client, "What is AI?", "system prompt")
        assert result.is_property_description is False
        assert result.features is None

    async def test_retry_on_bad_json_then_success(self, mock_llm_client):
        """First call returns garbage, second call returns valid JSON → success."""
        good_json = make_extraction_json(features={
            "GrLivArea": 1500,
            "OverallQual": 5,
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
        })
        mock_llm_client.chat.completions.create.side_effect = [
            make_llm_response("I cannot help with that."),  # bad JSON
            make_llm_response(good_json),  # valid retry
        ]

        result = await extract_features(mock_llm_client, "A house...", "system prompt")
        assert result.is_property_description is True
        assert result.features["GrLivArea"] == 1500
        assert mock_llm_client.chat.completions.create.call_count == 2

    async def test_raises_after_two_bad_json(self, mock_llm_client):
        """Both attempts return unparseable text → ExtractionError."""
        mock_llm_client.chat.completions.create.side_effect = [
            make_llm_response("Sorry, I can't do that."),
            make_llm_response("Still not JSON."),
        ]

        with pytest.raises(ExtractionError, match="2 attempts"):
            await extract_features(mock_llm_client, "A house...", "system prompt")

    async def test_partial_extraction_with_missing_fields(self, mock_llm_client):
        response_json = make_extraction_json(features={
            "GrLivArea": 1100,
            "YearBuilt": 1960,
            "Neighborhood": "NAmes",
            # OverallQual missing
        })
        mock_llm_client.chat.completions.create.return_value = make_llm_response(response_json)

        result = await extract_features(mock_llm_client, "Small ranch...", "system prompt")
        assert result.is_property_description is True
        assert "OverallQual" in result.missing_required
        assert result.features["GrLivArea"] == 1100

    async def test_invalid_field_nullified_during_extraction(self, mock_llm_client):
        """LLM returns an out-of-range value — validation nullifies it."""
        response_json = make_extraction_json(features={
            "GrLivArea": 1500,
            "OverallQual": 15,  # out of range 1-10
            "YearBuilt": 2000,
            "Neighborhood": "NAmes",
        })
        mock_llm_client.chat.completions.create.return_value = make_llm_response(response_json)

        result = await extract_features(mock_llm_client, "A house...", "system prompt")
        assert result.features["OverallQual"] is None
        assert "OverallQual" in result.missing_required
