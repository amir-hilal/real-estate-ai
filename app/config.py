from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    openai_api_key: str
    llm_model: str = "gpt-4o"
    extraction_prompt_version: str = "v1"
    explanation_prompt_version: str = "v1"

    # ML model artifact
    model_path: Path = Path("ml/artifacts/model.joblib")
    training_stats_path: Path = Path("ml/artifacts/training_stats.json")

    # Prompts directory
    prompts_dir: Path = Path("prompts")

    # Server
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
