import { apiClient } from "./client";
import { pollUntil, waitForJob } from "./jobs";
import type {
  ExerciseDetail,
  Job,
  ReadingExerciseSummary,
  SchreibenAttempt,
  SchreibenContent,
  SchreibenGenerateRequest,
} from "../types/api";

const getExercise = (id: string) => apiClient.get<ExerciseDetail<SchreibenContent>>(`/schreiben/exercises/${id}`);
const getAttempt = (id: string) => apiClient.get<SchreibenAttempt>(`/schreiben/attempts/${id}`);

export const schreibenApi = {
  listExercises: (teil: number) => apiClient.get<ReadingExerciseSummary[]>(`/schreiben/exercises?teil=${teil}`),
  getExercise,
  generateExercise: async (payload: SchreibenGenerateRequest) => {
    const job = await waitForJob(await apiClient.post<Job>("/schreiben/exercises/generate", payload));
    return getExercise(job.result?.exercise_id as string);
  },
  // Grading runs in the background; resolve once the attempt is graded (or grading failed).
  submitAttempt: async (exerciseId: string, responseText: string) => {
    const attempt = await apiClient.post<SchreibenAttempt>("/schreiben/attempts", {
      exercise_id: exerciseId,
      response_text: responseText,
    });
    return pollUntil(attempt, () => getAttempt(attempt.id), (a) => a.status === "graded" || a.status === "failed");
  },
};
