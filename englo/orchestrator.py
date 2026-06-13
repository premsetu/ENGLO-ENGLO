from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import pronunciation, stt, tts, tutor_llm
from .models import Activity, ActivityType, PronunciationScore, TurnResult

console = Console()

# Only these activity types warrant pronunciation scoring
_SCORED_TYPES = {ActivityType.LISTEN_REPEAT, ActivityType.RECALL_DRILL}


def run_turn(activity: Activity, audio_path: str | Path | None = None) -> TurnResult:
    """Drive one speak→listen→evaluate cycle for the given activity."""

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
        console.print("\n[bold green]Speak now — press Enter when done[/bold green]")
        tmp_path = recorder.record_to_file()
        source = tmp_path
    else:
        source = str(audio_path)

    # 3. STT — word timestamps included for pronunciation scoring
    console.print("[dim]Transcribing…[/dim]")
    stt_result = stt.transcribe_full(source)
    console.print(f"[cyan]You said:[/cyan] {stt_result.transcript!r}")

    if tmp_path:
        Path(tmp_path).unlink(missing_ok=True)

    # 4. Pronunciation scoring (only for shadow/repeat activities; stub otherwise)
    if activity.type in _SCORED_TYPES:
        console.print("[dim]Scoring pronunciation…[/dim]")
        pron = pronunciation.score(
            stt_result,
            target_text=activity.target_text,
            audio_path=source if audio_path else None,
        )
        _show_pronunciation(pron)
    else:
        pron = PronunciationScore(backend="none")

    # 5. Tutor LLM evaluation
    console.print("[dim]Evaluating…[/dim]")
    llm_resp = tutor_llm.evaluate(activity, stt_result.transcript, pron)

    # 6. Display + speak the response
    _show_verdict(llm_resp)
    tts.speak(
        llm_resp.next_spoken_line,
        language_mix=llm_resp.language_mix,
        simplicity_level=activity.simplicity_level,
    )

    return TurnResult(
        activity_id=activity.id,
        transcript=stt_result.transcript,
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


def _show_pronunciation(pron: PronunciationScore) -> None:
    bar = _score_bar(pron.overall)
    weak = ", ".join(pron.weak_phonemes) if pron.weak_phonemes else "none"
    colour = _score_colour(pron.overall)
    console.print(
        Panel(
            Text.from_markup(
                f"[{colour}]Overall {pron.overall:.0%}[/{colour}]  {bar}\n"
                f"Accuracy [bold]{pron.accuracy:.0%}[/bold]  "
                f"Completeness [bold]{pron.completeness:.0%}[/bold]  "
                f"Fluency [bold]{pron.fluency:.0%}[/bold]\n"
                f"[dim]Weak phonemes:[/dim] {weak}  "
                f"[dim]backend: {pron.backend}[/dim]"
            ),
            title="Pronunciation",
            border_style=colour,
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


def _score_bar(score: float, width: int = 12) -> str:
    filled = round(score * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _score_colour(score: float) -> str:
    if score >= 0.75:
        return "green"
    if score >= 0.50:
        return "yellow"
    return "red"
