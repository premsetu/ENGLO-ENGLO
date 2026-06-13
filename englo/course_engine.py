from __future__ import annotations

import json
from pathlib import Path

from .models import Activity, LessonFile, NextStep, TurnResult, Verdict

_CURRICULUM_DIR = Path(__file__).parent / "curriculum"

# A learner repeats a failed activity up to this many times before the
# engine moves on anyway (avoids a frustration loop at the same prompt).
MAX_ATTEMPTS = 3


def load_curriculum(curriculum_dir: Path | None = None) -> list[LessonFile]:
    """Load every lesson JSON in the curriculum dir, sorted by filename."""
    directory = curriculum_dir or _CURRICULUM_DIR
    lessons = []
    for path in sorted(directory.glob("*.json")):
        lessons.append(LessonFile(**json.loads(path.read_text())))
    return lessons


class CourseEngine:
    """Deterministic sequencer: holds position in the curriculum and decides
    repeat / next-activity / next-lesson from each turn's verdict.

    The LLM never drives this — it only grades the turn (§5 of the spec).
    """

    def __init__(self, lessons: list[LessonFile] | None = None):
        self.lessons = lessons if lessons is not None else load_curriculum()
        if not self.lessons:
            raise ValueError("Curriculum is empty — no lesson files found")
        self.lesson_idx = 0
        self.activity_idx = 0
        self.attempts = 0

    @property
    def current_lesson_file(self) -> LessonFile:
        return self.lessons[self.lesson_idx]

    @property
    def current_activity(self) -> Activity:
        return self.current_lesson_file.lesson.activities[self.activity_idx]

    @property
    def is_complete(self) -> bool:
        return self.lesson_idx >= len(self.lessons)

    def record_turn(self, result: TurnResult) -> NextStep:
        """Advance (or hold) position based on the turn's verdict.

        pass            → next activity
        partial / fail  → repeat, up to MAX_ATTEMPTS, then move on
        """
        self.attempts += 1
        verdict = result.llm_response.verdict

        if verdict is not Verdict.PASS and self.attempts < MAX_ATTEMPTS:
            return NextStep.REPEAT

        self.attempts = 0
        self.activity_idx += 1

        if self.activity_idx < len(self.current_lesson_file.lesson.activities):
            return NextStep.NEXT_ACTIVITY

        self.activity_idx = 0
        self.lesson_idx += 1

        if self.lesson_idx < len(self.lessons):
            return NextStep.NEXT_LESSON
        return NextStep.COURSE_COMPLETE

    def position(self) -> dict:
        """Serializable cursor — used by the progress tracker to resume."""
        return {
            "lesson_idx": self.lesson_idx,
            "activity_idx": self.activity_idx,
            "attempts": self.attempts,
        }

    def restore(self, position: dict) -> None:
        self.lesson_idx = position.get("lesson_idx", 0)
        self.activity_idx = position.get("activity_idx", 0)
        self.attempts = position.get("attempts", 0)
