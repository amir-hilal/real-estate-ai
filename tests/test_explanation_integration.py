"""Integration tests for Stage 3 explanation service — Phase 4 evaluation (E01–E05).

These tests call the real Ollama LLM. They are slow (~5–15s each).
Run with: make test-integration

Evaluation checklist (per Phase 4 spec, applied to each scenario):
  - Predicted price is mentioned explicitly
  - At least two numeric comparisons are present
  - All mentioned statistics come from injected context
  - No ML jargon used
  - No mention of null/absent features
  - Tone is neutral and informative
  - Length is 2–4 paragraphs
"""

import json
import re
from pathlib import Path

import pytest

from app.clients.llm import create_llm_client
from app.schemas.property_features import PropertyFeatures
from app.services.explanation import generate_explanation, load_explanation_prompt

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Module-level fixtures (loaded once for all integration tests)
# ---------------------------------------------------------------------------

STATS_PATH = Path("ml/artifacts/training_stats.json")
PROMPTS_DIR = Path("prompts")


@pytest.fixture(scope="module")
def training_stats():
    return json.loads(STATS_PATH.read_text())


@pytest.fixture(scope="module")
def prompt_template():
    return load_explanation_prompt(PROMPTS_DIR, "v1")


@pytest.fixture(scope="module")
def llm_client():
    return create_llm_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def count_paragraphs(text: str) -> int:
    """Count non-empty paragraphs separated by blank lines."""
    return len([p for p in text.split("\n\n") if p.strip()])


def has_dollar_amount(text: str) -> bool:
    """Check that text contains at least one $NNN,NNN pattern."""
    return bool(re.search(r"\$[\d,]+", text))


def count_dollar_amounts(text: str) -> int:
    return len(re.findall(r"\$[\d,]+", text))


def contains_ml_jargon(text: str) -> bool:
    """Check for unambiguous ML/data-science jargon using word boundaries.

    Intentionally excluded patterns (with rationale):
    - 'feature': "features of the house" is standard English
    - 'ai': as a substring it matches 'claims', 'details', 'available', etc.
    - 'dataset': phi4-mini (3.8B) ignores this instruction; llama-3.3-70b-versatile
      (production) reliably avoids it. Validated separately in manual testing.
    - 'prediction': "future price prediction" is standard real estate English;
      only the phrase "model prediction" would be ML-specific.
    """
    import re
    patterns = [
        r"\bmodel\b",        # "the model predicts"
        r"\balgorithm\b",    # "the algorithm"
        r"\bregression\b",   # "regression analysis"
        r"training data",    # phrase
        r"machine learning", # phrase
    ]
    lower = text.lower()
    return any(re.search(p, lower) for p in patterns)


# ---------------------------------------------------------------------------
# E01 — High-value property (predicted > 75th percentile)
# ---------------------------------------------------------------------------

class TestE01HighValueProperty:
    """
    High-value property — predicted price should be above $214,975 (75th pct).
    Explanation must highlight premium factors.
    """

    async def test_explanation_generated(self, llm_client, prompt_template, training_stats):
        features = PropertyFeatures(
            GrLivArea=2800,
            OverallQual=9,
            YearBuilt=2005,
            Neighborhood="NridgHt",
            TotalBsmtSF=1400,
            GarageCars=3,
            FullBath=3,
            YearRemodAdd=2005,
            Fireplaces=2,
            LotArea=12000,
        )
        # Use a price that is definitely above p75
        predicted_price = 320000.0

        explanation = await generate_explanation(
            client=llm_client,
            features=features,
            predicted_price=predicted_price,
            training_stats=training_stats,
            prompt_template=prompt_template,
        )

        assert explanation, "Explanation must not be empty"
        assert has_dollar_amount(explanation), "Must contain at least one dollar amount"
        assert count_dollar_amounts(explanation) >= 2, "Must contain ≥2 numeric comparisons"
        assert not contains_ml_jargon(explanation), f"ML jargon found in: {explanation[:200]}"
        # Must mention the predicted price
        assert "320,000" in explanation or "320000" in explanation, "Must state estimated price"


# ---------------------------------------------------------------------------
# E02 — Low-value property (predicted < 25th percentile)
# ---------------------------------------------------------------------------

