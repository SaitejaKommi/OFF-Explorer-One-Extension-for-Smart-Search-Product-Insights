"""
Application configuration and feature flags.
All settings can be overridden via environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # DuckDB
    duckdb_path: str = ":memory:"
    parquet_glob: str = "data/*.parquet"

    # CORS – restrict in production
    cors_origins: list[str] = ["*"]

    # Feature flags
    slm_enabled: bool = False          # Enable Phi-3-mini via Ollama
    slm_model: str = "phi3:mini"       # Ollama model tag
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: float = 30.0       # seconds

    # Search defaults
    default_result_limit: int = 20
    max_relaxation_steps: int = 3

    # Context
    context_max_history: int = 10


settings = Settings()
