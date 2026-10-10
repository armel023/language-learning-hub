"""Generated media on disk (a Docker volume), served by the API under MEDIA_URL_PREFIX."""
import shutil
from pathlib import Path

from app.config import get_settings

MEDIA_URL_PREFIX = "/api/v1/media"


def media_root() -> Path:
    return Path(get_settings().media_dir)


def save(relative_path: str, data: bytes) -> str:
    """Write a file under the media root and return the URL the frontend can play it from."""
    path = media_root() / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"{MEDIA_URL_PREFIX}/{relative_path}"


def delete_dir(relative_dir: str) -> None:
    """Best-effort cleanup, e.g. when generation fails after some audio was written."""
    shutil.rmtree(media_root() / relative_dir, ignore_errors=True)
