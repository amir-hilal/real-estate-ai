from typing import Optional
from pydantic import BaseModel, Field


class PropertyFeatures(BaseModel):
    """
    Validated feature set for ML price prediction.

    Required fields (Tier 1): must be present for Stage 2 to run.
    Optional fields (Tier 2): imputed by the preprocessing pipeline if absent.

    Field names match the training dataset exactly — any change requires model retraining.
    """

    # --- Required (Tier 1) ---
    GrLivArea: int = Field(
        ...,
        ge=300,
        le=6000,
        description="Above-grade living area in square feet",
    )
    OverallQual: int = Field(
        ...,
        ge=1,
        le=10,
        description="Overall material and finish quality (1=Very Poor, 10=Very Excellent)",
    )
    YearBuilt: int = Field(
        ...,
        ge=1800,
        le=2025,
        description="Year the house was originally constructed",
    )
    Neighborhood: str = Field(
        ...,
        description=(
            "Physical location within Ames city limits. "
            "Valid values: Blmngtn, Blueste, BrDale, BrkSide, ClearCr, CollgCr, "
            "Crawfor, Edwards, Gilbert, IDOTRR, MeadowV, Mitchel, NAmes, NoRidge, "
            "NPkVill, NridgHt, NWAmes, OldTown, SWISU, Sawyer, SawyerW, Somerst, "
            "StoneBr, Timber, Veenker"
        ),
    )

    # --- Optional (Tier 2) — imputed by pipeline if None ---
    TotalBsmtSF: Optional[int] = Field(
        default=None,
        ge=0,
        le=6000,
        description="Total square feet of basement area (0 if no basement)",
    )
    GarageCars: Optional[int] = Field(
        default=None,
        ge=0,
        le=5,
        description="Size of garage in car capacity (0 if no garage)",
    )
    FullBath: Optional[int] = Field(
        default=None,
        ge=0,
        le=5,
        description="Number of full bathrooms above grade",
    )
    YearRemodAdd: Optional[int] = Field(
        default=None,
        ge=1800,
        le=2025,
        description="Remodel year (same as YearBuilt if no remodeling)",
    )
    Fireplaces: Optional[int] = Field(
        default=None,
        ge=0,
        le=5,
        description="Number of fireplaces",
    )
    LotArea: Optional[int] = Field(
        default=None,
        ge=1000,
        le=200000,
        description="Lot size in square feet",
    )
    MasVnrArea: Optional[float] = Field(
        default=None,
        ge=0,
        le=2000,
        description="Masonry veneer area in square feet (0 if none)",
    )
    Exterior1st: Optional[str] = Field(
        default=None,
        description=(
            "Exterior covering on house. "
            "Valid values: VinylSd, HdBoard, MetalSd, Wd Sdng, Plywood, CemntBd, "
            "BrkFace, WdShing, Stucco, AsbShng, Other"
        ),
    )
