import pytest
import asyncio
from app.schemas.constraint import BusinessConstraint
from app.schemas.clue import ClueItem
from app.engines.collector.dispatcher import CollectionDispatcher
from unittest.mock import MagicMock, patch, AsyncMock

@pytest.fixture
def mock_dispatcher():
    dispatcher = CollectionDispatcher()
    
    # Mock search strategy
    dispatcher.general_strategy.collect = AsyncMock(return_value=[
        ClueItem(id="search_1", source="search", title="招标网首页", url="http://example.com/"),
        ClueItem(id="search_2", source="search", title="普通公告", url="http://example.com/notice/1"),
    ])
    # Mock site strategy
    dispatcher.site_strategy.collect = AsyncMock(return_value=[
        ClueItem(id="site_1", source="site", title="站点公告", url="http://test.com/notice/2"),
    ])
    # Mock wechat strategy
    dispatcher.wechat_strategy.collect = AsyncMock(return_value=[
        ClueItem(id="wechat_1", source="wechat", title="公众号推送", url="http://wx.example.com/a"),
    ])
    
    return dispatcher

@pytest.mark.asyncio
async def test_run_all_tasks(mock_dispatcher):
    constraint = BusinessConstraint(
        company_name="测试工程公司",
        core_business=["建筑施工"],
        qualifications=[],
        geography_limits=[],
        financial_thresholds=[],
        other_constraints=[]
    )
    
    config = {
        "target_urls": ["http://test.com"],
        "wechat_accounts": ["招标资讯网"]
    }
    
    results = await mock_dispatcher.run_all_tasks(constraint, config)
    
    assert len(results) == 4
    ids = [c.id for c in results]
    assert "search_1" in ids
    assert "site_1" in ids
    assert "wechat_1" in ids
    
    mock_dispatcher.general_strategy.collect.assert_called_once_with(constraint, search_keywords="")
    called_targets = mock_dispatcher.site_strategy.collect.call_args[0][1]
    assert "http://test.com" in called_targets
    assert "http://example.com/" in called_targets
    assert len(called_targets) == 2
    mock_dispatcher.wechat_strategy.collect.assert_called_once_with(constraint, ["招标资讯网"], search_keywords="")
