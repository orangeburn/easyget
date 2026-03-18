from unittest.mock import patch
from app.services.task_service import TaskService
from app.utils.keywords import build_fallback_expanded_keywords, split_search_keywords

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


def test_split_search_keywords_preserves_phrases():
    keywords = split_search_keywords("广州 智慧医院 软件开发,会议活动策划\n庆典服务")
    assert keywords == ["广州 智慧医院 软件开发", "会议活动策划", "庆典服务"]


def test_fallback_expansion_builds_search_terms():
    keywords = build_fallback_expanded_keywords("会议活动策划,庆典服务")
    assert "会议活动策划" in keywords
    assert "会议活动策划招标" in keywords
    assert "庆典服务采购公告" in keywords
