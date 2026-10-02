from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import configure_logging
from app.db.seed import ensure_default_user
from app.db.session import SessionLocal
from app.routers import decks, flashcards, health, reading, study, vocab_extraction

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_default_user(db)
    finally:
        db.close()
    yield


app = FastAPI(title="A2 Deutsch Hub API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(flashcards.router, prefix="/api/v1")
app.include_router(decks.router, prefix="/api/v1")
app.include_router(vocab_extraction.router, prefix="/api/v1")
app.include_router(study.router, prefix="/api/v1")
app.include_router(reading.router, prefix="/api/v1")
