from typing import Any, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: str = "error"
    error_code: str
    message: str


class ExtractionResult(BaseModel):
    """Structured result from the Stage 1 extraction service (internal use)."""
    is_property_description: bool
    features: Optional[dict[str, Any]] = None
    missing_required: list[str] = []
    message: Optional[str] = None


# --- Route-level response models ---

class ExtractResponse(BaseModel):
    """Response shape for POST /extract."""
    status: str  # "complete" | "partial" | "error" | "not_a_property"
    features: Optional[dict[str, Any]] = None
    missing_required_fields: list[str] = []
    message: Optional[str] = None


class PredictResponse(BaseModel):
    """Response shape for POST /predict (full pipeline)."""
    status: str  # "complete" | "incomplete"
    features: Optional[dict[str, Any]] = None
    missing_required_fields: list[str] = []
    prediction_usd: Optional[int] = None
    explanation: Optional[str] = None
    message: Optional[str] = None
