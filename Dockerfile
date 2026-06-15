FROM python:3.11-slim

# System libs: libsndfile for soundfile, ffmpeg for audio decoding (Whisper/edge-tts)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY englo/ ./englo/
COPY pyproject.toml .

# Whisper model + edge-tts fetch at runtime; cache dirs live under /app
ENV HF_HOME=/app/.cache/huggingface \
    API_RELOAD=false

EXPOSE 8000

# Hosts inject $PORT; the entrypoint honours it (falls back to 8000 locally)
CMD ["python", "-m", "englo.api"]
