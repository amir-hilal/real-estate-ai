from typing import Any, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: str = "error"
    error_code: str
    message: str


class PredictionResponse(BaseModel):
    status: str = "success"
    predicted_price: float
    features: dict[str, Any]
    explanation: Optional[str] = None


class ExtractionResult(BaseModel):
    """Structured result from the Stage 1 extraction service."""
    is_property_description: bool
    features: Optional[dict[str, Any]] = None
    missing_required: list[str] = []
    message: Optional[str] = None
