from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "amazon_customer_queries"
    qdrant_candidate_limit: int = 20
    max_review_iterations: int = 3
    escalation_confidence: float = 0.45
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://user:password@localhost:5432/amazon_bot"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
