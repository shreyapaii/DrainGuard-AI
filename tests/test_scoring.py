import pytest

from drainguard.scoring import assess_priority


def test_all_heavy_observations_give_high_priority():
    result = assess_priority(obstruction="Heavy", water_level="High", rainfall="Heavy")
    assert result.score == 10
    assert result.max_score == 10
    assert result.priority == "High"
    assert result.evidence.startswith("Complete")


def test_missing_observations_contribute_zero_and_are_not_assumed():
    result = assess_priority(obstruction="Partial", water_level=None, rainfall=None)
    assert result.score == 2
    missing = [f for f in result.factors if f.value is None]
    assert len(missing) == 2
    assert all(f.points is None for f in missing)
    assert result.evidence.startswith("Partial")


def test_all_missing_is_low_priority_with_no_invented_points():
    result = assess_priority()
    assert result.score == 0
    assert result.priority == "Low"


def test_medium_band():
    result = assess_priority(obstruction="Partial", water_level="Medium", rainfall="Light")
    assert result.score == 5
    assert result.priority == "Medium"


def test_invalid_value_raises():
    with pytest.raises(ValueError):
        assess_priority(obstruction="Enormous")
