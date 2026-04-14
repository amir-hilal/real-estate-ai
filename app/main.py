"""
FastAPI application factory + lifespan.

The ML pipeline is loaded once at startup via the lifespan context manager
and stored in app.state. Route handlers access it from there — it is never
loaded inside a request handler.
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.prediction import load_pipeline, load_training_stats

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Loading ML pipeline from %s", settings.model_path)
    app.state.pipeline = load_pipeline(settings.model_path)
    app.state.training_stats = load_training_stats(settings.training_stats_path)
    logger.info("Startup complete.")

    yield

    # --- Shutdown ---
    logger.info("Shutting down.")


app = FastAPI(
    title="AI Real Estate Agent",
    description="LLM extraction → ML prediction → LLM explanation pipeline",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    pipeline_loaded = hasattr(app.state, "pipeline") and app.state.pipeline is not None
    return {"status": "ok", "model_loaded": pipeline_loaded}


# Routes are registered here as they are implemented.
# from app.routes import predict_router, extract_router
# app.include_router(predict_router)
# app.include_router(extract_router)
