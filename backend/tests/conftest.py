import os

# Pydantic AI prints an observability banner on first run; keep test output clean.
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
