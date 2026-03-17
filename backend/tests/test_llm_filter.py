import pytest
import asyncio
from unittest.mock import MagicMock, patch
from app.engines.analyzer.llm_filter import LLMSemanticFilter

@pytest.mark.asyncio
async def test_llm_filter_tender():
    filter_service = LLMSemanticFilter()
    mock_response = {"is_lead": True, "reason": "项目匹配"}
    
    with patch.object(filter_service.llm, 'extract_structured_data', return_value=mock_response):
        is_lead, reason = await filter_service.filter("充电桩采购项目", "某单位采购50台充电桩")
        assert is_lead is True
        assert reason is None

@pytest.mark.asyncio
async def test_llm_filter_news():
    filter_service = LLMSemanticFilter()
    mock_response = {"is_lead": False, "reason": "行业新闻"}
    
    with patch.object(filter_service.llm, 'extract_structured_data', return_value=mock_response):
        is_lead, reason = await filter_service.filter("充电桩行业2026年发展报告", "根据最新数据，充电桩市场快速增长...")
        assert is_lead is False
        assert reason == "行业新闻"
