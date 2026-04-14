from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Environment: "development" uses Ollama, "production" uses Groq
    environment: str = "development"

    # Ollama (development)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi4-mini"
    ollama_timeout: int = 120

    # Groq (production)
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout: int = 120

    # Prompt versioning
    extraction_prompt_version: str = "v1"
    explanation_prompt_version: str = "v1"

    # ML model artifact
    model_path: Path = Path("ml/artifacts/model.joblib")
    training_stats_path: Path = Path("ml/artifacts/training_stats.json")

    # Prompts directory
    prompts_dir: Path = Path("prompts")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def llm_base_url(self) -> str:
        """OpenAI-compatible base URL for the active LLM provider."""
        if self.environment == "production":
            return self.groq_base_url
        return f"{self.ollama_base_url}/v1"

    @property
    def llm_model(self) -> str:
        if self.environment == "production":
            return self.groq_model
        return self.ollama_model

    @property
    def llm_api_key(self) -> str:
        if self.environment == "production":
            return self.groq_api_key
        return "ollama"  # Ollama ignores the key but the SDK requires one

    @property
    def llm_timeout(self) -> int:
        if self.environment == "production":
            return self.groq_timeout
        return self.ollama_timeout

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
