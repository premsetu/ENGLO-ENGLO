from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from . import mastery
from .models import Activity, LessonFile, NextStep, TurnResult

if TYPE_CHECKING:
    from .progress import ProgressTracker

_CURRICULUM_DIR = Path(__file__).parent / "curriculum"


def load_curriculum(curriculum_dir: Path | None = None) -> list[LessonFile]:
    directory = curriculum_dir or _CURRICULUM_DIR
    return [
        LessonFile(**json.loads(p.read_text()))
        for p in sorted(directory.glob("*.json"))
    ]


class CourseEngine:
    """Deterministic sequencer — the LLM grades, this decides what comes next.

    Mastery gating (spec §9):
      - An activity is cleared when `consecutive_passes` reaches
        `mastery.required_passes(activity)`.
      - A pass requires BOTH verdict=pass AND pron.overall >= threshold from
        `success_criteria`.
      - Below that bar: repeat (up to MAX_HARD_ATTEMPTS), then advance anyway
        to avoid a frustration loop.

    SRS / error-drill injection:
      - Call `pop_pending_drill(tracker)` before each activity.  If non-None,
        run that drill first.  The curriculum cursor does not advance until the
        pending drill queue is empty.
    """

    MAX_HARD_ATTEMPTS = 4  # absolute ceiling before forced advance

    def __init__(self, lessons: list[LessonFile] | None = None):
        self.lessons = lessons if lessons is not None else load_curriculum()
        if not self.lessons:
            raise ValueError("Curriculum is empty — no lesson files found")
        self.lesson_idx = 0
        self.activity_idx = 0
        self._attempts = 0
        self._consecutive_passes = 0

    # ── current position ─────────────────────────────────────────────────────

    @property
    def current_lesson_file(self) -> LessonFile:
        return self.lessons[self.lesson_idx]

    @property
    def current_activity(self) -> Activity:
        return self.current_lesson_file.lesson.activities[self.activity_idx]

    @property
    def is_complete(self) -> bool:
        return self.lesson_idx >= len(self.lessons)

    # ── drill injection ───────────────────────────────────────────────────────

    def pop_pending_drill(self, tracker: ProgressTracker) -> Activity | None:
        """Return (and consume) the next pending SRS/error drill, or None."""
        hindi = self.current_activity.hindi_support if not self.is_complete else 0.5
        drills = tracker.get_pending_drills(hindi_support=hindi)
        return drills[0] if drills else None

    # ── turn recording ────────────────────────────────────────────────────────

    def record_turn(self, result: TurnResult) -> NextStep:
        """Advance (or hold) based on mastery gate + attempt ceiling."""
        activity = self.current_activity
        self._attempts += 1
        req = mastery.required_passes(activity)

        if mastery.passes_gate(result, activity):
            self._consecutive_passes += 1
        else:
            self._consecutive_passes = 0

        # Advance when mastery is confirmed OR the hard-attempt ceiling is hit
        cleared = (
            self._consecutive_passes >= req
            or self._attempts >= self.MAX_HARD_ATTEMPTS
        )

        if not cleared:
            return NextStep.REPEAT

        self._attempts = 0
        self._consecutive_passes = 0
        self.activity_idx += 1

        if self.activity_idx < len(self.current_lesson_file.lesson.activities):
            return NextStep.NEXT_ACTIVITY

        self.activity_idx = 0
        self.lesson_idx += 1
        return NextStep.NEXT_LESSON if self.lesson_idx < len(self.lessons) else NextStep.COURSE_COMPLETE

    # ── persistence ───────────────────────────────────────────────────────────

    def position(self) -> dict:
        return {
            "lesson_idx": self.lesson_idx,
            "activity_idx": self.activity_idx,
            "attempts": self._attempts,
            "consecutive_passes": self._consecutive_passes,
        }

    def restore(self, position: dict) -> None:
        self.lesson_idx = position.get("lesson_idx", 0)
        self.activity_idx = position.get("activity_idx", 0)
        self._attempts = position.get("attempts", 0)
        self._consecutive_passes = position.get("consecutive_passes", 0)
