"""
Pydantic schemas for POST /chat request body.

Conversation history and accumulated features are client-managed state —
the /chat endpoint is stateless on the server.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)
    accumulated_features: dict[str, Any] = Field(default_factory=dict)
    prompt_version: str | None = Field(
        default=None,
        description="Chat prompt version to use (e.g. 'v1', 'v2', 'v3'). Defaults to server config.",
    )
