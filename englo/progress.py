from __future__ import annotations

import json
import time
from pathlib import Path

from .models import TurnResult

_DEFAULT_SAVE_PATH = Path.home() / ".englo" / "progress.json"


class ProgressTracker:
    """Persists learner state between sessions.

    Stores:
      - course engine cursor (lesson / activity / attempts)
      - per-activity history (transcript, verdict, timestamp)
      - simple vocab seen set
    """

    def __init__(self, save_path: Path | None = None):
        self.save_path = save_path or _DEFAULT_SAVE_PATH
        self._data: dict = self._load()

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self.save_path.exists():
            try:
                return json.loads(self.save_path.read_text())
            except json.JSONDecodeError:
                pass
        return {"cursor": {}, "history": [], "vocab_seen": []}

    def save(self) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2))

    # ── cursor (course engine position) ──────────────────────────────────────

    def get_cursor(self) -> dict:
        return self._data.get("cursor", {})

    def set_cursor(self, cursor: dict) -> None:
        self._data["cursor"] = cursor
        self.save()

    def reset(self) -> None:
        self._data = {"cursor": {}, "history": [], "vocab_seen": []}
        self.save()

    # ── turn logging ─────────────────────────────────────────────────────────

    def log_turn(self, result: TurnResult) -> None:
        entry = {
            "ts": int(time.time()),
            "activity_id": result.activity_id,
            "transcript": result.transcript,
            "verdict": result.llm_response.verdict.value,
            "pron_overall": result.pronunciation.overall,
        }
        # Merge any vocab from the LLM's notes
        reinforced = result.llm_response.notes_for_tracker.get("vocab_reinforced", [])
        for word in reinforced:
            if word not in self._data["vocab_seen"]:
                self._data["vocab_seen"].append(word)

        self._data.setdefault("history", []).append(entry)
        self.save()

    # ── read-back helpers ─────────────────────────────────────────────────────

    def total_turns(self) -> int:
        return len(self._data.get("history", []))

    def pass_rate(self) -> float:
        history = self._data.get("history", [])
        if not history:
            return 0.0
        passes = sum(1 for h in history if h["verdict"] == "pass")
        return passes / len(history)

    def summary(self) -> str:
        return (
            f"Turns: {self.total_turns()}  |  "
            f"Pass rate: {self.pass_rate():.0%}  |  "
            f"Vocab seen: {len(self._data.get('vocab_seen', []))}"
        )
