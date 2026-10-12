import { apiClient } from "./client";
import type { Job } from "../types/api";

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

export const jobsApi = {
  getJob: (id: string) => apiClient.get<Job>(`/jobs/${id}`),
};

/** Re-fetch `initial` until `isDone` says it's finished, or give up after a few minutes. */
export async function pollUntil<T>(initial: T, fetchLatest: () => Promise<T>, isDone: (value: T) => boolean): Promise<T> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let current = initial;
  while (!isDone(current)) {
    if (Date.now() > deadline) {
      throw new Error("This is taking longer than expected. Please try again in a moment.");
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    current = await fetchLatest();
  }
  return current;
}

/** Wait for a background job to finish; throws with the job's error message if it failed. */
export async function waitForJob(job: Job): Promise<Job> {
  const finished = await pollUntil(
    job,
    () => jobsApi.getJob(job.id),
    (j) => j.status === "succeeded" || j.status === "failed",
  );
  if (finished.status === "failed") {
    throw new Error(finished.error_message ?? "The job failed.");
  }
  return finished;
}
