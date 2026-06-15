# ENGLO — Voice-First English Tutor for Hindi Speakers

A complete, voice-first English tutoring system for **Hindi-speaking absolute
beginners**. The learner speaks; the app listens, scores pronunciation, grades
the response with an LLM (or an offline fallback), and replies in a warm
bilingual voice — fading from mostly-Hindi to English-only as the learner
progresses.

Built in 7 phases. Everything lives in the installable `englo/` Python package,
with a FastAPI backend and an Expo (React Native) mobile app.

---

## 1. What it does (the loop)

```
Learner speaks  ─►  STT (Whisper)  ─►  Pronunciation scoring  ─►  Tutor grader (LLM/local)
       ▲                                                                    │
       └──────────────  Bilingual TTS reply  ◄──  Course engine decides next step
```

- **Deterministic course engine** drives the flow — the LLM only *grades* a
  turn, it never decides what comes next.
- **Mastery gating**: an activity is cleared only after the required number of
  consecutive passes (2 for L0/L1 listen-and-repeat, 1 otherwise) AND the
  pronunciation score clears the activity's threshold.
- **Spaced repetition (SM-2)** and **error-driven drills** are injected
  automatically before curriculum activities.
- **Bilingual scaffolding** fades: `hindi_support` 0.8 at L0 → 0.0 by L4.

---

## 2. Repository layout

```
englo/                        # installable Python package
├── __main__.py               # CLI session loop      →  python -m englo
├── models.py                 # all Pydantic v2 data models
├── stt.py                    # faster-whisper speech-to-text (+ word timestamps)
├── tts.py                    # edge-tts text-to-speech (bilingual voice routing)
├── bilingual.py              # Devanagari/Latin segment splitting + voice routing
├── pronunciation.py          # local (Whisper-prob) + optional Azure scorer
├── tutor_llm.py              # Claude grader + offline heuristic fallback
├── orchestrator.py           # single-turn orchestration + Rich terminal UI
├── course_engine.py          # deterministic sequencer + mastery gating
├── mastery.py                # pass thresholds, required-passes logic
├── srs.py                    # SM-2 spaced repetition scheduler
├── progress.py               # progress persistence + drill generation
├── recorder.py               # microphone capture (CLI)
├── curriculum/               # 16 lesson JSON files (L0 + L1)
│   ├── l0_lesson1..8.json    # Bootstrap  (pre-A1, hindi_support 0.8)
│   └── l1_lesson1..8.json    # First Sentences (A1, hindi_support 0.5)
├── scripts/
│   └── author_curriculum.py  # generate curriculum via Claude
└── api/                      # FastAPI backend
    ├── __main__.py           # uvicorn launcher    →  python -m englo.api
    ├── app.py                # FastAPI app + CORS + /health
    ├── session_store.py      # in-memory session store (engine + tracker per id)
    └── routes/session.py     # 5 REST endpoints

mobile/                       # Expo React Native app (TypeScript)
├── App.tsx                   # navigation root
├── app.json, package.json, babel.config.js, tsconfig.json
├── assets/                   # icon / splash placeholders
└── src/
    ├── api/client.ts         # typed axios API client
    ├── hooks/useAudio.ts     # expo-av record (16kHz WAV) + playback
    ├── hooks/useSession.ts   # turn lifecycle state machine
    ├── components/           # ActivityCard, RecordButton, PronunciationBar
    └── screens/              # HomeScreen, LessonScreen

Dockerfile, render.yaml, Procfile, DEPLOY.md   # public deployment
requirements.txt, pyproject.toml, .env.example
main.py                       # thin shim → python -m englo
```

---

## 3. Tech stack

| Concern              | Choice                                   | Why |
|----------------------|------------------------------------------|-----|
| Speech-to-text       | **faster-whisper** (local)               | Accent-tolerant, Indian-English, word timestamps, free |
| Text-to-speech       | **edge-tts** (Microsoft neural, free)    | `en-IN-NeerjaNeural` + `hi-IN-SwaraNeural`, bilingual |
| Tutor grader         | **Claude** `claude-haiku-4-5-20251001`   | Structured JSON verdicts, low temp; offline fallback when no key |
| Pronunciation        | Local (Whisper word-probs) + opt. Azure  | Zero-dependency local scorer, cloud upgrade optional |
| Spaced repetition    | **SM-2**                                 | Proven, simple ease/interval algorithm |
| Backend              | **FastAPI** + uvicorn                    | Async REST wrapping the pipeline |
| Mobile               | **Expo / React Native** + expo-av        | Cross-platform voice UI |
| Data models          | **Pydantic v2**                          | Validation everywhere |

---

## 4. The 7 build phases (all complete)

1. **Skeleton loop** — STT → tutor LLM → TTS speak/listen round-trip.
2. **Course engine + data model** — deterministic sequencer, lesson loop.
3. **Pronunciation scoring** — local Whisper-prob scorer (+ optional Azure).
4. **Bilingual scaffolding** — Devanagari detection, per-segment voice routing,
   `hindi_support` directive fading.
5. **Progress + SRS + mastery gating** — SM-2, error-driven drills,
   consecutive-pass gating.
