import { apiClient } from "./client";
import type { ExtractedVocabEntry, VocabExtractionJob, VocabularyItem } from "../types/api";

export const vocabExtractionApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.postForm<VocabExtractionJob>("/vocab-extraction/upload", formData);
  },
  getJob: (jobId: string) => apiClient.get<VocabExtractionJob>(`/vocab-extraction/${jobId}`),
  confirm: (jobId: string, entries: ExtractedVocabEntry[], deckId?: string | null) =>
    apiClient.post<VocabularyItem[]>(`/vocab-extraction/${jobId}/confirm`, {
      entries,
      deck_id: deckId ?? null,
    }),
};
