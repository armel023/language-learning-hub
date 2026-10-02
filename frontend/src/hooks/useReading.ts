import { useMutation, useQuery } from "@tanstack/react-query";

import { readingApi } from "../api/reading";
import type { ReadingExerciseGenerateRequest } from "../types/api";

export function useReadingExercises(teil: number) {
  return useQuery({
    queryKey: ["reading-exercises", teil],
    queryFn: () => readingApi.listExercises(teil),
  });
}

export function useReadingExercise(id: string | null) {
  return useQuery({
    queryKey: ["reading-exercise", id],
    queryFn: () => readingApi.getExercise(id as string),
    enabled: id !== null,
  });
}

export function useGenerateReadingExercise() {
  return useMutation({
    mutationFn: (payload: ReadingExerciseGenerateRequest) => readingApi.generateExercise(payload),
  });
}

export function useSubmitReadingAttempt() {
  return useMutation({
    mutationFn: readingApi.submitAttempt,
  });
}
