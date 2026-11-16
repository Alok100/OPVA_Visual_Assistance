import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import FeasibilityLevel, CheckOperation
from app.spec import interpret_requirement


def test_bolt_and_yellow_marking_produces_three_checks():
    spec = interpret_requirement(
        "Detect every bolt and verify whether each bolt has the expected yellow line marking."
    )
    assert spec.target_object == "bolt"
    ops = [c.operation for c in spec.checks]
    assert ops == [
        CheckOperation.DETECT,
        CheckOperation.COUNT,
        CheckOperation.COLOR_MARK_CHECK,
    ]
    assert spec.feasibility.level == FeasibilityLevel.NEEDS_INFO
    assert spec.checks[2].method.lower().startswith("hsv color-threshold check for yellow")


def test_non_bolt_requirement_is_not_feasible():
    spec = interpret_requirement("Inspect the surface for scratches.")
    assert spec.feasibility.level == FeasibilityLevel.NOT_FEASIBLE
    assert spec.checks == []


def test_bolt_without_marking_mention_skips_color_check():
    spec = interpret_requirement("Detect and count every bolt.")
    assert len(spec.checks) == 2
    assert any("no marking" in m.lower() for m in spec.feasibility.missing_information)


def test_mark_without_color_flags_missing_information():
    spec = interpret_requirement("Detect every bolt and check for a marking.")
    assert len(spec.checks) == 2
    assert any("color" in m.lower() for m in spec.feasibility.missing_information)