6. **Curriculum authoring** — L0 + L1 content: **16 lessons, 104 activities**.
7. **Platform wrap** — FastAPI backend + Expo mobile app.

Plus two follow-ups added during live testing:
- **Offline grader fallback** so the loop runs with no API key / no network.
- **Async `/turn` fix** — the blocking pipeline now runs in a worker thread.

---

## 5. Curriculum (current content)

- **16 lessons**, **104 activities**
- By type: `listen_repeat` 47, `translate_say` 30, `prompt_respond` 24,
  `recall_drill` 3
- **L0 Bootstrap** (pre-A1, hindi_support 0.8): Greetings, Numbers, Colors,
  Family, Objects, Food, Days, Review
- **L1 First Sentences** (A1, hindi_support 0.5): To-Be, Likes, Family sentences,
  Requests, Locations, Shopping, Daily Routine, Review
- L2–L4 (A2–B2) are scaffolded in the level map but content is not yet authored.

---

## 6. Running it

### Prerequisites
```bash
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY (optional — see note)
```
> **No API key?** The tutor automatically uses a built-in **offline heuristic
> grader** (lexical match + pronunciation score, bilingual feedback). Set a key
> to upgrade to Claude. Force offline anytime with `TUTOR_LLM_LOCAL=1`.

### A) Command-line tutor (speak into your mic)
```bash
python -m englo            # full voice session in the terminal
python -m englo --reset    # wipe saved progress and start over
```

### B) REST API server
```bash
python -m englo.api        # serves on http://0.0.0.0:8000
# Interactive API docs:    http://localhost:8000/docs
```

### C) Mobile app
```bash
cd mobile
npm install
# point it at your machine's LAN IP so the phone can reach the API:
echo "EXPO_PUBLIC_API_URL=http://<your-LAN-IP>:8000" > .env
npx expo start             # scan the QR code with Expo Go
```

---

## 7. API endpoints

| Method | Path                               | Purpose |
|--------|------------------------------------|---------|
| POST   | `/api/session`                     | Create a session → `{session_id}` |
| GET    | `/api/session/{id}/activity`       | Current activity + base64 MP3 prompt |
| POST   | `/api/session/{id}/turn`           | Upload WAV → verdict + scores + base64 MP3 reply |
| GET    | `/api/session/{id}/progress`       | Session summary (turns, pass rate, vocab) |
| DELETE | `/api/session/{id}`                | End session |
| GET    | `/health`                          | Liveness check |

Audio in = multipart WAV upload; audio out = base64-encoded MP3.

---

## 8. Deploying for a public URL

Configs are committed. Fastest path is Render (one-click blueprint):

1. Push the repo to GitHub.
2. Render → **New → Blueprint** → select the repo (it reads `render.yaml`).
3. Paste your `ANTHROPIC_API_KEY` when prompted (optional — offline grader works without).
4. **Apply** → you get `https://englo-api.onrender.com/docs`.

Also supported: **Railway**, **Fly.io**, plain **Docker** (`docker build -t englo . && docker run -p 8000:8000 englo`). Full steps in `DEPLOY.md`.

---

## 9. Verified live (this build was run end-to-end)

A complete `/turn` round-trip was exercised against the running server:

```
upload WAV ("Hello")
  → STT transcript: "Hello"               (faster-whisper)
  → pronunciation:  overall 0.88          (acc 0.76 / comp 1.0 / flu 1.0)
  → verdict:        pass                   (offline grader)
  → tutor reply:    "बहुत बढ़िया! Say it once more: Hello."
                    (Hindi praise in Hindi voice, English in Indian-English voice)
  → HTTP 200
```

TTS, STT, pronunciation scoring, the course engine, mastery gating, SM-2 SRS,
and bilingual segment routing all confirmed working.

---

## 10. Notes & limitations

- **Network**: edge-tts (Microsoft), the Whisper model download, and the
  Anthropic API need outbound internet. Every standard host/laptop has this.
- **API key**: optional thanks to the offline grader; Claude is used when a key
  is present.
- **Azure pronunciation** is optional — set `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION`
  to upgrade from the local Whisper-probability scorer.
- **Sessions** are stored in-memory; swap `session_store.py` for Redis/DB for
  multi-user production.
- **Not yet authored**: L2–L4 curriculum content.

---

## 11. Git

- Branch: `claude/new-session-u9bruv`
- Commit history (newest first):
  - `fix: offline grader fallback + async /turn crash`
  - `feat: add deployment configs (Docker/Render/Railway/Fly)`
  - `chore: add missing Expo boilerplate`
  - `feat: Phase 7 — FastAPI backend + Expo React Native mobile app`
  - `refactor: consolidate all code inside the englo/ package`
  - `feat: Phase 6 — full L0 + L1 curriculum (16 lessons, 104 activities)`
  - `feat: Phase 5 — mastery gating, SM-2 SRS, error-driven drills`
  - `feat: Phase 4 — bilingual scaffolding end-to-end`
  - `feat: Phase 3 — pronunciation scoring (local + Azure)`
  - `feat: Phase 2 — course engine, progress tracker, full lesson loop`
  - `feat: Phase 1 skeleton — STT → Tutor LLM → TTS speak-listen loop`
