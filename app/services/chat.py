"""
Chat orchestration service.

Handles one conversational turn:
  1. Build system prompt with already-known / still-missing feature context
  2. Call LLM (non-streaming) to classify intent + extract new features
  3. Merge new features with accumulated_features from the client
  4. If intent="chat" or required fields still missing → yield reply event → done
  5. If all required fields present →
       yield prediction event (ML inference)
       yield token events (streaming explanation)
       yield done event
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, AsyncIterator

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.clients.llm import chat_completion, chat_completion_stream
from app.config import settings
from app.schemas.chat import ChatMessage
from app.schemas.property_features import PropertyFeatures
from app.services.explanation import build_explanation_prompt, load_explanation_prompt
from app.services.prediction import predict

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ["GrLivArea", "OverallQual", "YearBuilt", "Neighborhood"]

_FIELD_LABELS = {
    "GrLivArea": "above-grade living area (sq ft)",
    "OverallQual": "overall quality rating (1–10)",
    "YearBuilt": "year built",
    "Neighborhood": "neighborhood",
    "TotalBsmtSF": "total basement area (sq ft)",
    "GarageCars": "garage capacity (cars)",
    "FullBath": "full bathrooms above grade",
    "YearRemodAdd": "year last remodelled",
    "Fireplaces": "number of fireplaces",
    "LotArea": "lot area (sq ft)",
    "MasVnrArea": "masonry veneer area (sq ft)",
    "Exterior1st": "primary exterior material",
}


def load_chat_prompt(prompts_dir: Path, version: str) -> str:
    """Load the chat prompt template from disk."""
    prompt_path = prompts_dir / version / "chat.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Chat prompt not found at {prompt_path}. "
            f"Expected: {version}/chat.md in {prompts_dir}/"
        )
    return prompt_path.read_text(encoding="utf-8")


def build_chat_system_prompt(template: str, accumulated_features: dict[str, Any]) -> str:
    """
    Render the chat prompt template with the current known/missing feature context.

    Injects two sections the LLM needs on every turn:
    - {already_known}: features confirmed in previous turns
    - {still_missing}: required fields that are still null
    """
    known = {k: v for k, v in accumulated_features.items() if v is not None}
    missing_required = [f for f in _REQUIRED_FIELDS if known.get(f) is None]

    if known:
        known_lines = "\n".join(
            f"- {_FIELD_LABELS.get(k, k)}: {v}" for k, v in known.items()
        )
    else:
        known_lines = "(none yet)"

    if missing_required:
        missing_lines = "\n".join(
            f"- {_FIELD_LABELS[f]}" for f in missing_required
        )
    else:
        missing_lines = "(none — all required features are known)"

    return template.replace("{already_known}", known_lines).replace("{still_missing}", missing_lines)


def _merge_features(
    accumulated: dict[str, Any],
    new_features: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge newly extracted features into accumulated, ignoring null values."""
    merged = dict(accumulated)
    if new_features:
        for k, v in new_features.items():
            if v is not None:
                merged[k] = _coerce_scalar(v)
    return merged


def _coerce_scalar(value: Any) -> Any:
    """Coerce list/range values from LLM into a single scalar (midpoint)."""
    if isinstance(value, list) and len(value) >= 1:
        if all(isinstance(x, (int, float)) for x in value):
            return round(sum(value) / len(value))
        return value[0]
    return value


def _parse_chat_llm_response(raw: str) -> dict | None:
    """
    Parse and minimally validate the LLM JSON response for a chat turn.

    Returns the parsed dict or None if parsing fails.
    Does not raise — caller handles None with a fallback.
    """
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.warning("Chat LLM response is not valid JSON. raw=%r", raw[:200])
        return None

    if "intent" not in data or "reply" not in data:
        logger.warning("Chat LLM response missing required fields. keys=%s", list(data.keys()))
        return None

    if data["intent"] not in ("chat", "property"):
        logger.warning("Chat LLM returned unknown intent=%r", data["intent"])
        return None

    return data


def _sse_event(event_type: str, payload: dict) -> str:
    """Format a single SSE event string."""
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


async def _stream_text_as_tokens(text: str) -> AsyncIterator[str]:
    """Yield a text string as word-level token SSE events."""
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == 0 else " " + word
        yield _sse_event("token", {"text": chunk})


