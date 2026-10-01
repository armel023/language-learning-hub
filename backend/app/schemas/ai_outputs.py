from pydantic import BaseModel, Field

from app.models.vocabulary import Article, PartOfSpeech


class ExtractedVocabEntry(BaseModel):
    word: str
    part_of_speech: PartOfSpeech
    article: Article | None = None
    plural_form: str | None = None
    translation: str
    example_sentence_de: str | None = None
    example_sentence_translation: str | None = None


class VocabExtractionAIOutput(BaseModel):
    entries: list[ExtractedVocabEntry] = Field(default_factory=list)
