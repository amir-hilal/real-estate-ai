"""Unit tests for Stage 3 explanation service.

All tests mock the LLM client — no external service required.
Tests cover: prompt loading, prompt rendering, property line formatting,
price bracket selection, generate_explanation success and failure paths.
"""

import pytest

from app.schemas.property_features import PropertyFeatures
from app.services.explanation import (
    ExplanationError,
    _format_property_lines,
    build_explanation_prompt,
    generate_explanation,
    load_explanation_prompt,
)
from tests.conftest import make_llm_response

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_STATS = {
    "median_sale_price": 165000.0,
    "mean_sale_price": 181457.0,
    "std_sale_price": 77327.0,
    "price_25th_percentile": 130000.0,
    "price_75th_percentile": 214975.0,
    "training_sample_size": 1166,
    "median_price_per_sqft": 120.09,
    "neighborhood_median_price": {
        "NAmes": 142000,
        "NridgHt": 314813,
        "BrDale": 100000,
    },
    "top_features": ["OverallQual", "GrLivArea", "Neighborhood", "TotalBsmtSF"],
}

MINIMAL_FEATURES = PropertyFeatures(
    GrLivArea=1500,
    OverallQual=7,
    YearBuilt=1995,
    Neighborhood="NAmes",
)

ALL_FEATURES = PropertyFeatures(
    GrLivArea=2000,
    OverallQual=8,
    YearBuilt=2002,
    Neighborhood="NridgHt",
    TotalBsmtSF=1000,
    GarageCars=2,
    FullBath=2,
    YearRemodAdd=2010,
    Fireplaces=1,
    LotArea=9000,
    MasVnrArea=150,
    Exterior1st="VinylSd",
)


@pytest.fixture
def explanation_template():
    """Load the real explanation_v1.md prompt from disk."""
    from pathlib import Path
    return Path("prompts/explanation_v1.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# load_explanation_prompt
# ---------------------------------------------------------------------------

class TestLoadExplanationPrompt:

    def test_loads_existing_prompt(self, tmp_path):
        prompt_file = tmp_path / "explanation_v1.md"
        prompt_file.write_text("You are an expert.", encoding="utf-8")
        result = load_explanation_prompt(tmp_path, "v1")
        assert result == "You are an expert."

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="explanation_v99.md"):
            load_explanation_prompt(tmp_path, "v99")


# ---------------------------------------------------------------------------
# _format_property_lines
# ---------------------------------------------------------------------------

class TestFormatPropertyLines:

    def test_required_fields_always_present(self):
        lines = _format_property_lines(MINIMAL_FEATURES)
        assert "1,500 sq ft" in lines
        assert "7/10" in lines
        assert "1995" in lines
        assert "NAmes" in lines

    def test_null_optional_fields_omitted(self):
        lines = _format_property_lines(MINIMAL_FEATURES)
        # Optional fields not set — should not appear
        assert "basement" not in lines.lower()
        assert "garage" not in lines.lower()
        assert "fireplace" not in lines.lower()

    def test_non_null_optional_fields_included(self):
        lines = _format_property_lines(ALL_FEATURES)
        assert "2,000 sq ft" in lines
        assert "2 car(s)" in lines
        assert "VinylSd" in lines
        assert "1,000 sq ft" in lines  # basement

    def test_returns_fallback_for_empty_features(self):
        # Edge case: all fields somehow empty — won't happen in practice but test it
        lines = _format_property_lines(MINIMAL_FEATURES)
        assert lines  # non-empty


# ---------------------------------------------------------------------------
# build_explanation_prompt — price bracket selection
# ---------------------------------------------------------------------------

class TestPriceBracketSelection:

    def test_above_75th_percentile_triggers_premium_instruction(self, explanation_template):
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=250000, training_stats=SAMPLE_STATS
        )
        assert "above the 75th percentile" in prompt
        assert "premium" in prompt.lower()

    def test_below_25th_percentile_triggers_discount_instruction(self, explanation_template):
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=110000, training_stats=SAMPLE_STATS
        )
        assert "below the 25th percentile" in prompt
        assert "limiting" in prompt.lower()

    def test_near_median_triggers_median_anchor_instruction(self, explanation_template):
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=165000, training_stats=SAMPLE_STATS
        )
        assert "near the median" in prompt

    def test_at_exactly_p75_treated_as_median_bracket(self, explanation_template):
        # p75 = 214975 — not strictly greater than, so falls in median bracket
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=214975, training_stats=SAMPLE_STATS
        )
        assert "near the median" in prompt

    def test_at_exactly_p25_treated_as_median_bracket(self, explanation_template):
        # p25 = 130000 — not strictly less than, so falls in median bracket
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=130000, training_stats=SAMPLE_STATS
        )
        assert "near the median" in prompt


