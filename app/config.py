import re
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
    prompt_version: str = "latest"

    # ML model artifact
    model_path: Path = Path("ml/artifacts/model.joblib")
    training_stats_path: Path = Path("ml/artifacts/training_stats.json")

    # Prompts directory
    prompts_dir: Path = Path("prompts")
    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS — frontend origin(s) allowed to call the API
    cors_origin: str = "http://localhost:5173"

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

_VERSION_PATTERN = re.compile(r"^v(\d+)$")


def resolve_prompt_version(version: str | None = None) -> str:
    """
    Resolve a prompt version string to a concrete version directory name.

    - ``None`` or ``"latest"`` → highest ``vN/`` directory in ``prompts_dir``
      that contains both ``chat.md`` and ``explanation.md``.
    - Any other string (e.g. ``"v2"``) → returned as-is.
    """
    if version and version != "latest":
        return version

    best: int = 0
    for path in settings.prompts_dir.iterdir():
        if path.is_dir():
            m = _VERSION_PATTERN.match(path.name)
            if m and (path / "chat.md").exists() and (path / "explanation.md").exists():
                n = int(m.group(1))
                if n > best:
                    best = n

    if best == 0:
        raise FileNotFoundError("No valid prompt version directories found in prompts/")
    return f"v{best}"
