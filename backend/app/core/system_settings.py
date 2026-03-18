from typing import Dict, Any
import asyncio
import httpx
from openai import OpenAI
from app.core.database import SessionLocal, SystemSettingsModel
from app.core.config import settings


DEFAULT_MODEL_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL_NAME = "gpt-4-turbo-preview"


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ensure_row(db) -> SystemSettingsModel:
    model = db.query(SystemSettingsModel).first()
    if not model:
        model = SystemSettingsModel()
        db.add(model)
        db.commit()
        db.refresh(model)
    return model


def _apply_to_runtime(model: SystemSettingsModel) -> None:
    settings.MODEL_API_ENABLED = bool(model.model_api_enabled)
    settings.OPENAI_API_KEY = _normalize_text(model.model_api_key) if settings.MODEL_API_ENABLED else None
    settings.OPENAI_BASE_URL = _normalize_text(model.model_base_url) or DEFAULT_MODEL_BASE_URL
    settings.MODEL_NAME = _normalize_text(model.model_name) or DEFAULT_MODEL_NAME

    settings.SERPER_API_ENABLED = bool(model.serper_api_enabled)
    settings.SEARCH_API_KEY = _normalize_text(model.serper_api_key) if settings.SERPER_API_ENABLED else None

    settings.TAVILY_API_ENABLED = bool(model.tavily_api_enabled)
    settings.TAVILY_API_KEY = _normalize_text(model.tavily_api_key) if settings.TAVILY_API_ENABLED else None


def load_system_settings() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        model = _ensure_row(db)
        _apply_to_runtime(model)
        return serialize_system_settings(model)
    finally:
        db.close()


def serialize_system_settings(model: SystemSettingsModel) -> Dict[str, Any]:
    return {
        "model_api_enabled": bool(model.model_api_enabled),
        "model_api_key": model.model_api_key or "",
        "model_base_url": model.model_base_url or DEFAULT_MODEL_BASE_URL,
        "model_name": model.model_name or DEFAULT_MODEL_NAME,
        "serper_api_enabled": bool(model.serper_api_enabled),
        "serper_api_key": model.serper_api_key or "",
        "tavily_api_enabled": bool(model.tavily_api_enabled),
        "tavily_api_key": model.tavily_api_key or "",
        "browser_search_enabled": True
    }


def update_system_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        model = _ensure_row(db)
        model.model_api_enabled = bool(payload.get("model_api_enabled", False))
        model.model_api_key = _normalize_text(payload.get("model_api_key"))
        model.model_base_url = _normalize_text(payload.get("model_base_url")) or DEFAULT_MODEL_BASE_URL
        model.model_name = _normalize_text(payload.get("model_name")) or DEFAULT_MODEL_NAME
        model.serper_api_enabled = bool(payload.get("serper_api_enabled", False))
        model.serper_api_key = _normalize_text(payload.get("serper_api_key"))
        model.tavily_api_enabled = bool(payload.get("tavily_api_enabled", False))
        model.tavily_api_key = _normalize_text(payload.get("tavily_api_key"))
        db.commit()
        db.refresh(model)
        _apply_to_runtime(model)
        return serialize_system_settings(model)
    finally:
        db.close()


def _mask_error_message(err: Exception) -> str:
    msg = str(err) if err else "未知错误"
    return msg[:200]


def _model_test_params(base_url: str, model_name: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "model": model_name,
        "temperature": 0.0,
        "max_tokens": 1
    }
    if base_url and "minimax" in base_url.lower():
        params["extra_body"] = {"reasoning_split": True}
    return params


def _test_model_sync(api_key: str, base_url: str, model_name: str) -> Dict[str, Any]:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=12.0)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "ping"}],
            **_model_test_params(base_url, model_name)
        )
        if response and response.choices:
            return {"ok": True, "message": "模型连接正常"}
        return {"ok": False, "message": "模型响应异常"}
    except Exception as e:
        return {"ok": False, "message": f"模型连接失败: {_mask_error_message(e)}"}


async def test_system_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    # Model
    if payload.get("model_api_enabled"):
        api_key = _normalize_text(payload.get("model_api_key"))
        base_url = _normalize_text(payload.get("model_base_url")) or DEFAULT_MODEL_BASE_URL
        model_name = _normalize_text(payload.get("model_name")) or DEFAULT_MODEL_NAME
        if not api_key:
            results["model"] = {"ok": False, "message": "模型 API Key 为空"}
        else:
            results["model"] = await asyncio.to_thread(_test_model_sync, api_key, base_url, model_name)
    else:
        results["model"] = {"ok": True, "message": "未启用"}

    # Serper
    if payload.get("serper_api_enabled"):
        api_key = _normalize_text(payload.get("serper_api_key"))
        if not api_key:
            results["serper"] = {"ok": False, "message": "Serper API Key 为空"}
        else:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                        json={"q": "test", "gl": "cn", "hl": "zh-cn", "autocorrect": True}
                    )
                    resp.raise_for_status()
                results["serper"] = {"ok": True, "message": "Serper 连接正常"}
            except Exception as e:
                results["serper"] = {"ok": False, "message": f"Serper 连接失败: {_mask_error_message(e)}"}
    else:
        results["serper"] = {"ok": True, "message": "未启用"}

    # Tavily
    if payload.get("tavily_api_enabled"):
        api_key = _normalize_text(payload.get("tavily_api_key"))
        if not api_key:
            results["tavily"] = {"ok": False, "message": "Tavily API Key 为空"}
        else:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": api_key,
                            "query": "test",
                            "search_depth": "basic",
                            "include_answer": False,
                            "include_images": False,
                            "max_results": 1
                        }
                    )
                    resp.raise_for_status()
                results["tavily"] = {"ok": True, "message": "Tavily 连接正常"}
            except Exception as e:
                results["tavily"] = {"ok": False, "message": f"Tavily 连接失败: {_mask_error_message(e)}"}
    else:
        results["tavily"] = {"ok": True, "message": "未启用"}

    results["browser"] = {"ok": True, "message": "本地搜索默认开启"}
    return results
