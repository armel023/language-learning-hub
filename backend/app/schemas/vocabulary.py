import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.vocabulary import Article, PartOfSpeech, VocabSource


class VocabularyItemBase(BaseModel):
    word: str
    part_of_speech: PartOfSpeech
    article: Article | None = None
    plural_form: str | None = None
    translation: str
    example_sentence_de: str | None = None
    example_sentence_translation: str | None = None
    notes: str | None = None
    deck_id: uuid.UUID | None = None


class VocabularyItemCreate(VocabularyItemBase):
    pass


class VocabularyItemUpdate(BaseModel):
    word: str | None = None
    part_of_speech: PartOfSpeech | None = None
    article: Article | None = None
    plural_form: str | None = None
    translation: str | None = None
    example_sentence_de: str | None = None
    example_sentence_translation: str | None = None
    notes: str | None = None
    deck_id: uuid.UUID | None = None


class VocabularyItemRead(VocabularyItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: VocabSource
    source_file_name: str | None
    review_count: int
    correct_count: int
    incorrect_hard_count: int
    incorrect_moderate_count: int
    last_reviewed_at: datetime | None
    study_due_at_session: int | None
    created_at: datetime
    updated_at: datetime


class VocabularyListResponse(BaseModel):
    items: list[VocabularyItemRead]
    total: int
    page: int
    page_size: int
