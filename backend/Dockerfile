FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYDANTIC_AI_NO_BANNER=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# German Piper voices for Hören audio, baked in so offline TTS works without a first-use download.
# Before the app code so this ~250 MB layer is cached across code changes.
ARG PIPER_VOICES="thorsten/medium/de_DE-thorsten-medium karlsson/low/de_DE-karlsson-low kerstin/low/de_DE-kerstin-low ramona/low/de_DE-ramona-low"
RUN mkdir -p /opt/piper-voices && cd /opt/piper-voices \
    && for voice in $PIPER_VOICES; do \
         for ext in onnx onnx.json; do \
           curl -fsSL -o "$(basename "$voice").$ext" \
             "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/$voice.$ext?download=true"; \
         done; \
       done

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/docker-entrypoint.sh \
    && useradd --create-home appuser \
    && mkdir -p /data/media \
    && chown -R appuser:appuser /app /data/media

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
