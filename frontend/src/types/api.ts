export type PartOfSpeech = "noun" | "verb" | "adjective" | "adverb" | "phrase" | "other";
export type Article = "der" | "die" | "das";
export type VocabSource = "manual" | "ai_extracted";

export interface VocabularyItem {
  id: string;
  word: string;
  part_of_speech: PartOfSpeech;
  article: Article | null;
  plural_form: string | null;
  translation: string;
  example_sentence_de: string | null;
  example_sentence_translation: string | null;
  notes: string | null;
  deck_id: string | null;
  source: VocabSource;
  source_file_name: string | null;
  review_count: number;
  correct_count: number;
  incorrect_hard_count: number;
  incorrect_moderate_count: number;
  last_reviewed_at: string | null;
  study_due_at_session: number | null;
  created_at: string;
  updated_at: string;
}

export interface VocabularyListResponse {
  items: VocabularyItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface VocabularyItemCreate {
  word: string;
  part_of_speech: PartOfSpeech;
  article?: Article | null;
  plural_form?: string | null;
  translation: string;
  example_sentence_de?: string | null;
  example_sentence_translation?: string | null;
  notes?: string | null;
  deck_id?: string | null;
}

export interface ExtractedVocabEntry {
  word: string;
  part_of_speech: PartOfSpeech;
  article: Article | null;
  plural_form: string | null;
  translation: string;
  example_sentence_de: string | null;
  example_sentence_translation: string | null;
}

export type ExtractionStatus = "pending" | "processing" | "completed" | "failed";
export type VocabFileType = "pdf" | "docx" | "txt";

export interface VocabExtractionJob {
  id: string;
  original_filename: string;
  file_type: VocabFileType;
  status: ExtractionStatus;
  raw_ai_output: { entries: ExtractedVocabEntry[] } | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export type StudyOutcome = "correct" | "incorrect_hard" | "incorrect_moderate";

export interface StudySessionStart {
  session_number: number;
  words: VocabularyItem[];
}

export interface Deck {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface DeckCreate {
  name: string;
  description?: string | null;
}
