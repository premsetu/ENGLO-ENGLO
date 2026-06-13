#!/usr/bin/env python3
"""ENGLO — Phase 1 skeleton: one activity loop (STT → LLM verdict → TTS)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.rule import Rule

load_dotenv()

from englo.models import Activity
from englo.orchestrator import run_turn

console = Console()

_CURRICULUM = Path(__file__).parent / "englo" / "curriculum" / "l0_lesson1.json"


def load_activity(activity_id: str | None = None) -> Activity:
    data = json.loads(_CURRICULUM.read_text())
    activities = data["lesson"]["activities"]
    if activity_id:
        for a in activities:
            if a["id"] == activity_id:
                return Activity(**a)
        raise ValueError(f"Activity {activity_id!r} not found")
    return Activity(**activities[0])


def main() -> None:
    console.print(Rule("[bold blue]ENGLO — English Tutor[/bold blue]"))
    console.print(
        "[dim]Phase 1 skeleton · Level L0 · Lesson 1: Greetings & Introductions[/dim]\n"
    )

    # Optional: pass an activity ID or audio file path as CLI args
    activity_id = sys.argv[1] if len(sys.argv) > 1 else None
    audio_file = sys.argv[2] if len(sys.argv) > 2 else None

    activity = load_activity(activity_id)

    console.print(f"[bold]Activity:[/bold] {activity.id} — {activity.type.value}\n")

    result = run_turn(activity, audio_path=audio_file)

    console.print(Rule())
    console.print(f"[bold]Verdict:[/bold] {result.llm_response.verdict.value}")
    console.print(f"[bold]Transcript:[/bold] {result.transcript!r}")


if __name__ == "__main__":
    main()
