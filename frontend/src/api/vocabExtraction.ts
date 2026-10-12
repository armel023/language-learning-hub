import { apiClient } from "./client";
import { pollUntil } from "./jobs";
import type { ExtractedVocabEntry, VocabExtractionJob, VocabularyItem } from "../types/api";

export const vocabExtractionApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    // Extraction runs in the background; resolve with the finished (completed or failed) job.
    return apiClient
      .postForm<VocabExtractionJob>("/vocab-extraction/upload", formData)
      .then((job) =>
        pollUntil(job, () => vocabExtractionApi.getJob(job.id), (j) => j.status === "completed" || j.status === "failed"),
      );
  },
  getJob: (jobId: string) => apiClient.get<VocabExtractionJob>(`/vocab-extraction/${jobId}`),
  confirm: (jobId: string, entries: ExtractedVocabEntry[], deckId?: string | null) =>
    apiClient.post<VocabularyItem[]>(`/vocab-extraction/${jobId}/confirm`, {
      entries,
      deck_id: deckId ?? null,
    }),
};
