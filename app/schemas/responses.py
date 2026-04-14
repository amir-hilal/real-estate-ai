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
