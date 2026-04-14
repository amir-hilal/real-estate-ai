"""Integration tests for Stage 1 extraction — requires a running Ollama instance.

Run with: pytest -m integration
Skip with: pytest -m "not integration"

These are the T01–T10 test cases from the Phase 3 test plan. Each sends a real
property description to the local Ollama model and validates the structured output.
"""

import pytest

from app.clients.llm import create_llm_client
from app.config import settings
from app.services.extraction import extract_features, load_extraction_prompt

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def llm_client():
    return create_llm_client()


@pytest.fixture(scope="module")
def system_prompt():
    return load_extraction_prompt(settings.prompts_dir, settings.extraction_prompt_version)


# ---------------------------------------------------------------------------
# T01: Full-detail description (happy path)
# ---------------------------------------------------------------------------

class TestT01FullDescription:

    async def test_extracts_most_fields(self, llm_client, system_prompt):
        desc = (
            "Beautiful 2-story home in College Creek, built in 2005. "
            "1,800 sq ft of living space, 3 full baths, 2-car garage, "
            "full basement of 1,200 sq ft. Vinyl siding exterior. "
            "Recently remodeled in 2018. Has a fireplace. "
            "Lot is about 9,000 sq ft. Quality is excellent throughout."
        )
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is True
        f = result.features
        assert f["GrLivArea"] == 1800
        assert f["Neighborhood"] == "CollgCr"
        assert f["YearBuilt"] == 2005
        assert f["OverallQual"] is not None and f["OverallQual"] >= 8
        assert f["TotalBsmtSF"] == 1200
        assert f["GarageCars"] == 2
        assert f["FullBath"] == 3
        assert f["YearRemodAdd"] == 2018
        assert f["Fireplaces"] == 1
        assert f["Exterior1st"] == "VinylSd"
        # At least 8 non-null fields (passing criterion)
        non_null = sum(1 for v in f.values() if v is not None)
        assert non_null >= 8


# ---------------------------------------------------------------------------
# T02: Minimal description
# ---------------------------------------------------------------------------

class TestT02Minimal:

    async def test_partial_extraction_with_missing_required(self, llm_client, system_prompt):
        desc = "A small ranch in North Ames, about 1100 sq ft, built in the 1960s."
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is True
        f = result.features
        assert f["GrLivArea"] == 1100
        assert f["Neighborhood"] == "NAmes"
        assert f["YearBuilt"] is not None and 1960 <= f["YearBuilt"] <= 1969
        assert "OverallQual" in result.missing_required


# ---------------------------------------------------------------------------
# T03: Neighborhood mentioned obscurely
# ---------------------------------------------------------------------------

class TestT03ObscureNeighborhood:

    async def test_neighborhood_inference(self, llm_client, system_prompt):
        desc = (
            "A 1,600 sq ft house near Iowa State University, built in 1975. "
            "Quality is about average. 2-car garage."
        )
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is True
        f = result.features
        # "near Iowa State" maps to SWISU per the prompt
        assert f["Neighborhood"] in ("SWISU", None)  # acceptable if LLM returns either
        assert f["GrLivArea"] == 1600


# ---------------------------------------------------------------------------
# T04: Approximate values
# ---------------------------------------------------------------------------

class TestT04ApproximateValues:

    async def test_approximate_sqft(self, llm_client, system_prompt):
        desc = (
            "About 2,000 square foot home in Sawyer West, probably built around 1985. "
            "Good condition, 1 fireplace."
        )
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is True
        f = result.features
        assert f["GrLivArea"] == 2000
        assert f["Neighborhood"] == "SawyerW"
        assert f["YearBuilt"] == 1985
        assert f["Fireplaces"] == 1


# ---------------------------------------------------------------------------
# T05: Garage capacity direct mention
# ---------------------------------------------------------------------------

class TestT05GarageCapacity:

    async def test_garage_extracted(self, llm_client, system_prompt):
        desc = (
            "A 1,400 sq ft brick home in Old Town built in 1920. "
            "Has a 1-car detached garage. Quality is below average."
        )
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is True
        f = result.features
        assert f["GarageCars"] == 1
        assert f["Neighborhood"] == "OldTown"
        # "brick home" may or may not be inferred as BrkFace exterior
        assert f["Exterior1st"] in ("BrkFace", None)


# ---------------------------------------------------------------------------
# T06: Informal language
# ---------------------------------------------------------------------------

class TestT06InformalLanguage:

    async def test_informal_text(self, llm_client, system_prompt):
        desc = "Cozy little place near downtown Ames, maybe 900 sq ft, built ages ago like the 1940s."
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is True
        f = result.features
        assert f["GrLivArea"] is not None
        assert f["YearBuilt"] is not None and 1940 <= f["YearBuilt"] <= 1949


# ---------------------------------------------------------------------------
# T07: No basement mention
# ---------------------------------------------------------------------------

class TestT07NoBasement:

    async def test_basement_is_null(self, llm_client, system_prompt):
        desc = (
            "A 1500 sq ft home in Sawyer, built in 1990, quality is about average. "
            "Has 2 full baths."
        )
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is True
        f = result.features
        assert f["TotalBsmtSF"] is None
        assert f["GrLivArea"] == 1500
        assert f["Neighborhood"] == "Sawyer"
        assert f["FullBath"] == 2
        assert result.missing_required == []


# ---------------------------------------------------------------------------
# T08: Contradictory information
# ---------------------------------------------------------------------------

class TestT08Contradictory:

    async def test_contradiction_does_not_crash(self, llm_client, system_prompt):
        desc = (
            "A 3-bedroom home in Gilbert with only 5 total rooms, 2200 sq ft, "
            "built in 2001. Excellent quality. Lot is 8,000 sq ft."
        )
        result = await extract_features(llm_client, desc, system_prompt)

        # The key assertion: it doesn't crash and returns a valid structure
        assert result.is_property_description is True
        assert result.features is not None
        assert result.features["GrLivArea"] == 2200
        assert result.features["Neighborhood"] == "Gilbert"


# ---------------------------------------------------------------------------
# T09: Mixed units / ambiguous floor area
# ---------------------------------------------------------------------------

class TestT09MixedUnits:

    async def test_ambiguous_area(self, llm_client, system_prompt):
        desc = (
            "A home in Edwards that's about 150 square meters, built in 1978. "
            "Has a big lot, around half an acre. Quality is average."
        )
        result = await extract_features(llm_client, desc, system_prompt)

        # LLM may reject metric units as non-standard, or attempt conversion
        # Either outcome is acceptable — key is no crash
        if result.is_property_description:
            f = result.features
            assert f is not None
            # GrLivArea should be converted (~1615 sqft) or null — not raw 150
            if f["GrLivArea"] is not None:
                assert f["GrLivArea"] >= 300  # within valid range
            assert f["Neighborhood"] == "Edwards"
        else:
            # Guardrail triggered — still a valid response
            assert result.message is not None


# ---------------------------------------------------------------------------
# T10: Non-property description (guardrail)
# ---------------------------------------------------------------------------

class TestT10Guardrail:

    async def test_off_topic_rejected(self, llm_client, system_prompt):
        desc = "What is the best investment strategy for real estate?"
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is False
        assert result.features is None
        assert result.message is not None

    async def test_greeting_rejected(self, llm_client, system_prompt):
        desc = "Hello! How are you today?"
        result = await extract_features(llm_client, desc, system_prompt)

        assert result.is_property_description is False
        assert result.features is None
