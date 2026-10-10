import { useMutation, useQuery } from "@tanstack/react-query";

import { schreibenApi } from "../api/schreiben";
import type { SchreibenGenerateRequest } from "../types/api";

export function useSchreibenExercises(teil: number) {
  return useQuery({
    queryKey: ["schreiben-exercises", teil],
    queryFn: () => schreibenApi.listExercises(teil),
  });
}

export function useGenerateSchreibenExercise() {
  return useMutation({
    mutationFn: (payload: SchreibenGenerateRequest) => schreibenApi.generateExercise(payload),
  });
}

export function useSubmitSchreibenAttempt() {
  return useMutation({
    mutationFn: ({ exerciseId, responseText }: { exerciseId: string; responseText: string }) =>
      schreibenApi.submitAttempt(exerciseId, responseText),
  });
}
