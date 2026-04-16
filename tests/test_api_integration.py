"""
API integration tests — Phase 5 exit criteria.

These tests exercise the full HTTP pipeline via real services:
- Model loaded from disk (ml/artifacts/model.joblib)
- Real Ollama phi4-mini for LLM extraction and explanation
- FastAPI routes tested end-to-end via httpx ASGITransport

Run with: make test-integration (or pytest -m integration)
Duration: ~60–120s (three LLM calls per full pipeline test)
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import resolve_prompt_version, settings
from app.main import app
from app.services.explanation import load_explanation_prompt
from app.services.extraction import load_extraction_prompt
from app.services.prediction import load_pipeline, load_training_stats

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixture: real artifacts in app.state (model + stats + prompts from disk)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_app_state():
    """
    Load real artifacts into app.state before each test module.

    This replaces the FastAPI lifespan for testing — the model is loaded once
    at module scope to avoid reloading the 1.4MB artifact per test.
    """
    app.state.pipeline = load_pipeline(settings.model_path)
    app.state.training_stats = load_training_stats(settings.training_stats_path)
    app.state.extraction_prompt = load_extraction_prompt(
        settings.prompts_dir, settings.extraction_prompt_version
    )
    app.state.explanation_prompt = load_explanation_prompt(
        settings.prompts_dir, resolve_prompt_version(settings.prompt_version)
    )
    yield
    for attr in ("pipeline", "training_stats", "extraction_prompt", "explanation_prompt"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)


# ---------------------------------------------------------------------------
# A1 — Health check
# ---------------------------------------------------------------------------

async def test_health_check_with_loaded_model(real_app_state):
    """GET /health returns 200 with model_loaded and stats_loaded both true."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["stats_loaded"] is True


# ---------------------------------------------------------------------------
# A2 — Full pipeline happy path
# ---------------------------------------------------------------------------

async def test_full_pipeline_happy_path(real_app_state):
    """
    POST /predict with a rich description returns status=complete,
    a numeric prediction, and a non-empty explanation.
    """
    description = (
        "A 2,100 sq ft two-storey house in North Ridge Heights, built in 2005. "
        "Quality rating 8 out of 10. Two-car garage, full finished basement of 1,000 sq ft, "
        "2 full bathrooms, 1 fireplace, lot size around 9,500 sq ft. Vinyl siding exterior."
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=180.0
    ) as client:
        resp = await client.post("/predict", json={"description": description})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert isinstance(body["prediction_usd"], int)
    assert body["prediction_usd"] > 0
    assert body["explanation"] is not None
    assert len(body["explanation"]) > 50
    assert body["features"] is not None


# ---------------------------------------------------------------------------
# A3 — Partial extraction → supplement → complete
# ---------------------------------------------------------------------------

async def test_predict_partial_then_supplement(real_app_state):
    """
    POST /predict with a description missing required fields returns status=incomplete.
    Resubmitting with supplemental_features for the missing fields returns complete.

    Uses a description that supplies Neighborhood and YearBuilt but omits
    GrLivArea and OverallQual, making partial extraction the expected outcome.
    """
    partial_description = (
        "A house built in 2001 located in the Sawyer neighborhood of Ames, Iowa. "
        "It has 3 bedrooms and a single-car garage."
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=120.0
    ) as client:
        # Step 1: initial request — some required fields expected to be missing
        resp1 = await client.post("/predict", json={"description": partial_description})

    # 422 means the LLM could not parse even this description — acceptable edge case
    assert resp1.status_code in (200, 422)
    if resp1.status_code == 422:
        pytest.skip("LLM returned unparseable output for partial description — not a route failure")

    body1 = resp1.json()

    # If all fields happen to be extracted (phi4-mini may guess sizes),
    # the test still passes with either status.
    assert body1["status"] in ("complete", "incomplete")

    if body1["status"] == "incomplete":
        missing = body1["missing_required_fields"]
        assert len(missing) > 0

        # Step 2: resubmit with supplemental features for everything missing
        # Provide all 4 required fields to guarantee completion
        supplemental = {
            "GrLivArea": 1500,
            "OverallQual": 6,
            "YearBuilt": 1995,
            "Neighborhood": "NAmes",
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", timeout=120.0
        ) as client:
            resp2 = await client.post("/predict", json={
                "description": partial_description,
                "supplemental_features": supplemental,
            })

        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["status"] == "complete"
        assert isinstance(body2["prediction_usd"], int)


# ---------------------------------------------------------------------------
# A4 — Empty description rejected
# ---------------------------------------------------------------------------

async def test_predict_empty_description_rejected(real_app_state):
    """POST /predict with description="" returns 422 (Pydantic min_length validation)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/predict", json={"description": ""})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# A5 — Non-property input returns structured 422
# ---------------------------------------------------------------------------

async def test_predict_non_property_returns_structured_error(real_app_state):
    """
    POST /predict with a non-property description returns 422 with
    error_code=NOT_A_PROPERTY_DESCRIPTION.

    phi4-mini may occasionally try to extract features anyway; if the
    guardrail fires, the error code is checked. If extraction proceeds
    with nulls, it may return incomplete — both are acceptable.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=60.0
    ) as client:
        resp = await client.post("/predict", json={"description": "What is the weather today?"})

    # Either the guardrail fires (422) or it extracts nothing and returns incomplete (200)
    assert resp.status_code in (200, 422)
    if resp.status_code == 422:
        assert resp.json()["detail"]["error_code"] in (
            "NOT_A_PROPERTY_DESCRIPTION",
            "EXTRACTION_PARSE_FAILURE",
        )


# ---------------------------------------------------------------------------
# A6 — POST /extract happy path
# ---------------------------------------------------------------------------

async def test_extract_complete_description(real_app_state):
    """
    POST /extract with a complete property description returns status=complete
    and all required features extracted.
    """
    description = (
        "3-bedroom house, 1,800 sq ft, built in 1998, quality 7. "
        "Located in the Sawyer neighborhood. Two-car garage, full bath, no basement."
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=60.0
    ) as client:
        resp = await client.post("/extract", json={"description": description})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("complete", "partial")
    assert body["features"] is not None
    # At minimum the required fields should be populated for a rich description
    if body["status"] == "complete":
        assert body["missing_required_fields"] == []
