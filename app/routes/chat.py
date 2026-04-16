"""
POST /chat — Conversational chat endpoint with SSE streaming.

Accepts a user message, conversation history, accumulated features,
and an optional prompt_version to select which chat prompt to use.
Streams SSE events: features, token, prediction, done, error.

The endpoint is stateless — all session state is managed by the client.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.clients.llm import create_llm_client
from app.config import resolve_prompt_version, settings
from app.schemas.chat import ChatRequest
from app.services.chat import load_chat_prompt, run_chat_turn
from app.services.explanation import load_explanation_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_chat_prompt(app_state, version: str) -> str:
    """Load a chat prompt by version, caching on app.state.chat_prompts dict."""
    if not hasattr(app_state, "chat_prompts"):
        app_state.chat_prompts = {}
    if version not in app_state.chat_prompts:
        app_state.chat_prompts[version] = load_chat_prompt(
            settings.prompts_dir, version
        )
    return app_state.chat_prompts[version]


def _get_explanation_prompt(app_state, version: str) -> str:
    """Load an explanation prompt by version, caching on app.state.explanation_prompts dict."""
    if not hasattr(app_state, "explanation_prompts"):
        app_state.explanation_prompts = {}
    if version not in app_state.explanation_prompts:
        app_state.explanation_prompts[version] = load_explanation_prompt(
            settings.prompts_dir, version
        )
    return app_state.explanation_prompts[version]


@router.post("/chat", include_in_schema=True)
async def chat_route(request: Request, body: ChatRequest) -> StreamingResponse:
    """
    Run one conversational turn and stream the result as SSE.

    Response content-type: text/event-stream

    Events:
      features   — {"extracted_features": {...}}  (metadata only)
      token      — {"text": "<chunk>"}   (reply AND explanation chunks)
      prediction — {"prediction_usd": 183400, "features": {...}}
      done       — {}
      error      — {"code": "...", "message": "..."}
    """
    if not hasattr(request.app.state, "pipeline") or request.app.state.pipeline is None:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error_code": "MODEL_NOT_LOADED",
                "message": "ML model is not available. Please retry in a moment.",
            },
        )

    # Resolve prompt version: client override or server default
    version = resolve_prompt_version(body.prompt_version or settings.prompt_version)

    logger.info(
        "POST /chat message_len=%d history_turns=%d accumulated_keys=%s prompt_version=%s",
        len(body.message),
        len(body.history),
        list(body.accumulated_features.keys()),
        version,
    )

    # Load chat and explanation prompts (cached per version)
    try:
        chat_prompt = _get_chat_prompt(request.app.state, version)
        explanation_prompt = _get_explanation_prompt(request.app.state, version)
    except FileNotFoundError:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "error",
                "error_code": "INVALID_PROMPT_VERSION",
                "message": f"Prompt version '{version}' not found.",
            },
        )

    client = create_llm_client()

    async def event_stream():
        async for event in run_chat_turn(
            client=client,
            message=body.message,
            history=body.history,
            accumulated_features=body.accumulated_features,
            pipeline=request.app.state.pipeline,
            training_stats=request.app.state.training_stats,
            chat_prompt_template=chat_prompt,
            explanation_prompt_template=explanation_prompt,
            prompt_version=version,
        ):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
