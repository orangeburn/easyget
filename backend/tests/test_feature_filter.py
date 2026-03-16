from app.engines.analyzer.feature_filter import StructuralFeatureScorer


def test_feature_scorer_high_score():
    scorer = StructuralFeatureScorer(min_score=25)
    title = "某市政道路改造工程招标公告"
    snippet = "项目编号：ABC-123 预算：500万元 截止：2026-03-20"
    score, reason = scorer.score(title=title, snippet=snippet, full_text="")
    assert score >= 25
    assert reason is None


def test_feature_scorer_low_score():
    scorer = StructuralFeatureScorer(min_score=25)
    title = "行业资讯速递"
    snippet = "本周市场动态与政策解读"
    score, reason = scorer.score(title=title, snippet=snippet, full_text="")
    assert score < 25 or reason is not None
