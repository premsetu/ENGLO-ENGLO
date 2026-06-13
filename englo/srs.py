"""SM-2 spaced-repetition scheduler for vocab items.

Each VocabItem stores the SM-2 state.  SRSScheduler manages a collection of
items, schedules reviews, and converts due items into Recall-drill Activities
that the course engine can inject between curriculum activities.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel

from .models import Activity, ActivityType, SimplityLevel


class VocabItem(BaseModel):
    item: str                      # word or short phrase
    ease: float = 2.5              # SM-2 E-factor (min 1.3)
    interval: int = 1              # days until next review
    reps: int = 0                  # successful review streak
    due_date: str = ""             # ISO date; "" = due today
    source_activity: str = ""      # activity_id where first introduced

    def is_due(self, today: date | None = None) -> bool:
        ref = today or date.today()
        if not self.due_date:
            return True
        return date.fromisoformat(self.due_date) <= ref


# Verdict → numeric quality score (SM-2 uses 0–5; we map to 0–1)
_VERDICT_SCORE = {"pass": 1.0, "partial": 0.6, "fail": 0.0}


class SRSScheduler:
    def __init__(self, items: list[dict[str, Any]] | None = None):
        self._items: dict[str, VocabItem] = {}
        for raw in (items or []):
            vi = VocabItem(**raw)
            self._items[vi.item] = vi

    # ── mutation ──────────────────────────────────────────────────────────────

    def add(self, word: str, source_activity: str = "") -> None:
        if word not in self._items:
            self._items[word] = VocabItem(
                item=word,
                source_activity=source_activity,
                due_date=date.today().isoformat(),
            )

    def review(self, word: str, verdict: str) -> VocabItem:
        """Update SM-2 state after a review.  Returns the updated item."""
        if word not in self._items:
            self.add(word)
        item = self._items[word]
        score = _VERDICT_SCORE.get(verdict, 0.0)

        if score >= 0.6:
            if item.reps == 0:
                new_interval = 1
            elif item.reps == 1:
                new_interval = 6
            else:
                new_interval = max(1, round(item.interval * item.ease))
            new_ease = max(1.3, item.ease + 0.1 - (1 - score) * (0.08 + (1 - score) * 0.02))
            item.reps += 1
            item.ease = round(new_ease, 3)
            item.interval = new_interval
        else:
            item.reps = 0
            item.interval = 1

        item.due_date = (date.today() + timedelta(days=item.interval)).isoformat()
        self._items[word] = item
        return item

    # ── queries ───────────────────────────────────────────────────────────────

    def due_items(self, today: date | None = None) -> list[VocabItem]:
        return [v for v in self._items.values() if v.is_due(today)]

    def to_dict(self) -> list[dict]:
        return [v.model_dump() for v in self._items.values()]

    # ── drill factory ─────────────────────────────────────────────────────────

    @staticmethod
    def make_drill(word: str, hindi_support: float = 0.5) -> Activity:
        """Return a recall_drill Activity for the given vocab item."""
        return Activity(
            id=f"srs-{re.sub(r'[^a-z0-9]', '-', word.lower())}",
            type=ActivityType.RECALL_DRILL,
            target_text=word,
            hindi_scaffold=f"याद करें — अंग्रेज़ी में बोलिए: {word}",
            expected_pattern=word.lower(),
            success_criteria="pronunciation_accuracy >= 0.65 and utterance_complete",
            accent_setting="slow_clear",
            simplicity_level=SimplityLevel.L1,
            hindi_support=hindi_support,
            vocab_introduced=[],
        )
