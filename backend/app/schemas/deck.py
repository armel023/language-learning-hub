import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeckBase(BaseModel):
    name: str
    description: str | None = None


class DeckCreate(DeckBase):
    pass


class DeckUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class DeckRead(DeckBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
