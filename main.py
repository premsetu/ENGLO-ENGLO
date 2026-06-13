#!/usr/bin/env python3
"""ENGLO — voice-first English tutor for Hindi-speaking beginners.

Usage:
  python main.py               # resume from saved progress
  python main.py --reset       # wipe progress, start from scratch
  python main.py --dry <wav>   # single turn with a pre-recorded WAV (no mic)
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.rule import Rule

load_dotenv()

from englo.course_engine import CourseEngine
from englo.models import NextStep
from englo.orchestrator import run_turn
from englo.progress import ProgressTracker

console = Console()


def _banner() -> None:
    console.print(Rule("[bold blue]ENGLO — English Tutor[/bold blue]"))
    console.print("[dim]Voice-first English course for Hindi-speaking beginners[/dim]\n")


def _lesson_header(engine: CourseEngine) -> None:
    lf = engine.current_lesson_file
    console.print(
        Rule(
            f"[yellow]{lf.level.name} · {lf.lesson.title}[/yellow] "
            f"[dim]({lf.lesson.id})[/dim]"
        )
    )


def run_session(reset: bool = False, dry_wav: str | None = None) -> None:
    tracker = ProgressTracker()
    engine = CourseEngine()

    if reset:
        tracker.reset()
        console.print("[bold red]Progress reset.[/bold red]\n")
    else:
        cursor = tracker.get_cursor()
        if cursor:
            engine.restore(cursor)
            console.print(
                f"[dim]Resuming from lesson {cursor.get('lesson_idx', 0) + 1}, "
                f"activity {cursor.get('activity_idx', 0) + 1}[/dim]\n"
            )

    _banner()

    while not engine.is_complete:
        _lesson_header(engine)
        activity = engine.current_activity

        # Single-turn dry-run mode: use supplied WAV, then stop after one turn
        audio_path = dry_wav

        result = run_turn(activity, audio_path=audio_path)
        tracker.log_turn(result)

        step = engine.record_turn(result)
        tracker.set_cursor(engine.position())

        if step is NextStep.REPEAT:
            remaining = engine.attempts
            console.print(
                f"[yellow]Let's try again[/yellow] "
                f"[dim](attempt {remaining} of {engine.MAX_ATTEMPTS if hasattr(engine, 'MAX_ATTEMPTS') else 3})[/dim]\n"
            )
        elif step is NextStep.NEXT_LESSON:
            console.print(
                "\n[bold green]Lesson complete! Starting next lesson…[/bold green]\n"
            )
        elif step is NextStep.COURSE_COMPLETE:
            console.print("\n[bold magenta]Course complete! 🎉[/bold magenta]\n")
            break

        # In dry-run mode stop after the first turn
        if dry_wav:
            break

        # Prompt to continue or quit between activities
        try:
            inp = console.input("\n[dim]Press Enter for the next activity, q to quit:[/dim] ")
        except (EOFError, KeyboardInterrupt):
            inp = "q"
        if inp.strip().lower() == "q":
            break

    console.print(Rule())
    console.print(f"[bold]Session summary:[/bold] {tracker.summary()}")


def main() -> None:
    args = sys.argv[1:]
    reset = "--reset" in args
    dry_wav: str | None = None
    if "--dry" in args:
        idx = args.index("--dry")
        if idx + 1 < len(args):
            dry_wav = args[idx + 1]
        else:
            console.print("[red]--dry requires a WAV file path[/red]")
            sys.exit(1)

    run_session(reset=reset, dry_wav=dry_wav)


if __name__ == "__main__":
    main()
