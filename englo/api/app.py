"""FastAPI application — wraps the englo pipeline as a REST API.

Start with:
  python -m englo.api           (uses uvicorn)
  uvicorn englo.api.app:app --reload --port 8000

Endpoints:
  POST   /api/session                     create session
  GET    /api/session/{id}/activity       current activity + TTS prompt
  POST   /api/session/{id}/turn           submit audio, get verdict + TTS response
  GET    /api/session/{id}/progress       session summary
  DELETE /api/session/{id}                end session
  GET    /health                          liveness check
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import session as session_router

app = FastAPI(
    title="ENGLO API",
    description="Voice-first English tutor for Hindi-speaking beginners",
    version="0.1.0",
)

# Allow requests from the Expo dev server and any local origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
