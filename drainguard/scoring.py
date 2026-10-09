"""
Transparent maintenance-priority assessment (prototype).

This is a rule-based score built from observations a field team records.
It is NOT a calibrated flood probability and NOT a proven flood prediction.
Missing observations are kept as missing: they contribute 0 points and are
never silently assumed.
"""

from dataclasses import dataclass, field

OBSTRUCTION_POINTS = {"None": 0, "Partial": 2, "Heavy": 4}
WATER_POINTS = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
RAINFALL_POINTS = {"None": 0, "Light": 1, "Moderate": 2, "Heavy": 3}

HIGH_THRESHOLD = 7
MEDIUM_THRESHOLD = 4


@dataclass
class Factor:
    name: str
    value: str | None
    points: int | None
    max_points: int
    explanation: str


@dataclass
class PriorityResult:
    score: int
    max_score: int
    priority: str
    evidence: str
    factors: list[Factor] = field(default_factory=list)


def _build_factor(name: str, value: str | None, table: dict[str, int]) -> Factor:
    max_points = max(table.values())
    if value is None or value == "":
        return Factor(
            name=name,
            value=None,
            points=None,
            max_points=max_points,
            explanation="Not recorded. Contributes 0 points and is not assumed.",
        )
    if value not in table:
        raise ValueError(f"Invalid value for {name}: {value!r}. Allowed: {list(table)}")
    points = table[value]
    return Factor(
        name=name,
        value=value,
        points=points,
        max_points=max_points,
        explanation=f"Recorded as '{value}', adding {points} of {max_points} points.",
    )


def assess_priority(
    obstruction: str | None = None,
    water_level: str | None = None,
    rainfall: str | None = None,
) -> PriorityResult:
    """Compute a prototype maintenance priority from the recorded observations."""
    factors = [
        _build_factor("Visible obstruction", obstruction, OBSTRUCTION_POINTS),
        _build_factor("Observed water level", water_level, WATER_POINTS),
        _build_factor("Recent rainfall category", rainfall, RAINFALL_POINTS),
    ]

    score = sum(f.points or 0 for f in factors)
    max_score = sum(f.max_points for f in factors)
    recorded = sum(1 for f in factors if f.points is not None)

    if score >= HIGH_THRESHOLD:
        priority = "High"
    elif score >= MEDIUM_THRESHOLD:
        priority = "Medium"
    else:
        priority = "Low"

    if recorded == len(factors):
        evidence = "Complete: all three observations recorded."
    else:
        evidence = (
            f"Partial: {recorded} of {len(factors)} observations recorded. "
            "Priority reflects only the recorded observations."
        )

    return PriorityResult(
        score=score,
        max_score=max_score,
        priority=priority,
        evidence=evidence,
        factors=factors,
    )
