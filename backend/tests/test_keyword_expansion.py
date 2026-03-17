import pytest
from unittest.mock import MagicMock, patch
from app.services.task_service import TaskService

def test_expand_keywords_via_llm():
    service = TaskService()
    mock_response = ["充电桩招标", "充电站采购"]
    
    with patch.object(service.llm, 'extract_structured_data', return_value=mock_response):
        expanded = service._expand_keywords_via_llm("充电桩")
        assert len(expanded) == 2
        assert "充电桩招标" in expanded
        assert "充电站采购" in expanded

def test_expand_keywords_failure_returns_empty():
    service = TaskService()
    
    with patch.object(service.llm, 'extract_structured_data', side_effect=Exception("API Error")):
        expanded = service._expand_keywords_via_llm("充电桩")
        assert expanded == []
