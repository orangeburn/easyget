from typing import Optional
from pydantic import BaseModel


class SystemSettingsPayload(BaseModel):
    model_api_enabled: bool = False
    model_api_key: Optional[str] = None
    model_base_url: Optional[str] = None
    model_name: Optional[str] = None

    serper_api_enabled: bool = False
    serper_api_key: Optional[str] = None

    tavily_api_enabled: bool = False
    tavily_api_key: Optional[str] = None


class SystemSettingsResponse(SystemSettingsPayload):
    browser_search_enabled: bool = True


class ProviderTestResult(BaseModel):
    ok: bool
    message: str


class SystemSettingsTestResponse(BaseModel):
    model: ProviderTestResult
    serper: ProviderTestResult
    tavily: ProviderTestResult
    browser: ProviderTestResult
