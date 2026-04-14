"""
Stage 3: LLM explanation generation.

Receives a validated PropertyFeatures instance and a predicted price,
then generates a grounded 2–4 paragraph plain-English explanation.

The explanation is grounded exclusively in statistics from
ml/artifacts/training_stats.json — the LLM is prohibited from
inventing statistics by explicit prompt instructions.
"""

import logging
from pathlib import Path

from openai import AsyncOpenAI

from app.clients.llm import chat_completion
from app.config import settings
from app.schemas.property_features import PropertyFeatures

logger = logging.getLogger(__name__)


class ExplanationError(Exception):
    """Raised when the explanation service cannot produce a valid response."""


def load_explanation_prompt(prompts_dir: Path, version: str) -> str:
    """Load the explanation prompt template from disk."""
    prompt_path = prompts_dir / f"explanation_{version}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Explanation prompt not found at {prompt_path}. "
            f"Expected file: explanation_{version}.md in {prompts_dir}/"
        )
    return prompt_path.read_text(encoding="utf-8")


def build_explanation_prompt(
    template: str,
    features: PropertyFeatures,
    predicted_price: float,
    training_stats: dict,
) -> str:
    """
    Render the explanation prompt template with real data.

    Injects:
    - Training statistics (median, percentiles, neighborhood median, top features)
    - Property characteristics (non-null fields only, in plain English)
    - Predicted price
    - Price bracket instruction (premium/discount/average contextualisation)
    """
    # --- Neighborhood context line (only if neighborhood provided) ---
    neighborhood = features.Neighborhood
    nbhd_medians = training_stats.get("neighborhood_median_price", {})
    if neighborhood and neighborhood in nbhd_medians:
        nbhd_median = nbhd_medians[neighborhood]
        neighborhood_stat_line = (
            f"- Median sale price in the {neighborhood} neighborhood: ${nbhd_median:,}"
        )
    else:
        neighborhood_stat_line = ""

    # --- Top factors (top 3, human-readable) ---
    top_features = training_stats.get("top_features", [])
    top_factors_list = ", ".join(top_features[:3]) if top_features else "overall quality, living area, location"

    # --- Property lines (non-null fields only) ---
    property_lines = _format_property_lines(features)

    # --- Price bracket instruction ---
    p25 = training_stats["price_25th_percentile"]
    p75 = training_stats["price_75th_percentile"]
    if predicted_price > p75:
        bracket_instruction = (
            "The estimate is above the 75th percentile for this market. "
            "Acknowledge the premium factors that justify this higher price."
        )
    elif predicted_price < p25:
        bracket_instruction = (
            "The estimate is below the 25th percentile for this market. "
            "Acknowledge the limiting factors that contribute to this lower price."
        )
    else:
        bracket_instruction = (
            "The estimate is near the median for this market. "
            "Use the overall median as the primary comparison anchor."
        )

    return template.format(
        training_sample_size=training_stats["training_sample_size"],
        median_sale_price=training_stats["median_sale_price"],
        price_25th_percentile=p25,
        price_75th_percentile=p75,
        median_price_per_sqft=training_stats["median_price_per_sqft"],
        neighborhood_stat_line=neighborhood_stat_line,
        top_factors_list=top_factors_list,
        property_lines=property_lines,
        predicted_price=predicted_price,
        price_bracket_instruction=bracket_instruction,
    )


def _format_property_lines(features: PropertyFeatures) -> str:
    """
    Format non-null PropertyFeatures fields as plain-English lines.

    Null optional fields are omitted — per Phase 4 rules the LLM must
    not mention features that were absent from the description.
    """
    labels = {
        "GrLivArea": ("Above-grade living area", "{v:,} sq ft"),
        "OverallQual": ("Overall quality rating", "{v}/10"),
        "YearBuilt": ("Year built", "{v}"),
        "Neighborhood": ("Neighborhood", "{v}"),
        "TotalBsmtSF": ("Total basement area", "{v:,} sq ft"),
        "GarageCars": ("Garage capacity", "{v} car(s)"),
        "FullBath": ("Full bathrooms above grade", "{v}"),
        "YearRemodAdd": ("Year last remodeled", "{v}"),
        "Fireplaces": ("Fireplaces", "{v}"),
        "LotArea": ("Lot area", "{v:,} sq ft"),
        "MasVnrArea": ("Masonry veneer area", "{v:,} sq ft"),
        "Exterior1st": ("Primary exterior material", "{v}"),
    }
    data = features.model_dump()
    lines = []
    for field, (label, fmt) in labels.items():
        val = data.get(field)
        if val is not None:
            lines.append(f"- {label}: {fmt.format(v=val)}")
    return "\n".join(lines) if lines else "- No specific details provided."


async def generate_explanation(
    client: AsyncOpenAI,
    features: PropertyFeatures,
    predicted_price: float,
    training_stats: dict,
    prompt_template: str,
) -> str:
    """
    Run Stage 3: generate a plain-English explanation of the predicted price.

    Returns the explanation text on success.
    Raises ExplanationError if the LLM call fails or returns an empty response.

    The LLM call uses temperature=0.3 (slight creativity for natural prose,
    still deterministic enough for testing).
    """
    system_prompt = build_explanation_prompt(
        template=prompt_template,
        features=features,
        predicted_price=predicted_price,
        training_stats=training_stats,
    )

    try:
        explanation = await chat_completion(
            client,
            system_prompt=system_prompt,
            user_message="Please provide the explanation now.",
            temperature=0.3,
            json_mode=False,
        )
    except Exception as exc:
        raise ExplanationError(
            f"LLM call failed during explanation generation: {exc}"
        ) from exc

    explanation = explanation.strip()
    if not explanation:
        raise ExplanationError("LLM returned an empty explanation.")

    logger.info(
        "Explanation generated — length=%d chars, predicted_price=$%.0f",
        len(explanation),
        predicted_price,
    )
    return explanation
