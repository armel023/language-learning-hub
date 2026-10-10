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

export interface ExtractedVocabCandidate extends ExtractedVocabEntry {
  /** Set by the backend when the user already has a card for this word + part of speech. */
  already_in_cards?: boolean;
}

export type ExtractionStatus = "pending" | "processing" | "completed" | "failed";
export type VocabFileType = "pdf" | "docx" | "txt";

export interface VocabExtractionJob {
  id: string;
  original_filename: string;
  file_type: VocabFileType;
  status: ExtractionStatus;
  raw_ai_output: { entries: ExtractedVocabCandidate[] } | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  confirmed_at: string | null;
}

export type JobStatus = "pending" | "running" | "succeeded" | "failed";

export interface Job {
  id: string;
  kind: string;
  status: JobStatus;
  result: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
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

export interface SchreibenContent {
  title: string;
  situation: string;
  recipient: string;
  formality: "informal" | "formal";
  content_points: string[];
  word_range: [number, number];
  max_score: number;
}

export interface SchreibenGenerateRequest {
  teil: 1 | 2;
  topic?: string;
  level?: string;
}

export interface SchreibenCriterion {
  score: number;
  comment: string;
}

export interface SchreibenAttempt {
  id: string;
  exercise_id: string;
  status: "submitted" | "grading" | "graded" | "failed";
  response_text: string | null;
  score: number | null;
  max_score: number;
  rubric_scores: {
    content_points: (SchreibenCriterion & { point_number: number })[];
    communication: SchreibenCriterion;
    accuracy: SchreibenCriterion;
  } | null;
  feedback: {
    summary?: string;
    corrections?: { original: string; corrected: string; explanation: string }[];
    improved_version?: string;
    word_count?: number;
    word_range?: [number, number];
    error?: string;
  } | null;
  submitted_at: string | null;
}

/** Same shape as ReadingExerciseDetail for any skill, with a typed `content`. */
export type ExerciseDetail<TContent> = Omit<ReadingExerciseDetail, "content"> & { content: TContent };

export interface ScriptLine {
  speaker: string;
  gender: "female" | "male";
  text: string;
}

export interface AudioRef {
  url: string;
  duration_s: number;
}

export interface IconPicture {
  emoji: string;
  caption: string;
}

export interface HoerenTeil1Content {
  plays: number;
  items: { item_number: number; context: string; prompt: string; options: string[]; audio: AudioRef }[];
}

export interface HoerenTeil2Content {
  plays: number;
  context: string;
  audio: AudioRef;
  beispiel: { label: string; correct_code: string; explanation: string };
  pictures: (IconPicture & { code: string })[];
  aufgaben: { aufgabe_number: number; label: string }[];
}

export interface HoerenTeil3Content {
  plays: number;
  items: { item_number: number; context: string; prompt: string; options: IconPicture[]; audio: AudioRef }[];
}

export interface HoerenTeil4Content {
  plays: number;
  context: string;
  audio: AudioRef;
  statements: { number: number; statement: string }[];
}

export interface HoerenVocabEntry extends ExtractedVocabEntry {
  already_in_cards: boolean;
}

export interface HoerenAttemptResult extends ReadingAttemptResult {
  /** Keyed like the questions ("1".."5", "11".."15") or "all" for Teil 2 and 4. */
  transcripts: Record<string, ScriptLine[]>;
  vocabulary: HoerenVocabEntry[];
}
