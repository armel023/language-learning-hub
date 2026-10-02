from pydantic import BaseModel, Field, model_validator

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


def _validate_paragraph_question_mapping(paragraphs: list, questions: list) -> None:
    """Shared structural check for Teils that pair exactly 5 paragraphs with exactly 5
    questions, one-to-one (Teil 1 and Teil 3)."""
    paragraph_numbers = sorted(p.paragraph_number for p in paragraphs)
    if paragraph_numbers != [1, 2, 3, 4, 5]:
        raise ValueError("paragraphs must be numbered 1-5 with no duplicates")

    question_numbers = sorted(q.question_number for q in questions)
    if question_numbers != [1, 2, 3, 4, 5]:
        raise ValueError("questions must be numbered 1-5 with no duplicates")

    mapped_paragraphs = sorted(q.paragraph_number for q in questions)
    if mapped_paragraphs != [1, 2, 3, 4, 5]:
        raise ValueError(
            "each question must map to a distinct paragraph 1-5 (one question per paragraph)"
        )


class ReadingTeil1ParagraphAI(BaseModel):
    paragraph_number: int = Field(ge=1, le=5)
    text: str


class ReadingTeil1QuestionAI(BaseModel):
    question_number: int = Field(ge=1, le=5)
    paragraph_number: int = Field(ge=1, le=5)
    prompt: str
    options: list[str] = Field(min_length=3, max_length=3)
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str


class ReadingTeil1BeispielAI(BaseModel):
    prompt: str
    options: list[str] = Field(min_length=3, max_length=3)
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str


class ReadingTeil1AIOutput(BaseModel):
    article_title: str
    beispiel: ReadingTeil1BeispielAI
    paragraphs: list[ReadingTeil1ParagraphAI] = Field(min_length=5, max_length=5)
    questions: list[ReadingTeil1QuestionAI] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_one_to_one_mapping(self) -> "ReadingTeil1AIOutput":
        _validate_paragraph_question_mapping(self.paragraphs, self.questions)
        return self


class ReadingTeil2GroupAI(BaseModel):
    floor: str
    items: list[str] = Field(min_length=10, max_length=16)


class ReadingTeil2AufgabeAI(BaseModel):
    aufgabe_number: int = Field(ge=1, le=5)
    prompt: str
    option_a: str
    option_b: str
    # 0 = option_a is the correct floor, 1 = option_b is the correct floor,
    # 2 = neither (the real floor is a different one than both offered -> "Anderer Stock")
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str


class ReadingTeil2BeispielAI(BaseModel):
    prompt: str
    option_a: str
    option_b: str
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str


class ReadingTeil2AIOutput(BaseModel):
    groups: list[ReadingTeil2GroupAI] = Field(min_length=6, max_length=6)
    beispiel: ReadingTeil2BeispielAI
    aufgaben: list[ReadingTeil2AufgabeAI] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_structure(self) -> "ReadingTeil2AIOutput":
        floor_names = [g.floor for g in self.groups]
        if len(set(floor_names)) != 6:
            raise ValueError("groups must have 6 distinct floor names")

        aufgabe_numbers = sorted(a.aufgabe_number for a in self.aufgaben)
        if aufgabe_numbers != [1, 2, 3, 4, 5]:
            raise ValueError("aufgaben must be numbered 1-5 with no duplicates")

        for item in [*self.aufgaben, self.beispiel]:
            if item.option_a == item.option_b:
                raise ValueError("option_a and option_b must be two different floors")
            if item.option_a not in floor_names or item.option_b not in floor_names:
                raise ValueError("option_a and option_b must both be floor names from groups")

        return self


class ReadingTeil3ParagraphAI(BaseModel):
    paragraph_number: int = Field(ge=1, le=5)
    text: str


class ReadingTeil3QuestionAI(BaseModel):
    question_number: int = Field(ge=1, le=5)
    paragraph_number: int = Field(ge=1, le=5)
    prompt: str  # a sentence stem ending in "…", e.g. "Gülcan ist es wichtig …"
    options: list[str] = Field(min_length=3, max_length=3)  # grammatical completions of prompt
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str


class ReadingTeil3BeispielAI(BaseModel):
    prompt: str
    options: list[str] = Field(min_length=3, max_length=3)
    correct_option_index: int = Field(ge=0, le=2)
    explanation: str


class ReadingTeil3AIOutput(BaseModel):
    email_subject: str
    email_sender_name: str
    greeting: str  # salutation line only, e.g. "Liebe Sonja,"
    closing_phrase: str  # sign-off line(s) only, e.g. "Schreib mir bald!\nBis dann"
    beispiel: ReadingTeil3BeispielAI
    paragraphs: list[ReadingTeil3ParagraphAI] = Field(min_length=5, max_length=5)
    questions: list[ReadingTeil3QuestionAI] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_one_to_one_mapping(self) -> "ReadingTeil3AIOutput":
        _validate_paragraph_question_mapping(self.paragraphs, self.questions)
        return self


AD_CODES = ["a", "b", "c", "d", "e", "f"]
NO_MATCH_CODE = "X"


class ReadingTeil4AdAI(BaseModel):
    code: str  # must be one of AD_CODES
    url: str  # e.g. "www.park-cafe.de"
    text: str  # the advertisement body text


class ReadingTeil4AufgabeAI(BaseModel):
    aufgabe_number: int = Field(ge=1, le=5)
    prompt: str
    # One of AD_CODES, or the literal "X" meaning no advertisement matches this Aufgabe.
    correct_ad_code: str
    explanation: str


class ReadingTeil4BeispielAI(BaseModel):
    prompt: str
    correct_ad_code: str  # must be a real ad code - the Beispiel is always solvable
    explanation: str


class ReadingTeil4AIOutput(BaseModel):
    ads: list[ReadingTeil4AdAI] = Field(min_length=6, max_length=6)
    beispiel: ReadingTeil4BeispielAI
    aufgaben: list[ReadingTeil4AufgabeAI] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_structure(self) -> "ReadingTeil4AIOutput":
        codes = [ad.code for ad in self.ads]
        if sorted(codes) != AD_CODES:
            raise ValueError(f"ads must use exactly the codes {AD_CODES}, one each")

        aufgabe_numbers = sorted(a.aufgabe_number for a in self.aufgaben)
        if aufgabe_numbers != [1, 2, 3, 4, 5]:
            raise ValueError("aufgaben must be numbered 1-5 with no duplicates")

        if self.beispiel.correct_ad_code not in codes:
            raise ValueError("beispiel.correct_ad_code must be a real ad code, not X")

        used_codes: list[str] = []
        x_count = 0
        for a in self.aufgaben:
            if a.correct_ad_code == NO_MATCH_CODE:
                x_count += 1
            elif a.correct_ad_code in codes:
                used_codes.append(a.correct_ad_code)
            else:
                raise ValueError(
                    f"aufgabe {a.aufgabe_number} correct_ad_code must be a real ad code or 'X'"
                )

        if x_count != 1:
            raise ValueError("exactly one aufgabe must have correct_ad_code == 'X'")
        if len(set(used_codes)) != len(used_codes):
            raise ValueError("each ad may be the correct answer for at most one aufgabe (no repeats)")
        if self.beispiel.correct_ad_code in used_codes:
            raise ValueError("the ad used by the beispiel must not also answer a real aufgabe")

        return self
