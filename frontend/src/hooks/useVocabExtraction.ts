import { useMutation, useQueryClient } from "@tanstack/react-query";

import { vocabExtractionApi } from "../api/vocabExtraction";
import type { ExtractedVocabEntry } from "../types/api";

export function useUploadFile() {
  return useMutation({
    mutationFn: (file: File) => vocabExtractionApi.upload(file),
  });
}

export function useConfirmExtraction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, entries }: { jobId: string; entries: ExtractedVocabEntry[] }) =>
      vocabExtractionApi.confirm(jobId, entries),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
  });
}