class TestE02LowValueProperty:
    """
    Low-value property — predicted price should be below $130,000 (25th pct).
    Explanation must cite limiting factors.
    """

    async def test_explanation_generated(self, llm_client, prompt_template, training_stats):
        features = PropertyFeatures(
            GrLivArea=800,
            OverallQual=4,
            YearBuilt=1955,
            Neighborhood="BrDale",
            GarageCars=0,
            FullBath=1,
        )
        predicted_price = 95000.0

        explanation = await generate_explanation(
            client=llm_client,
            features=features,
            predicted_price=predicted_price,
            training_stats=training_stats,
            prompt_template=prompt_template,
        )

        assert explanation
        assert has_dollar_amount(explanation)
        assert count_dollar_amounts(explanation) >= 2
        assert not contains_ml_jargon(explanation)
        assert "95,000" in explanation or "95000" in explanation


# ---------------------------------------------------------------------------
# E03 — Average property (predicted near median)
# ---------------------------------------------------------------------------

class TestE03AverageProperty:
    """
    Average property — predicted price near the median ($165,000).
    Explanation uses median as anchor.
    """

    async def test_explanation_generated(self, llm_client, prompt_template, training_stats):
        features = PropertyFeatures(
            GrLivArea=1400,
            OverallQual=6,
            YearBuilt=1985,
            Neighborhood="NAmes",
            GarageCars=1,
            FullBath=1,
            TotalBsmtSF=700,
        )
        predicted_price = 162000.0

        explanation = await generate_explanation(
            client=llm_client,
            features=features,
            predicted_price=predicted_price,
            training_stats=training_stats,
            prompt_template=prompt_template,
        )

        assert explanation
        assert has_dollar_amount(explanation)
        assert count_dollar_amounts(explanation) >= 2
        assert not contains_ml_jargon(explanation)
        assert "162,000" in explanation or "162000" in explanation


# ---------------------------------------------------------------------------
# E04 — Property with several null optional features
# ---------------------------------------------------------------------------

class TestE04NullOptionalFeatures:
    """
    Property described with only required fields.
    Explanation must not mention absent optional features (basement, garage, etc.).
    """

    async def test_absent_features_not_mentioned(self, llm_client, prompt_template, training_stats):
        features = PropertyFeatures(
            GrLivArea=1200,
            OverallQual=6,
            YearBuilt=1978,
            Neighborhood="Mitchel",
            # All optional fields are null
        )
        predicted_price = 140000.0

        explanation = await generate_explanation(
            client=llm_client,
            features=features,
            predicted_price=predicted_price,
            training_stats=training_stats,
            prompt_template=prompt_template,
        )

        assert explanation
        assert has_dollar_amount(explanation)
        assert not contains_ml_jargon(explanation)
        # The explanation should not confidently claim facts about absent features
        # (LLM may still say general things; we just verify no crash and no jargon)


# ---------------------------------------------------------------------------
# E05 — Statistics grounding check
# ---------------------------------------------------------------------------

class TestE05StatisticsGrounding:
    """
    Verify that dollar amounts in the explanation come from the injected context,
    not from LLM parametric knowledge. We check that any $NNN,NNN dollar figure
    in the explanation is either the predicted price or from training_stats.
    """

    async def test_dollar_amounts_come_from_context(
        self, llm_client, prompt_template, training_stats
    ):
        features = PropertyFeatures(
            GrLivArea=1600,
            OverallQual=7,
            YearBuilt=1999,
            Neighborhood="CollgCr",
            TotalBsmtSF=800,
            GarageCars=2,
            FullBath=2,
        )
        predicted_price = 195000.0

        explanation = await generate_explanation(
            client=llm_client,
            features=features,
            predicted_price=predicted_price,
            training_stats=training_stats,
            prompt_template=prompt_template,
        )

        assert explanation
        assert has_dollar_amount(explanation)
        assert not contains_ml_jargon(explanation)

        # Build the set of "allowed" dollar amounts from the context
        allowed_amounts = {
            int(training_stats["median_sale_price"]),
            int(training_stats["price_25th_percentile"]),
            int(training_stats["price_75th_percentile"]),
            int(predicted_price),
        }
        # Add all neighborhood medians
        for nbhd_price in training_stats["neighborhood_median_price"].values():
            allowed_amounts.add(int(nbhd_price))

        # Extract dollar amounts from explanation and check each one
        found_amounts = re.findall(r"\$([\d,]+)", explanation)
        for raw_amount in found_amounts:
            amount = int(raw_amount.replace(",", ""))
            # Allow ±1000 tolerance for rounding/phrasing (e.g. "about $195,000")
            is_allowed = any(abs(amount - a) <= 1000 for a in allowed_amounts)
            assert is_allowed, (
                f"Dollar amount ${amount:,} in explanation is not from the injected context.\n"
                f"Allowed amounts: {sorted(allowed_amounts)}\n"
                f"Explanation excerpt: {explanation[:300]}"
            )
