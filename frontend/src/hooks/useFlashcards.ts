import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { decksApi, flashcardsApi, type ListVocabularyParams } from "../api/flashcards";
import type { DeckCreate, VocabularyItemCreate } from "../types/api";

export function useVocabularyList(params: ListVocabularyParams) {
  return useQuery({
    queryKey: ["vocabulary", params],
    queryFn: () => flashcardsApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useDecks() {
  return useQuery({ queryKey: ["decks"], queryFn: decksApi.list });
}

export function useCreateVocabulary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: VocabularyItemCreate) => flashcardsApi.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
  });
}

export function useDeleteVocabulary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => flashcardsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
  });
}

export function useCreateDeck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DeckCreate) => decksApi.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["decks"] }),
  });
}
