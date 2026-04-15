"""
LLM client factory.

Creates an AsyncOpenAI client configured for the active environment.
Both Ollama (dev) and Groq (prod) expose OpenAI-compatible APIs,
so the same client works for both — only base_url and api_key differ.
"""

import logging
import time

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def create_llm_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client using environment-determined settings."""
    client = AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=float(settings.llm_timeout),
    )
    logger.info(
        "LLM client created — provider=%s, model=%s, base_url=%s",
        settings.environment,
        settings.llm_model,
        settings.llm_base_url,
    )
    return client


async def chat_completion(
    client: AsyncOpenAI,
    system_prompt: str,
    user_message: str,
    *,
    messages: list[dict] | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> str:
    """
    Send a chat completion request and return the response content.

    If `messages` is provided it is used as the full message list (system
    prompt still prepended). Otherwise a single user turn is constructed
    from `user_message`.

    Logs model, latency, and status. Does NOT log prompt content
    (may contain user data).
    """
    model = model or settings.llm_model
    full_messages = [{"role": "system", "content": system_prompt}]
    if messages is not None:
        full_messages.extend(messages)
    else:
        full_messages.append({"role": "user", "content": user_message})
    kwargs: dict = {
        "model": model,
        "messages": full_messages,
        "temperature": temperature,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    start = time.monotonic()
    try:
        response = await client.chat.completions.create(**kwargs)
        elapsed = time.monotonic() - start
        content = response.choices[0].message.content or ""
        logger.info(
            "LLM call — model=%s, latency=%.2fs, status=success, response_len=%d",
            model,
            elapsed,
            len(content),
        )
        return content
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "LLM call — model=%s, latency=%.2fs, status=error",
            model,
            elapsed,
            exc_info=True,
        )
        raise


async def chat_completion_stream(
    client: AsyncOpenAI,
    system_prompt: str,
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.7,
):
    """
    Send a streaming chat completion request.

    Yields text chunks as they arrive from the LLM.
    `messages` is a list of {"role": ..., "content": ...} dicts;
    the system prompt is prepended automatically.
    """
    model = model or settings.llm_model
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    start = time.monotonic()
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
        elapsed = time.monotonic() - start
        logger.info(
            "LLM stream call — model=%s, latency=%.2fs, status=success",
            model,
            elapsed,
        )
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(
            "LLM stream call — model=%s, latency=%.2fs, status=error",
            model,
            elapsed,
            exc_info=True,
        )
        raise
