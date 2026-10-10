import { apiClient } from "./client";
import { waitForJob } from "./jobs";
import type { ExerciseApi } from "../components/ExerciseShell";
import type {
  HoerenAttemptResult,
  Job,
  ReadingAttemptSubmit,
  ReadingExerciseDetail,
  ReadingExerciseGenerateRequest,
  ReadingExerciseSummary,
} from "../types/api";

const getExercise = (id: string) => apiClient.get<ReadingExerciseDetail>(`/hoeren/exercises/${id}`);

export const hoerenApi: ExerciseApi<HoerenAttemptResult> = {
  listExercises: (teil) => apiClient.get<ReadingExerciseSummary[]>(`/hoeren/exercises?teil=${teil}`),
  getExercise,
  // Script generation, checking and audio synthesis run as one background job.
  generateExercise: async (payload: ReadingExerciseGenerateRequest) => {
    const job = await waitForJob(await apiClient.post<Job>("/hoeren/exercises/generate", payload));
    return getExercise(job.result?.exercise_id as string);
  },
  submitAttempt: (payload: ReadingAttemptSubmit) => apiClient.post<HoerenAttemptResult>("/hoeren/attempts", payload),
};
