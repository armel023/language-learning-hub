# A2 Deutsch Hub

Personal study app for the Goethe A2 German exam: Flashcards (manual + AI-assisted vocabulary extraction), Lesen (reading practice, Teil 1-4, each exercise checked by an independent AI reviewer) and Schreiben (writing tasks with AI grading and corrections). Hören and Sprechen are coming soon.

## Stack

- Backend: Python + FastAPI, SQLAlchemy + Alembic, PostgreSQL
- Frontend: React + Vite + TypeScript, MUI, TanStack Query
- AI: Pydantic AI agents on Gemini (primary) or local Ollama (offline)
- Monitoring: OpenTelemetry traces to self-hosted Arize Phoenix; per-run token usage in the `ai_runs` table
- Docker Compose for local dev

## Running locally

1. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` (and Postgres credentials if you want to change the defaults).
2. Start everything:
   ```
   docker compose up --build
   ```
3. Frontend: http://localhost:5173
   Backend health check: http://localhost:5173/api/v1/health (the frontend proxies `/api` to the backend)
   Phoenix (agent traces, token usage): http://localhost:6006

## Using it from your phone or another device (Tailscale)

The app is reachable on this PC's Tailscale IP, e.g. `http://100.95.163.84:5173`. The frontend calls the
API on its own origin (`/api/v1`, proxied by nginx), so no configuration is needed per address. Only the
frontend (5173) and Phoenix (6006) are published to the network; Postgres and the backend's port 8000
listen on localhost only.

If another device can't connect, allow Tailscale devices through Windows Firewall (admin PowerShell):

```
New-NetFirewallRule -DisplayName "A2 Deutsch Hub (Tailscale)" -Direction Inbound -Protocol TCP -LocalPort 5173,6006 -RemoteAddress 100.64.0.0/10 -Action Allow
```

## Offline mode with Ollama

Install Ollama on this machine and pull a model (default `gemma3:4b`):

```
ollama pull gemma3:4b
```

Then set `AI_PROVIDER=ollama` in `.env` and restart the backend (`docker compose up -d backend`). The backend
container reaches the host's Ollama at `http://host.docker.internal:11434` (`OLLAMA_BASE_URL`).

On CPU-only machines expect minutes per exercise rather than seconds (roughly 7 tokens/s for gemma3:4b),
and noticeably lower quality than Gemini. `OLLAMA_MAX_TOKENS`, `OLLAMA_TEMPERATURE` and
`OLLAMA_FREQUENCY_PENALTY` tune generation; the penalty prevents the repetition loops small models fall
into when forced to produce JSON.

(The compose file also has an `ollama` service under the `offline` profile, for machines without a local
Ollama install. It downloads a ~9 GB image; point `OLLAMA_BASE_URL` at `http://ollama:11434` to use it.)

## Backend dev without Docker

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend dev without Docker

```
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000`, like nginx does in Docker.
