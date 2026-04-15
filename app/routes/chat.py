"""
POST /chat — Conversational chat endpoint with SSE streaming.

Accepts a user message, conversation history, and accumulated features.
Streams SSE events: reply, prediction, token, done, error.

The endpoint is stateless — all session state is managed by the client.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.clients.llm import create_llm_client
from app.config import settings
from app.schemas.chat import ChatRequest
from app.services.chat import load_chat_prompt, run_chat_turn
from app.services.explanation import load_explanation_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", include_in_schema=True)
async def chat_route(request: Request, body: ChatRequest) -> StreamingResponse:
    """
    Run one conversational turn and stream the result as SSE.

    Response content-type: text/event-stream

    Events:
      reply      — {"text": "...", "extracted_features": {...}}
      prediction — {"prediction_usd": 183400, "features": {...}}
      token      — {"text": "<chunk>"}   (explanation chunks)
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

    logger.info(
        "POST /chat message_len=%d history_turns=%d accumulated_keys=%s",
        len(body.message),
        len(body.history),
        list(body.accumulated_features.keys()),
    )

    # Load prompts once per app lifetime (cache on app.state)
    if not hasattr(request.app.state, "chat_prompt"):
        request.app.state.chat_prompt = load_chat_prompt(
            settings.prompts_dir, settings.chat_prompt_version
        )
    if not hasattr(request.app.state, "explanation_prompt"):
        request.app.state.explanation_prompt = load_explanation_prompt(
            settings.prompts_dir, settings.explanation_prompt_version
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
            chat_prompt_template=request.app.state.chat_prompt,
            explanation_prompt_template=request.app.state.explanation_prompt,
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