async def run_chat_turn(
    client: AsyncOpenAI,
    message: str,
    history: list[ChatMessage],
    accumulated_features: dict[str, Any],
    pipeline,
    training_stats: dict,
    chat_prompt_template: str,
    explanation_prompt_template: str,
    prompt_version: str = "v1",
) -> AsyncIterator[str]:
    """
    Execute one chat turn and yield SSE event strings.

    Yields:
      event: reply    → conversational reply or ask-for-missing reply
      event: prediction → {"prediction_usd": ..., "features": ...}
      event: token    → {"text": "<chunk>"} for each explanation token
      event: done     → {}
      event: error    → {"code": "...", "message": "..."}  (terminates stream)
    """
    # 1. Build system prompt with current known/missing context
    system_prompt = build_chat_system_prompt(chat_prompt_template, accumulated_features)

    # 2. Build message list for the LLM (history + new user message)
    llm_messages = [{"role": m.role, "content": m.content} for m in history]
    # Deduplicate: if the client already appended the current message to history, skip it
    if llm_messages and llm_messages[-1]["role"] == "user" and llm_messages[-1]["content"] == message:
        logger.debug("Skipping duplicate user message already present in history")
    else:
        llm_messages.append({"role": "user", "content": message})

    # 3. Call LLM (non-streaming) for intent + extraction — pass full history
    try:
        raw = await chat_completion(
            client,
            system_prompt=system_prompt,
            user_message=message,
            messages=llm_messages,
            json_mode=True,
        )
    except Exception as exc:
        logger.error("Chat LLM call failed: %s", exc, exc_info=True)
        yield _sse_event("error", {
            "code": "LLM_ERROR",
            "message": "I had trouble understanding that — could you rephrase?",
        })
        return

    # 4. Parse response
    parsed = _parse_chat_llm_response(raw)
    if parsed is None:
        # Retry once with more explicit instruction
        logger.warning("Retrying chat LLM call after parse failure.")
        try:
            retry_msg = message + "\n\nIMPORTANT: Respond with ONLY a valid JSON object."
            raw = await chat_completion(
                client,
                system_prompt=system_prompt,
                user_message=retry_msg,
                json_mode=True,
            )
            parsed = _parse_chat_llm_response(raw)
        except Exception as exc:
            logger.error("Chat LLM retry failed: %s", exc, exc_info=True)

        if parsed is None:
            yield _sse_event("error", {
                "code": "PARSE_ERROR",
                "message": "I had trouble understanding that — could you rephrase?",
            })
            return

    intent: str = parsed["intent"]
    reply: str = parsed["reply"]
    extracted: dict | None = parsed.get("extracted_features")


    # 5. Merge extracted features into accumulated
    merged_features = _merge_features(accumulated_features, extracted)

    # 6. Check which required fields are still missing
    missing_required = [f for f in _REQUIRED_FIELDS if merged_features.get(f) is None]

    # 6b. If all required fields are present, validate ranges now — before emitting
    # the features event or streaming the reply. If any field is out of range,
    # remove it from merged_features so the client de-accumulates it, then ask
    # the user to re-enter the corrected value.
    validation_clarification: str | None = None
    if not missing_required:
        try:
            PropertyFeatures(**merged_features)
        except ValidationError as exc:
            bad_fields = [str(e["loc"][0]) for e in exc.errors()]
            for field in bad_fields:
                merged_features.pop(field, None)
            missing_required = [f for f in _REQUIRED_FIELDS if merged_features.get(f) is None]
            field_labels = [_FIELD_LABELS.get(f, f) for f in bad_fields]
            validation_clarification = (
                f"The value{'s' if len(bad_fields) > 1 else ''} you provided for "
                f"{', '.join(field_labels)} "
                f"{'are' if len(bad_fields) > 1 else 'is'} outside the expected range. "
                f"Could you provide {'those' if len(bad_fields) > 1 else 'that'} again?"
            )
            logger.warning(
                "Removed out-of-range fields %s from merged_features — asking user to re-enter",
                bad_fields,
            )

    logger.info(
        "Chat turn — intent=%s, missing_required=%s, extracted_keys=%s, accumulated_keys=%s",
        intent,
        missing_required or "none",
        [k for k, v in (extracted or {}).items() if v is not None],
        list(accumulated_features.keys()),
    )

    # 7. Emit extracted features (metadata only — no display text)
    # Uses merged_features with any invalid fields already removed, so the client
    # de-accumulates out-of-range values instead of keeping them.
    non_null_features = {k: v for k, v in merged_features.items() if v is not None}
    yield _sse_event("features", {"extracted_features": non_null_features})

    # 8. Route based on completeness (intent is a hint, but complete features always predict)
    if missing_required:
        # Stream clarification reply (range error) or LLM reply (genuinely missing fields)
        final_reply = validation_clarification or reply
        async for event in _stream_text_as_tokens(final_reply):
            yield event
        yield _sse_event("done", {})
        return

    # 9. All required features present and ranges validated — stream reply, then predict
    # intent may be "chat" here (e.g. user said "hello?" after providing all features);
    # we predict anyway because the features are complete.
    async for event in _stream_text_as_tokens(reply):
        yield event

    # Validation already ran in step 6b — this should not raise, but guard defensively.
    try:
        features = PropertyFeatures(**merged_features)
    except ValidationError as exc:
        logger.error("PropertyFeatures validation failed unexpectedly in step 9: %s", exc)
        yield _sse_event("error", {
            "code": "VALIDATION_ERROR",
            "message": "I couldn't validate the property details. Could you clarify the values you provided?",
        })
        return

    try:
        price = predict(pipeline, features)
    except Exception as exc:
        logger.error("Prediction failed: %s", exc, exc_info=True)
        yield _sse_event("error", {
            "code": "PREDICTION_ERROR",
            "message": "Something went wrong while estimating the price. Please try again.",
        })
        return

    yield _sse_event("prediction", {
        "prediction_usd": round(price),
        "features": features.model_dump(),
    })

    # Brief yield to let the event loop flush the prediction event
    # before explanation tokens start — helps frontend process prediction
    # as a separate chunk from explanation tokens
    await asyncio.sleep(0)

    # 10. Stream explanation
    explanation_prompt = build_explanation_prompt(
        template=explanation_prompt_template,
        features=features,
        predicted_price=price,
        training_stats=training_stats,
        version=prompt_version,
    )

    try:
        async for chunk in chat_completion_stream(
            client,
            system_prompt=explanation_prompt,
            messages=[{"role": "user", "content": "Please provide the explanation now."}],
            temperature=0.3,
        ):
            yield _sse_event("token", {"text": chunk})
    except Exception as exc:
        logger.error("Explanation streaming failed: %s", exc, exc_info=True)
        yield _sse_event("error", {
            "code": "EXPLANATION_ERROR",
            "message": "Explanation temporarily unavailable.",
        })
        return

    yield _sse_event("done", {})
