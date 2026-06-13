#!/usr/bin/env python3
"""ENGLO — voice-first English tutor for Hindi-speaking beginners.

Usage:
  python main.py               # resume from saved progress
  python main.py --reset       # wipe progress, start from scratch
  python main.py --dry <wav>   # single turn with a pre-recorded WAV (no mic)
"""

from __future__ import annotations

import sys

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


def _run_one_activity(engine, tracker, audio_path, is_drill=False) -> NextStep | None:
    """Run a single activity turn, log it, and return the NextStep (or None for drills)."""
    activity = engine.current_activity if not is_drill else None
    # For drills we receive the activity from outside; handled by caller.
    return None


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
                f"[dim]Resuming: lesson {cursor.get('lesson_idx', 0) + 1}, "
                f"activity {cursor.get('activity_idx', 0) + 1}[/dim]\n"
            )

    _banner()

    while not engine.is_complete:
        # ── SRS / error drills before each curriculum activity ────────────────
        drill = engine.pop_pending_drill(tracker)
        if drill:
            console.print(Rule(f"[cyan]Recall Drill[/cyan] [dim]({drill.id})[/dim]"))
            result = run_turn(drill, audio_path=dry_wav)
            tracker.log_turn(result, drill)
            tracker.mark_drill_done(drill.target_text, result.llm_response.verdict.value)
            if dry_wav:
                break
            _prompt_continue()
            continue

        # ── Curriculum activity ───────────────────────────────────────────────
        _lesson_header(engine)
        activity = engine.current_activity
        result = run_turn(activity, audio_path=dry_wav)
        tracker.log_turn(result, activity)

        step = engine.record_turn(result)
        tracker.set_cursor(engine.position())

        if step is NextStep.REPEAT:
            needed = engine.MAX_HARD_ATTEMPTS - engine._attempts
            console.print(
                f"[yellow]Not quite — let's try again.[/yellow] "
                f"[dim](up to {needed} more attempt{'s' if needed != 1 else ''})[/dim]\n"
            )
        elif step is NextStep.NEXT_ACTIVITY:
            console.print("[green]✓ Moving to next activity.[/green]\n")
        elif step is NextStep.NEXT_LESSON:
            console.print("[bold green]Lesson complete![/bold green]\n")
        elif step is NextStep.COURSE_COMPLETE:
            console.print("[bold magenta]Course complete![/bold magenta]\n")
            break

        if dry_wav:
            break

        _prompt_continue()

    console.print(Rule())
    console.print(f"[bold]Session summary:[/bold] {tracker.summary()}")


def _prompt_continue() -> None:
    try:
        inp = console.input("\n[dim]Press Enter for next, q to quit:[/dim] ")
    except (EOFError, KeyboardInterrupt):
        inp = "q"
    if inp.strip().lower() == "q":
        raise SystemExit(0)


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
