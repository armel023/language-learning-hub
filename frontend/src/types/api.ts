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

export type ExerciseType = "lesen_teil1" | "lesen_teil2" | "lesen_teil3" | "lesen_teil4";

export interface ReadingExerciseSummary {
  id: string;
  exercise_type: ExerciseType;
  title: string;
  level: string;
  topic: string | null;
  created_at: string;
}

export interface ReadingTeil1Paragraph {
  paragraph_number: number;
  text: string;
}

export interface ReadingTeil1Question {
  question_number: number;
  paragraph_number: number;
  prompt: string;
  options: string[];
}

export interface ReadingTeil1Beispiel {
  prompt: string;
  options: string[];
  correct_option_index: number;
  explanation: string;
}

export interface ReadingTeil1Content {
  article_title: string;
  beispiel: ReadingTeil1Beispiel;
  paragraphs: ReadingTeil1Paragraph[];
  questions: ReadingTeil1Question[];
}

export interface ReadingTeil2Group {
  floor: string;
  items: string[];
}

export interface ReadingTeil2Aufgabe {
  aufgabe_number: number;
  prompt: string;
  options: string[];
}

export interface ReadingTeil2Beispiel {
  prompt: string;
  options: string[];
  correct_option_index: number;
  explanation: string;
}

export interface ReadingTeil2Content {
  groups: ReadingTeil2Group[];
  beispiel: ReadingTeil2Beispiel;
  aufgaben: ReadingTeil2Aufgabe[];
}

export interface ReadingTeil3Content {
  email_subject: string;
  email_sender_name: string;
  greeting: string;
  closing_phrase: string;
  beispiel: ReadingTeil1Beispiel;
  paragraphs: ReadingTeil1Paragraph[];
  questions: ReadingTeil1Question[];
}

export interface ReadingTeil4Ad {
  code: string;
  url: string;
  text: string;
}

export interface ReadingTeil4Aufgabe {
  aufgabe_number: number;
  prompt: string;
}

export interface ReadingTeil4Beispiel {
  prompt: string;
  correct_ad_code: string;
  explanation: string;
}

export interface ReadingTeil4Content {
  ads: ReadingTeil4Ad[];
  beispiel: ReadingTeil4Beispiel;
  aufgaben: ReadingTeil4Aufgabe[];
}

export interface ReadingExerciseDetail {
  id: string;
  exercise_type: ExerciseType;
  title: string;
  level: string;
  topic: string | null;
  content: ReadingTeil1Content | ReadingTeil2Content | ReadingTeil3Content | ReadingTeil4Content;
  created_at: string;
}

export interface ReadingExerciseGenerateRequest {
  teil: 1 | 2 | 3 | 4;
  topic?: string | null;
  level?: string;
}

export interface ReadingAttemptSubmit {
  exercise_id: string;
  answers: Record<string, number | string>;
}

export interface ReadingAttemptResult {
  id: string;
  exercise_id: string;
  score: number;
  max_score: number;
  is_correct_per_question: Record<string, boolean>;
  correct_answers: Record<string, number | string>;
  explanations: Record<string, string>;
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
