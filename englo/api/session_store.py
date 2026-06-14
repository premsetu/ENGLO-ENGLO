"""In-memory session store.

Each session holds a CourseEngine + ProgressTracker pair.  Sessions are
keyed by a UUID string.  This is intentionally simple — swap for Redis
or a DB-backed store when moving to multi-user production.
"""

from __future__ import annotations

import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ..course_engine import CourseEngine
from ..progress import ProgressTracker


@dataclass
class Session:
    id: str
    engine: CourseEngine
    tracker: ProgressTracker
    # Temp dir for this session's audio files (cleaned up on close)
    _tmp_dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="englo-")))

    def audio_path(self, filename: str) -> Path:
        return self._tmp_dir / filename

    def close(self) -> None:
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


_store: dict[str, Session] = {}


def create() -> Session:
    sid = str(uuid.uuid4())
    session = Session(
        id=sid,
        engine=CourseEngine(),
        tracker=ProgressTracker(save_path=Path.home() / ".englo" / f"{sid}.json"),
    )
    _store[sid] = session
    return session


def get(sid: str) -> Session | None:
    return _store.get(sid)


def delete(sid: str) -> None:
    session = _store.pop(sid, None)
    if session:
        session.close()