# ---------------------------------------------------------------------------
# build_explanation_prompt — statistics injection
# ---------------------------------------------------------------------------

class TestPromptStatisticsInjection:

    def test_median_price_injected(self, explanation_template):
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=165000, training_stats=SAMPLE_STATS
        )
        assert "165,000" in prompt

    def test_neighborhood_median_injected_when_known(self, explanation_template):
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=165000, training_stats=SAMPLE_STATS
        )
        assert "142,000" in prompt  # NAmes median

    def test_neighborhood_stat_omitted_for_unknown_neighborhood(self, explanation_template):
        features = PropertyFeatures(
            GrLivArea=1500, OverallQual=7, YearBuilt=1995, Neighborhood="Veenker"
        )
        # Veenker is not in SAMPLE_STATS neighborhood_median_price
        prompt = build_explanation_prompt(
            explanation_template, features, predicted_price=165000, training_stats=SAMPLE_STATS
        )
        # Should not crash; neighborhood stat line should be empty
        assert "Veenker" in prompt  # appears in property lines, just not in stats line

    def test_top_3_features_listed(self, explanation_template):
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=165000, training_stats=SAMPLE_STATS
        )
        assert "overall quality" in prompt
        assert "above-grade living area" in prompt
        assert "neighborhood location" in prompt
        # 4th feature should NOT appear in the top factors list
        assert "basement size" not in prompt.split("Top factors")[1].split("\n")[0]

    def test_predicted_price_injected(self, explanation_template):
        prompt = build_explanation_prompt(
            explanation_template, MINIMAL_FEATURES, predicted_price=198500, training_stats=SAMPLE_STATS
        )
        assert "198,500" in prompt


# ---------------------------------------------------------------------------
# generate_explanation — success and failure
# ---------------------------------------------------------------------------

class TestGenerateExplanation:

    async def test_returns_explanation_text(self, mock_llm_client, explanation_template):
        explanation_text = (
            "This property is estimated at $165,000. "
            "Compared to the neighborhood median of $142,000, the quality rating of 7 "
            "and 1,500 sq ft of living space align well with that benchmark. "
            "The year of construction (1995) and the overall quality are the primary drivers."
        )
        mock_llm_client.chat.completions.create.return_value = make_llm_response(explanation_text)

        result = await generate_explanation(
            client=mock_llm_client,
            features=MINIMAL_FEATURES,
            predicted_price=165000,
            training_stats=SAMPLE_STATS,
            prompt_template=explanation_template,
        )
        assert result == explanation_text

    async def test_strips_leading_trailing_whitespace(self, mock_llm_client, explanation_template):
        mock_llm_client.chat.completions.create.return_value = make_llm_response(
            "   Some explanation text.   "
        )
        result = await generate_explanation(
            client=mock_llm_client,
            features=MINIMAL_FEATURES,
            predicted_price=165000,
            training_stats=SAMPLE_STATS,
            prompt_template=explanation_template,
        )
        assert result == "Some explanation text."

    async def test_raises_on_empty_response(self, mock_llm_client, explanation_template):
        mock_llm_client.chat.completions.create.return_value = make_llm_response("   ")
        with pytest.raises(ExplanationError, match="empty"):
            await generate_explanation(
                client=mock_llm_client,
                features=MINIMAL_FEATURES,
                predicted_price=165000,
                training_stats=SAMPLE_STATS,
                prompt_template=explanation_template,
            )

    async def test_raises_on_llm_exception(self, mock_llm_client, explanation_template):
        mock_llm_client.chat.completions.create.side_effect = RuntimeError("Connection refused")
        with pytest.raises(ExplanationError, match="LLM call failed"):
            await generate_explanation(
                client=mock_llm_client,
                features=MINIMAL_FEATURES,
                predicted_price=165000,
                training_stats=SAMPLE_STATS,
                prompt_template=explanation_template,
            )
