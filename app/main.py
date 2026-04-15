"""
FastAPI application factory + lifespan.

The ML pipeline is loaded once at startup via the lifespan context manager
and stored in app.state. Route handlers access it from there — it is never
loaded inside a request handler.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.extract import router as extract_router
from app.routes.predict import router as predict_router
from app.routes.chat import router as chat_router

app.include_router(chat_router)
app.include_router(extract_router)
app.include_router(predict_router)


@app.get("/health")
async def health():
    pipeline_loaded = hasattr(app.state, "pipeline") and app.state.pipeline is not None
    stats_loaded = hasattr(app.state, "training_stats") and app.state.training_stats is not None
    status_code = 200 if (pipeline_loaded and stats_loaded) else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if status_code == 200 else "unavailable",
            "model_loaded": pipeline_loaded,
            "stats_loaded": stats_loaded,
        },
    )
