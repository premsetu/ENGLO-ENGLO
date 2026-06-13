from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .models import Activity, TurnResult
from .srs import SRSScheduler

_DEFAULT_SAVE_PATH = Path.home() / ".englo" / "progress.json"

# Inject an error-targeted drill once this many occurrences are logged
_ERROR_DRILL_THRESHOLD = 3

# Words that exercise each phoneme trap (spec §9: error-driven adaptation)
_ERROR_DRILL_WORDS: dict[str, list[str]] = {
    "θ/ð (th-sound)":       ["this", "that", "the", "three", "think", "thank you"],
    "w (not v)":            ["we", "water", "what", "where", "work", "want"],
    "vowel cluster":        ["eat", "out", "air", "ear", "oil", "good"],
    "ʃ (sh in -tion)":     ["station", "question", "action", "nation"],
    "r (retroflex risk)":  ["right", "road", "run", "read", "write"],
    "v (not b/w)":          ["very", "have", "give", "live", "love"],
    "past-tense -ed ending":["walked", "talked", "played", "helped", "wanted"],
}


class ProgressTracker:
    """Persists all learner state between sessions.

    Keys in the backing JSON:
      cursor        — course engine position (lesson/activity/attempts)
      history       — per-turn log
      vocab_seen    — flat list of words introduced so far
      vocab_srs     — SM-2 state for each vocab item
      error_log     — {error_type: {count, last_seen, example}}
    """

    def __init__(self, save_path: Path | None = None):
        self.save_path = save_path or _DEFAULT_SAVE_PATH
        self._data: dict[str, Any] = self._load()
        self.srs = SRSScheduler(self._data.get("vocab_srs", []))

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self.save_path.exists():
            try:
                return json.loads(self.save_path.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "cursor": {},
            "history": [],
            "vocab_seen": [],
            "vocab_srs": [],
            "error_log": {},
        }

    def save(self) -> None:
        self._data["vocab_srs"] = self.srs.to_dict()
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2))

    def reset(self) -> None:
        self._data = {
            "cursor": {},
            "history": [],
            "vocab_seen": [],
            "vocab_srs": [],
            "error_log": {},
        }
        self.srs = SRSScheduler()
        self.save()

    # ── cursor ────────────────────────────────────────────────────────────────

    def get_cursor(self) -> dict:
        return self._data.get("cursor", {})

    def set_cursor(self, cursor: dict) -> None:
        self._data["cursor"] = cursor
        self.save()

    # ── turn logging ──────────────────────────────────────────────────────────

    def log_turn(self, result: TurnResult, activity: Activity) -> None:
        entry = {
            "ts": int(time.time()),
            "activity_id": result.activity_id,
            "transcript": result.transcript,
            "verdict": result.llm_response.verdict.value,
            "pron_overall": result.pronunciation.overall,
        }
        self._data.setdefault("history", []).append(entry)

        verdict = result.llm_response.verdict.value

        # Register new vocab and review existing items via SRS
        for word in activity.vocab_introduced:
            if word not in self._data.setdefault("vocab_seen", []):
                self._data["vocab_seen"].append(word)
            self.srs.add(word, source_activity=activity.id)

        # Also review vocab reinforced by the LLM this turn
        for word in result.llm_response.notes_for_tracker.get("vocab_reinforced", []):
            self.srs.review(word, verdict)

        # Log phoneme errors from the pronunciation scorer
        for label in result.pronunciation.weak_phonemes:
            self.log_error(label, example=result.transcript)

        self.save()

    def log_error(self, error_type: str, example: str = "") -> None:
        log = self._data.setdefault("error_log", {})
        entry = log.setdefault(error_type, {"count": 0, "last_seen": 0, "example": ""})
        entry["count"] += 1
        entry["last_seen"] = int(time.time())
        if example:
            entry["example"] = example
        self._data["error_log"] = log

    # ── drill generation ──────────────────────────────────────────────────────

    def get_srs_drills(self, hindi_support: float = 0.5) -> list[Activity]:
        """Return Recall-drill Activities for all SRS items due today."""
        from .srs import SRSScheduler
        return [SRSScheduler.make_drill(vi.item, hindi_support) for vi in self.srs.due_items()]

    def get_error_drills(self, hindi_support: float = 0.5) -> list[Activity]:
        """Return targeted drill Activities for errors above the threshold."""
        from .srs import SRSScheduler
        drills: list[Activity] = []
        for error_type, entry in self._data.get("error_log", {}).items():
            if entry["count"] >= _ERROR_DRILL_THRESHOLD:
                words = _ERROR_DRILL_WORDS.get(error_type, [])
                # One drill per error type (first word in the list)
                if words:
                    drills.append(SRSScheduler.make_drill(words[0], hindi_support))
        return drills

    def get_pending_drills(self, hindi_support: float = 0.5) -> list[Activity]:
        """SRS + error drills combined, deduped by activity id."""
        seen: set[str] = set()
        result: list[Activity] = []
        for a in self.get_srs_drills(hindi_support) + self.get_error_drills(hindi_support):
            if a.id not in seen:
                seen.add(a.id)
                result.append(a)
        return result

    def mark_drill_done(self, word: str, verdict: str) -> None:
        """Update SRS state after a recall drill was completed."""
        self.srs.review(word, verdict)
        self.save()

    # ── read-back helpers ─────────────────────────────────────────────────────

    def total_turns(self) -> int:
        return len(self._data.get("history", []))

    def pass_rate(self) -> float:
        history = self._data.get("history", [])
        if not history:
            return 0.0
        return sum(1 for h in history if h["verdict"] == "pass") / len(history)

    def summary(self) -> str:
        due = len(self.srs.due_items())
        error_count = sum(
            1 for e in self._data.get("error_log", {}).values()
            if e["count"] >= _ERROR_DRILL_THRESHOLD
        )
        return (
            f"Turns: {self.total_turns()}  |  "
            f"Pass rate: {self.pass_rate():.0%}  |  "
            f"Vocab: {len(self._data.get('vocab_seen', []))}  |  "
            f"SRS due: {due}  |  "
            f"Error drills: {error_count}"
        )
