import { apiClient } from "./client";
import { pollUntil, waitForJob } from "./jobs";
import type {
  ExerciseDetail,
  Job,
  ReadingExerciseSummary,
  SprechenAttempt,
  SprechenContent,
  SprechenGenerateRequest,
} from "../types/api";

const getExercise = (id: string) => apiClient.get<ExerciseDetail<SprechenContent>>(`/sprechen/exercises/${id}`);
const getAttempt = (id: string) => apiClient.get<SprechenAttempt>(`/sprechen/attempts/${id}`);

export const sprechenApi = {
  listExercises: (teil: number) => apiClient.get<ReadingExerciseSummary[]>(`/sprechen/exercises?teil=${teil}`),
  getExercise,
  generateExercise: async (payload: SprechenGenerateRequest) => {
    const job = await waitForJob(await apiClient.post<Job>("/sprechen/exercises/generate", payload));
    return getExercise(job.result?.exercise_id as string);
  },
  /** Feedback is generated in the background after the conversation; resolve once it is ready. */
  waitForFeedback: async (attemptId: string) =>
    pollUntil(await getAttempt(attemptId), () => getAttempt(attemptId), (a) => a.status === "graded" || a.status === "failed"),
};

/** WebSocket URL for the live conversation, on the page's own origin (works behind nginx/Tailscale). */
export function liveSessionUrl(exerciseId: string): string {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/api/v1/sprechen/live/${exerciseId}`;
}
