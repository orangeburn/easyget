from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # [LLM Services]
    MODEL_API_ENABLED: bool = False
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-4-turbo-preview"

    # [Search API]
    SERPER_API_ENABLED: bool = False
    SEARCH_API_KEY: Optional[str] = None
    TAVILY_API_ENABLED: bool = False
    TAVILY_API_KEY: Optional[str] = None
    
    # [Anti-Crawl Settings]
    WEB_PROXY_URL: Optional[str] = None

    # [Reader]
    READER_PROVIDER: str = "builtin"
    READER_API_KEY: Optional[str] = None
    READER_BASE_URL: Optional[str] = None

    class Config:
        env_file = [".env", ".env.local"]
        extra = "ignore"

settings = Settings()
