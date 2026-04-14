"""
Unit tests for POST /extract and POST /predict route handlers.

All external dependencies (LLM client, model inference) are mocked.
The app.state is populated manually to simulate a successful startup.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.property_features import PropertyFeatures
from app.services.explanation import ExplanationError
from tests.conftest import make_extraction_json

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_FEATURES = {
    "GrLivArea": 1500,
    "OverallQual": 7,
    "YearBuilt": 2000,
    "Neighborhood": "NAmes",
}

ALL_FEATURES = {
    **MINIMAL_FEATURES,
    "TotalBsmtSF": 800,
    "GarageCars": 2,
    "FullBath": 2,
    "YearRemodAdd": 2005,
    "Fireplaces": 1,
    "LotArea": 8000,
    "MasVnrArea": 0.0,
    "Exterior1st": "VinylSd",
}


@pytest.fixture
def mock_app_state():
    """Populate app.state with a fake pipeline and training stats."""
    import joblib
    import numpy as np

    # Fake pipeline that returns a fixed log-transformed price (~$175k)
    fake_pipeline = MagicMock()
    fake_pipeline.predict.return_value = np.array([np.log1p(175_000)])

    # Minimal training_stats matching what build_explanation_prompt expects
    fake_stats = {
        "training_sample_size": 1168,
        "median_sale_price": 163000,
        "price_25th_percentile": 130000,
        "price_75th_percentile": 214975,
        "median_price_per_sqft": 120.09,
        "neighborhood_median_price": {"NAmes": 140000},
        "top_features": ["OverallQual", "GrLivArea"],
    }

    app.state.pipeline = fake_pipeline
    app.state.training_stats = fake_stats
    # Pre-load prompts from disk so route doesn't hit the filesystem per-request
    app.state.extraction_prompt = Path("prompts/extraction_v1.md").read_text()
    app.state.explanation_prompt = Path("prompts/explanation_v1.md").read_text()
    yield
    # Cleanup
    del app.state.pipeline
    del app.state.training_stats
    del app.state.extraction_prompt
    del app.state.explanation_prompt


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    async def test_health_ok_when_state_loaded(self, mock_app_state):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model_loaded"] is True
        assert body["stats_loaded"] is True

    async def test_health_503_when_no_state(self):
        # Ensure state is absent
        for attr in ("pipeline", "training_stats"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 503
        assert resp.json()["status"] == "unavailable"


# ---------------------------------------------------------------------------
# POST /extract
# ---------------------------------------------------------------------------

class TestExtractEndpoint:
    async def test_complete_extraction(self, mock_app_state):
        extraction_json = make_extraction_json(features=ALL_FEATURES)
        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=extraction_json)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/extract", json={"description": "A nice 3-bed house in NAmes built in 2000"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "complete"
        assert body["missing_required_fields"] == []

    async def test_partial_extraction_returns_missing_fields(self, mock_app_state):
        partial = {"GrLivArea": None, "OverallQual": None, "YearBuilt": None, "Neighborhood": None}
        extraction_json = make_extraction_json(features=partial)

        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=extraction_json)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/extract", json={"description": "A house"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "partial"
        assert set(body["missing_required_fields"]) == {"GrLivArea", "OverallQual", "YearBuilt", "Neighborhood"}

    async def test_not_a_property_description(self, mock_app_state):
        off_topic_json = make_extraction_json(is_property=False, message="Please describe a property.")

        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=off_topic_json)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/extract", json={"description": "What is the weather today?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_a_property"

    async def test_llm_parse_failure_returns_422(self, mock_app_state):
        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value="not json at all")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/extract", json={"description": "A house"})

        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["error_code"] == "EXTRACTION_PARSE_FAILURE"

    async def test_empty_description_rejected(self, mock_app_state):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/extract", json={"description": ""})
        # FastAPI Pydantic validation catches min_length=1
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /predict
# ---------------------------------------------------------------------------

class TestPredictEndpoint:
    async def test_full_pipeline_complete(self, mock_app_state):
        extraction_json = make_extraction_json(features=ALL_FEATURES)
        fake_explanation = "This property is estimated at $175,000 based on its features."

        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=extraction_json)):
            with patch("app.routes.predict.generate_explanation", new=AsyncMock(return_value=fake_explanation)):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    resp = await client.post("/predict", json={"description": "A 1500sqft house in NAmes, built 2000, quality 7"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "complete"
        assert isinstance(body["prediction_usd"], int)
        assert body["explanation"] == fake_explanation
        assert body["features"] is not None

    async def test_incomplete_when_required_fields_missing(self, mock_app_state):
        extraction_json = make_extraction_json(features={})  # all None

        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=extraction_json)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/predict", json={"description": "A house"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "incomplete"
        assert len(body["missing_required_fields"]) > 0

    async def test_supplemental_features_fill_gaps(self, mock_app_state):
        # Extraction returns only 2 required fields; supplemental provides the other 2
        partial = {"GrLivArea": 1500, "OverallQual": 7, "YearBuilt": None, "Neighborhood": None}
        extraction_json = make_extraction_json(features=partial)
        fake_explanation = "Estimated at $175,000."

        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=extraction_json)):
            with patch("app.routes.predict.generate_explanation", new=AsyncMock(return_value=fake_explanation)):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    resp = await client.post("/predict", json={
                        "description": "A 1500sqft house",
                        "supplemental_features": {"YearBuilt": 2000, "Neighborhood": "NAmes"},
                    })

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "complete"

    async def test_extraction_parse_failure_returns_422(self, mock_app_state):
        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value="not json")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/predict", json={"description": "A house"})

        assert resp.status_code == 422
        assert resp.json()["detail"]["error_code"] == "EXTRACTION_PARSE_FAILURE"

    async def test_not_a_property_returns_422(self, mock_app_state):
        off_topic_json = make_extraction_json(is_property=False)

        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=off_topic_json)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/predict", json={"description": "hello world"})

        assert resp.status_code == 422
        assert resp.json()["detail"]["error_code"] == "NOT_A_PROPERTY_DESCRIPTION"

    async def test_explanation_failure_returns_fallback_message(self, mock_app_state):
        extraction_json = make_extraction_json(features=ALL_FEATURES)

        with patch("app.services.extraction.chat_completion", new=AsyncMock(return_value=extraction_json)):
            with patch("app.routes.predict.generate_explanation", new=AsyncMock(side_effect=ExplanationError("LLM timeout"))):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    resp = await client.post("/predict", json={"description": "A nice house"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "complete"
        assert "unavailable" in body["explanation"].lower()

    async def test_model_not_loaded_returns_503(self):
        for attr in ("pipeline", "training_stats"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/predict", json={"description": "A house"})

        assert resp.status_code == 503
        assert resp.json()["detail"]["error_code"] == "MODEL_NOT_LOADED"

    async def test_empty_description_rejected(self, mock_app_state):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/predict", json={"description": ""})
        assert resp.status_code == 422
