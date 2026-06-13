"""Mastery gate — decides whether a turn clears the bar to advance.

The gate combines two signals:
  1. LLM verdict (pass / partial / fail)
  2. Pronunciation threshold extracted from `activity.success_criteria`

Both must pass for `passes_gate()` to return True.

Also defines per-type required consecutive passes before the engine advances:
listen_repeat at L0 requires 2 in a row (spec §9: "across N activities").
All other types require 1.
"""

from __future__ import annotations

import re

from .models import Activity, ActivityType, SimplityLevel, TurnResult, Verdict

# Regex to pull `pronunciation_accuracy >= 0.XX` from success_criteria string
_PRON_RE = re.compile(r"pronunciation_accuracy\s*>=\s*([\d.]+)")


def parse_pron_threshold(success_criteria: str) -> float:
    m = _PRON_RE.search(success_criteria)
    return float(m.group(1)) if m else 0.0


def required_passes(activity: Activity) -> int:
    """How many consecutive passes before the engine advances past this activity."""
    if (
        activity.type == ActivityType.LISTEN_REPEAT
        and activity.simplicity_level in (SimplityLevel.L0, SimplityLevel.L1)
    ):
        return 2
    return 1


def passes_gate(result: TurnResult, activity: Activity) -> bool:
    """True when this turn satisfies the activity's mastery criteria."""
    if result.llm_response.verdict is not Verdict.PASS:
        return False

    threshold = parse_pron_threshold(activity.success_criteria)
    if threshold > 0.0 and result.pronunciation.overall < threshold:
        return False

    return True
