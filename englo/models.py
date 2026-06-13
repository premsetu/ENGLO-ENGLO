from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel


class ActivityType(str, Enum):
    LISTEN_REPEAT = "listen_repeat"
    TRANSLATE_SAY = "translate_say"
    PROMPT_RESPOND = "prompt_respond"
    ROLEPLAY = "roleplay"
    FREE_CONVERSATION = "free_conversation"
    RECALL_DRILL = "recall_drill"


class SimplityLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class Activity(BaseModel):
    id: str
    type: ActivityType
    target_text: str
    hindi_scaffold: str
    expected_pattern: str
    success_criteria: str
    accent_setting: str
    simplicity_level: SimplityLevel = SimplityLevel.L0
    hindi_support: float = 0.8  # 0.0–1.0; 0.8 at L0
    vocab_introduced: list[str] = []


class PronunciationScore(BaseModel):
    overall: float = 0.0
    weak_phonemes: list[str] = []


class Verdict(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"


class LLMResponse(BaseModel):
    verdict: Verdict
    correction: str
    next_spoken_line: str
    language_mix: str  # "hi" | "en" | "hi+en"
    notes_for_tracker: dict[str, Any] = {}


class TurnResult(BaseModel):
    activity_id: str
    transcript: str
    pronunciation: PronunciationScore
    llm_response: LLMResponse


class Level(BaseModel):
    id: str
    name: str
    cefr: str
    hindi_support: float
    accent_setting: str


class Lesson(BaseModel):
    id: str
    level_id: str = ""
    title: str
    activities: list[Activity]


class LessonFile(BaseModel):
    """One curriculum JSON file: a level header plus one lesson."""

    level: Level
    lesson: Lesson


class NextStep(str, Enum):
    REPEAT = "repeat"
    NEXT_ACTIVITY = "next_activity"
    NEXT_LESSON = "next_lesson"
    COURSE_COMPLETE = "course_complete"
