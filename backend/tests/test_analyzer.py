import pytest
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint, ConstraintItem
from app.engines.analyzer.evaluator import ClueEvaluator
from unittest.mock import MagicMock, patch

def test_clue_evaluator_pass():
    """测试常规状态下的评估加分"""
    evaluator = ClueEvaluator()
    constraint = BusinessConstraint(
        company_name="理想国际",
        core_business=["建筑工程"],
        geography_limits=[],
    )
    
    clue = ClueItem(
        id="123",
        source="wechat",
        title="建筑工程",
        url="http://test.com/1",
        extracted_metadata={
            "is_matched_core_business": True,
            "required_qualifications": [],
            "location": "广东省广州市"
        }
    )
    
    with patch.object(evaluator, "_get_feedback_counts", return_value=(0, 0)):
        score, veto = evaluator.evaluate(clue, constraint)
    assert score == 100 # business(30) + qual(30) + loc(20) + semantic(20)
    assert veto is None

def test_clue_evaluator_veto():
    """测试触发一票否决"""
    evaluator = ClueEvaluator()
    constraint = BusinessConstraint(
        company_name="理想国际",
        qualifications=[], # 我们没有资质！
        geography_limits=[]
    )
    
    clue = ClueItem(
        id="124",
        source="site",
        title="绝密级开发项目",
        url="http://test.com/2",
        extracted_metadata={
            "is_matched_core_business": True,
            "required_qualifications": ["保密资质二级"],
            "location": "北京"
        }
    )
    
    with patch.object(evaluator, "_get_feedback_counts", return_value=(0, 0)):
        score, veto = evaluator.evaluate(clue, constraint)
    assert score == 0
    assert "保密资质二级" in veto
