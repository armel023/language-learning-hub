import { apiClient } from "./client";
import { waitForJob } from "./jobs";
import type {
  Job,
  ReadingAttemptResult,
  ReadingAttemptSubmit,
  ReadingExerciseDetail,
  ReadingExerciseGenerateRequest,
  ReadingExerciseSummary,
} from "../types/api";

const getExercise = (id: string) => apiClient.get<ReadingExerciseDetail>(`/reading/exercises/${id}`);

export const readingApi = {
  listExercises: (teil: number) => apiClient.get<ReadingExerciseSummary[]>(`/reading/exercises?teil=${teil}`),
  getExercise,
  // Generation runs as a background job; resolve once the exercise exists so callers are unchanged.
  generateExercise: async (payload: ReadingExerciseGenerateRequest) => {
    const job = await waitForJob(await apiClient.post<Job>("/reading/exercises/generate", payload));
    return getExercise(job.result?.exercise_id as string);
  },
  submitAttempt: (payload: ReadingAttemptSubmit) =>
    apiClient.post<ReadingAttemptResult>("/reading/attempts", payload),
};
