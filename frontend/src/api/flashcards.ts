import { apiClient } from "./client";
import type {
  Deck,
  DeckCreate,
  VocabularyItem,
  VocabularyItemCreate,
  VocabularyListResponse,
} from "../types/api";

export interface ListVocabularyParams {
  search?: string;
  page: number;
  pageSize: number;
}

export const flashcardsApi = {
  list: ({ search, page, pageSize }: ListVocabularyParams) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    return apiClient.get<VocabularyListResponse>(`/vocabulary?${params.toString()}`);
  },
  create: (payload: VocabularyItemCreate) => apiClient.post<VocabularyItem>("/vocabulary", payload),
  delete: (id: string) => apiClient.delete<void>(`/vocabulary/${id}`),
};

export const decksApi = {
  list: () => apiClient.get<Deck[]>("/decks"),
  create: (payload: DeckCreate) => apiClient.post<Deck>("/decks", payload),
};
