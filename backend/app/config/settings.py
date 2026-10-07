from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    groq_api_key: str
    groq_model: str = "qwen/qwen3.8-27b"
    openalex_email: str = ""
    openalex_api_key: str = ""

    # LangSmith tracing — optional. Blank key = tracing off, zero behavior
    # change (LangChain/LangGraph check LANGSMITH_TRACING before doing any
    # work, so this costs nothing when unset). Free tier at smith.langchain.com.
    langsmith_api_key: str = ""
    langsmith_project: str = "paper-tail"


@lru_cache
def get_settings() -> Settings:
    return Settings()
