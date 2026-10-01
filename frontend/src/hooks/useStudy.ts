import { useMutation, useQueryClient } from "@tanstack/react-query";

import { studyApi } from "../api/study";
import type { StudyOutcome } from "../types/api";

export function useStartStudySession() {
  return useMutation({ mutationFn: studyApi.startSession });
}

export function useRecordStudyReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ vocabularyId, outcome }: { vocabularyId: string; outcome: StudyOutcome }) =>
      studyApi.recordReview(vocabularyId, outcome),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
  });
}
