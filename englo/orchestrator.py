from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import stt, tts, tutor_llm
from .models import Activity, PronunciationScore, TurnResult

console = Console()


def run_turn(activity: Activity, audio_path: str | Path | None = None) -> TurnResult:
    """Drive one speak→listen→evaluate cycle for the given activity.

    If `audio_path` is supplied the recorder is skipped (useful for testing).
    Returns a TurnResult with the transcript, pronunciation stub, and LLM verdict.
    """
    # 1. Play the tutor prompt
    _show_prompt(activity)
    tts.speak(
        activity.hindi_scaffold,
        language_mix="hi+en",
        simplicity_level=activity.simplicity_level,
    )

    # 2. Record learner speech (or use supplied file)
    tmp_path: str | None = None
    if audio_path is None:
        from . import recorder
        console.print("\n[bold green]🎤 Speak now — press Enter when done[/bold green]")
        tmp_path = recorder.record_to_file()
        source = tmp_path
    else:
        source = str(audio_path)

    # 3. STT
    console.print("[dim]Transcribing…[/dim]")
    transcript = stt.transcribe(source)
    console.print(f"[cyan]You said:[/cyan] {transcript!r}")

    if tmp_path:
        Path(tmp_path).unlink(missing_ok=True)

    # 4. Pronunciation scoring — stub for Phase 1 (Phase 3 wires real scorer)
    pron = PronunciationScore(overall=0.0, weak_phonemes=[])

    # 5. Tutor LLM evaluation
    console.print("[dim]Evaluating…[/dim]")
    llm_resp = tutor_llm.evaluate(activity, transcript, pron)

    # 6. Display + speak the response
    _show_verdict(llm_resp)
    tts.speak(
        llm_resp.next_spoken_line,
        language_mix=llm_resp.language_mix,
        simplicity_level=activity.simplicity_level,
    )

    return TurnResult(
        activity_id=activity.id,
        transcript=transcript,
        pronunciation=pron,
        llm_response=llm_resp,
    )


def _show_prompt(activity: Activity) -> None:
    console.print(
        Panel(
            Text.from_markup(
                f"[bold]Target:[/bold] {activity.target_text}\n"
                f"[dim]{activity.hindi_scaffold}[/dim]"
            ),
            title=f"[yellow]{activity.type.value}[/yellow]",
            border_style="yellow",
        )
    )


def _show_verdict(resp) -> None:
    colour = {"pass": "green", "partial": "yellow", "fail": "red"}.get(
        resp.verdict.value, "white"
    )
    console.print(
        Panel(
            Text.from_markup(
                f"[bold {colour}]Verdict: {resp.verdict.value.upper()}[/bold {colour}]\n"
                f"[italic]{resp.correction}[/italic]\n\n"
                f'"{resp.next_spoken_line}"'
            ),
            title="Tutor",
            border_style=colour,
        )
    )
