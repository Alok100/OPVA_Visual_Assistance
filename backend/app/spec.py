"""Deterministic requirement interpretation for the Microtask 2 POC.

This is intentionally NOT a general-purpose NL planner (see CLAUDE.md /
Microtask 2 instructions). It recognizes one known requirement shape — bolt
detection, counting, and a per-bolt color-marking check — via keyword
matching, and returns a structured InspectionSpec plus an honest feasibility
assessment. Anything that doesn't match is reported as needs_info rather than
silently guessed at. Real LLM-based interpretation is Microtask 2+ later work
(see docs/ROADMAP.md).
"""

from __future__ import annotations

import re

from .models import (
    CheckOperation,
    FeasibilityLevel,
    FeasibilityResult,
    InspectionCheck,
    InspectionSpec,
)

_BOLT_PATTERN = re.compile(r"\bbolts?\b", re.IGNORECASE)
_COUNT_PATTERN = re.compile(r"\bcount(ing)?\b", re.IGNORECASE)
_MARK_PATTERN = re.compile(r"\b(line|mark(ing)?|stripe)\b", re.IGNORECASE)
_COLOR_PATTERN = re.compile(
    r"\b(yellow|blue|red|green|white|black|orange)\b", re.IGNORECASE
)


def interpret_requirement(requirement_text: str) -> InspectionSpec:
    """Build a deterministic InspectionSpec for the known bolt/marking request.

    Returns a spec with feasibility=NOT_FEASIBLE (empty checks) when the text
    doesn't match the one supported pattern, instead of fabricating checks.
    """
    text = requirement_text.strip()
    has_bolt = bool(_BOLT_PATTERN.search(text))
    has_mark = bool(_MARK_PATTERN.search(text))
    color_match = _COLOR_PATTERN.search(text)

    if not has_bolt:
        return InspectionSpec(
            requirement_text=requirement_text,
            target_object="unknown",
            checks=[],
            feasibility=FeasibilityResult(
                level=FeasibilityLevel.NOT_FEASIBLE,
                reasons=[
                    "This POC's deterministic interpreter only recognizes bolt-"
                    "inspection requirements (detect, count, check a color "
                    "marking). The requirement text doesn't mention a bolt."
                ],
                limitations=[
                    "No general-purpose requirement interpretation exists yet "
                    "— see docs/ROADMAP.md Microtask 2 (LLM-based interpretation)."
                ],
                missing_information=["A requirement describing a bolt to detect."],
            ),
        )

    checks = [
        InspectionCheck(
            id="check-detect",
            title="Bolt detection",
            operation=CheckOperation.DETECT,
            method="Pretrained object detector (feasibility verified empirically, not assumed)",
        ),
        InspectionCheck(
            id="check-count",
            title="Bolt counting",
            operation=CheckOperation.COUNT,
            method="Count of detections above the confidence threshold",
            applies_to="check-detect",
        ),
    ]

    reasons = [
        "Requirement mentions bolts; deterministic bolt-detection pattern matched."
    ]
    limitations = [
        "Standard pretrained object detectors (COCO-80 classes) have no 'bolt' "
        "class — detection feasibility on this dataset must be verified "
        "empirically before this check can be trusted; see the Step 4 report.",
    ]
    missing_information: list[str] = []
    level = FeasibilityLevel.NEEDS_INFO

    color = color_match.group(1).lower() if color_match else None
    if has_mark and color:
        checks.append(
            InspectionCheck(
                id="check-marking",
                title=f"{color.capitalize()} marking verification",
                operation=CheckOperation.COLOR_MARK_CHECK,
                method=(
                    f"HSV color-threshold check for {color} paint within each "
                    "detected bolt's region (OpenCV, configurable thresholds)"
                ),
                applies_to="check-detect",
            )
        )
        reasons.append(
            f"Requirement mentions a '{color}' marking/line to verify per bolt."
        )
        limitations.append(
            "Color thresholding is sensitive to lighting and to other "
            f"{color}-colored objects (e.g. cable insulation) appearing in the "
            "same crop region — results below are flagged REVIEW, not FAIL, "
            "when evidence is weak."
        )
    elif has_mark and not color:
        missing_information.append(
            "Which color the expected marking/line should be."
        )
    else:
        missing_information.append(
            "No marking/line check was requested — only detection and counting "
            "will run."
        )

    return InspectionSpec(
        requirement_text=requirement_text,
        target_object="bolt",
        checks=checks,
        feasibility=FeasibilityResult(
            level=level,
            reasons=reasons,
            limitations=limitations,
            missing_information=missing_information,
        ),
    )
