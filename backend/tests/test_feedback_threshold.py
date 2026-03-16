from app.engines.analyzer.evaluator import ClueEvaluator


def test_dynamic_threshold_low_samples():
    assert ClueEvaluator._compute_dynamic_threshold(2, 1) == 0


def test_dynamic_threshold_more_negatives():
    assert ClueEvaluator._compute_dynamic_threshold(2, 8) == 72


def test_dynamic_threshold_more_positives():
    assert ClueEvaluator._compute_dynamic_threshold(8, 2) == 48
