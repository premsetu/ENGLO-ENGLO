# Deploying ENGLO (getting a public link)

The API can't be reached from a Claude Code container — that session is
isolated with no public port. To get a real, clickable URL, deploy it to any
host. All configs are in this repo; pick one path below.

## Option A — Render (one-click blueprint, recommended)

1. Push this branch to GitHub.
2. [Render dashboard](https://dashboard.render.com) → **New → Blueprint**.
3. Select this repo + branch. Render reads `render.yaml` automatically.
4. Paste your **`ANTHROPIC_API_KEY`** when prompted (it's marked secret).
5. **Apply**. Render builds the `Dockerfile` and gives you:
   `https://englo-api.onrender.com/docs`

Free plan sleeps when idle; the first request after sleep is slow (it also
downloads the Whisper model on first boot). Upgrade the plan to keep it warm.

## Option B — Railway

1. [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**.
2. Railway detects the `Dockerfile` (or the `Procfile`).
3. Add env var `ANTHROPIC_API_KEY` in the service settings.
4. **Generate Domain** → you get `https://englo-api.up.railway.app/docs`.

## Option C — Fly.io

```bash
fly launch --dockerfile Dockerfile --name englo-api
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly deploy
# → https://englo-api.fly.dev/docs
```

## Option D — any Docker host / VPS

```bash
docker build -t englo-api .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... englo-api
# → http://<server-ip>:8000/docs
```

## After deploy

- API docs:   `https://<your-host>/docs`
- Health:     `https://<your-host>/health` → `{"status":"ok"}`
- Point the mobile app at it: set `EXPO_PUBLIC_API_URL=https://<your-host>`
  in `mobile/.env`, then `cd mobile && npx expo start`.

## Notes

- The host needs outbound internet for edge-tts (Microsoft), the Whisper model
  download, and the Anthropic API. Every host above has that by default.
- `$PORT` is honoured automatically — the entrypoint reads it before falling
  back to `8000`, so Render/Railway/Fly/Heroku all just work.
