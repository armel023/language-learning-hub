# A2 Deutsch Hub

Personal study app for the Goethe A2 German exam: Flashcards (manual + AI-assisted vocabulary extraction) and Lesen (reading practice, Teil 1-4). Hören, Schreiben, and Sprechen are coming soon.

## Stack

- Backend: Python + FastAPI, SQLAlchemy + Alembic, PostgreSQL
- Frontend: React + Vite + TypeScript, TanStack Query
- AI: Gemini API (primary) or local Ollama + Gemma (offline fallback)
- Docker Compose for local dev

## Running locally

1. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` (and Postgres credentials if you want to change the defaults).
2. Start everything:
   ```
   docker compose up --build
   ```
3. Frontend: http://localhost:5173
   Backend health check: http://localhost:8000/api/v1/health

### Optional: offline mode with Ollama

```
docker compose --profile offline up --build
```

Then set `AI_PROVIDER=ollama` in `.env` and pull the model into the running container:

```
docker compose exec ollama ollama pull gemma2:9b
```

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
