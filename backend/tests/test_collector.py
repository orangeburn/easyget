import pytest
import asyncio
from app.schemas.constraint import BusinessConstraint
from app.engines.collector.dispatcher import CollectionDispatcher
from unittest.mock import MagicMock, patch, AsyncMock

@pytest.fixture
def mock_dispatcher():
    dispatcher = CollectionDispatcher()
    
    # Mock search strategy
    dispatcher.general_strategy.collect = AsyncMock(return_value=["mocked_search_1", "mocked_search_2"])
    # Mock site strategy
    dispatcher.site_strategy.collect = AsyncMock(return_value=["mocked_site_1"])
    # Mock wechat strategy
    dispatcher.wechat_strategy.collect = AsyncMock(return_value=["mocked_wechat_1"])
    
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
    assert "mocked_search_1" in results
    assert "mocked_site_1" in results
    assert "mocked_wechat_1" in results
    
    mock_dispatcher.general_strategy.collect.assert_called_once_with(constraint)
    mock_dispatcher.site_strategy.collect.assert_called_once_with(constraint, ["http://test.com"])
    mock_dispatcher.wechat_strategy.collect.assert_called_once_with(constraint, ["招标资讯网"])
