"""Session lifecycle and turn-processing endpoints."""

from __future__ import annotations

import base64
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ... import stt, tts
from ...models import ActivityType, NextStep
from ...orchestrator import _SCORED_TYPES
from ... import pronunciation as pron_mod
from ... import tutor_llm
from ...models import PronunciationScore
from .. import session_store

router = APIRouter(prefix="/api/session", tags=["session"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SessionCreated(BaseModel):
    session_id: str


class ActivityOut(BaseModel):
    session_id: str
    activity_id: str
    activity_type: str
    target_text: str
    hindi_scaffold: str
    simplicity_level: str
    hindi_support: float
    is_drill: bool
    prompt_audio_b64: str   # base64 MP3 of the tutor's opening prompt
    lesson_title: str
    level_name: str


class TurnOut(BaseModel):
    session_id: str
    transcript: str
    pronunciation_overall: float
    pronunciation_accuracy: float
    pronunciation_completeness: float
    pronunciation_fluency: float
    weak_phonemes: list[str]
    verdict: str
    correction: str
    next_spoken_line: str
    language_mix: str
    response_audio_b64: str  # base64 MP3 of tutor's spoken response
    step: str                # repeat | next_activity | next_lesson | course_complete
    is_complete: bool


class ProgressOut(BaseModel):
    session_id: str
    total_turns: int
    pass_rate: float
    vocab_count: int
    summary: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _b64_tts(text: str, language_mix: str, simplicity_level: str) -> str:
    audio_bytes = tts.synthesize(text, language_mix=language_mix,
                                  simplicity_level=simplicity_level)
    return base64.b64encode(audio_bytes).decode()


def _get_or_404(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=SessionCreated, status_code=201)
def create_session():
    """Start a new learning session from the beginning of the curriculum."""
    session = session_store.create()
    return SessionCreated(session_id=session.id)


@router.get("/{session_id}/activity", response_model=ActivityOut)
def get_activity(session_id: str):
    """Return the current activity + TTS of the tutor prompt, ready to play."""
    session = _get_or_404(session_id)
    engine = session.engine

    if engine.is_complete:
        raise HTTPException(status_code=410, detail="Course complete")

    # Check for pending SRS/error drills first
    drill = engine.pop_pending_drill(session.tracker)
    is_drill = drill is not None
    activity = drill if is_drill else engine.current_activity

    lf = engine.current_lesson_file
    prompt_audio = _b64_tts(
        activity.hindi_scaffold,
        language_mix="hi+en",
        simplicity_level=activity.simplicity_level,
    )

    return ActivityOut(
        session_id=session_id,
        activity_id=activity.id,
        activity_type=activity.type.value,
        target_text=activity.target_text,
        hindi_scaffold=activity.hindi_scaffold,
        simplicity_level=activity.simplicity_level,
        hindi_support=activity.hindi_support,
        is_drill=is_drill,
        prompt_audio_b64=prompt_audio,
        lesson_title=lf.lesson.title,
        level_name=lf.level.name,
    )


@router.post("/{session_id}/turn", response_model=TurnOut)
async def submit_turn(session_id: str, audio: UploadFile = File(...)):
    """Accept a learner's audio recording and return the evaluation + tutor response."""
    session = _get_or_404(session_id)
    engine = session.engine

    if engine.is_complete:
        raise HTTPException(status_code=410, detail="Course complete")

    # Determine which activity we're evaluating
    drill = engine.pop_pending_drill(session.tracker)
    is_drill = drill is not None
    activity = drill if is_drill else engine.current_activity

    # Save uploaded audio to session temp dir
    audio_path = session.audio_path(f"{uuid.uuid4()}.wav")
    audio_path.write_bytes(await audio.read())

    # STT
    stt_result = stt.transcribe_full(str(audio_path))

    # Pronunciation scoring (only for scored activity types)
    if activity.type in _SCORED_TYPES:
        pron = pron_mod.score(stt_result, activity.target_text, str(audio_path))
    else:
        pron = PronunciationScore(backend="none")

    audio_path.unlink(missing_ok=True)

    # LLM evaluation
    llm_resp = tutor_llm.evaluate(activity, stt_result.transcript, pron)

    # TTS of tutor response
    response_audio = _b64_tts(
        llm_resp.next_spoken_line,
        language_mix=llm_resp.language_mix,
        simplicity_level=activity.simplicity_level,
    )

    # Determine next step
    from ...models import TurnResult
    result = TurnResult(
        activity_id=activity.id,
        transcript=stt_result.transcript,
        pronunciation=pron,
        llm_response=llm_resp,
    )

    if is_drill:
        session.tracker.log_turn(result, activity)
        session.tracker.mark_drill_done(activity.target_text, llm_resp.verdict.value)
        step = NextStep.NEXT_ACTIVITY
    else:
        session.tracker.log_turn(result, activity)
        step = engine.record_turn(result)
        session.tracker.set_cursor(engine.position())

    return TurnOut(
        session_id=session_id,
        transcript=stt_result.transcript,
        pronunciation_overall=pron.overall,
        pronunciation_accuracy=pron.accuracy,
        pronunciation_completeness=pron.completeness,
        pronunciation_fluency=pron.fluency,
        weak_phonemes=pron.weak_phonemes,
        verdict=llm_resp.verdict.value,
        correction=llm_resp.correction,
        next_spoken_line=llm_resp.next_spoken_line,
        language_mix=llm_resp.language_mix,
        response_audio_b64=response_audio,
        step=step.value,
        is_complete=engine.is_complete,
    )


@router.get("/{session_id}/progress", response_model=ProgressOut)
def get_progress(session_id: str):
    session = _get_or_404(session_id)
    tracker = session.tracker
    return ProgressOut(
        session_id=session_id,
        total_turns=tracker.total_turns(),
        pass_rate=tracker.pass_rate(),
        vocab_count=len(tracker._data.get("vocab_seen", [])),
        summary=tracker.summary(),
    )


@router.delete("/{session_id}", status_code=204)
def end_session(session_id: str):
    session_store.delete(session_id)
