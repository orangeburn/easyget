from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # [LLM Services]
    OPENAI_API_KEY: str = "sk-..."
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-4-turbo-preview"

    # [Search API]
    SEARCH_API_KEY: Optional[str] = None
    
    # [Anti-Crawl Settings]
    WEB_PROXY_URL: Optional[str] = None

    class Config:
        env_file = [".env", ".env.local"]
        extra = "ignore"

settings = Settings()
