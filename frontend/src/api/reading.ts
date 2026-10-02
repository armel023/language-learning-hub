import { apiClient } from "./client";
import type {
  ReadingAttemptResult,
  ReadingAttemptSubmit,
  ReadingExerciseDetail,
  ReadingExerciseGenerateRequest,
  ReadingExerciseSummary,
} from "../types/api";

export const readingApi = {
  listExercises: (teil: number) => apiClient.get<ReadingExerciseSummary[]>(`/reading/exercises?teil=${teil}`),
  getExercise: (id: string) => apiClient.get<ReadingExerciseDetail>(`/reading/exercises/${id}`),
  generateExercise: (payload: ReadingExerciseGenerateRequest) =>
    apiClient.post<ReadingExerciseDetail>("/reading/exercises/generate", payload),
  submitAttempt: (payload: ReadingAttemptSubmit) =>
    apiClient.post<ReadingAttemptResult>("/reading/attempts", payload),
};
