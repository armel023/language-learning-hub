import { apiClient } from "./client";
import type { StudyOutcome, StudySessionStart, VocabularyItem } from "../types/api";

export const studyApi = {
  startSession: () => apiClient.post<StudySessionStart>("/study/sessions"),
  recordReview: (vocabularyId: string, outcome: StudyOutcome) =>
    apiClient.post<VocabularyItem>("/study/reviews", { vocabulary_id: vocabularyId, outcome }),
};
