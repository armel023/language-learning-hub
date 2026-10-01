import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { useCreateVocabulary } from "../../hooks/useFlashcards";
import type { Article, PartOfSpeech, VocabularyItemCreate } from "../../types/api";

const PARTS_OF_SPEECH: PartOfSpeech[] = ["noun", "verb", "adjective", "adverb", "phrase", "other"];
const ARTICLES: Article[] = ["der", "die", "das"];

export function FlashcardAddPage() {
  const navigate = useNavigate();
  const createVocabulary = useCreateVocabulary();

  const [form, setForm] = useState<VocabularyItemCreate>({
    word: "",
    part_of_speech: "noun",
    article: null,
    translation: "",
    example_sentence_de: "",
    notes: "",
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createVocabulary.mutate(
      {
        ...form,
        article: form.part_of_speech === "noun" ? form.article : null,
      },
      { onSuccess: () => navigate("/flashcards") },
    );
  }

  return (
    <Box maxWidth={480}>
      <Typography variant="h4" mb={3}>
        Add vocabulary
      </Typography>
      <Box component="form" onSubmit={handleSubmit}>
        <Stack spacing={2}>
          <TextField
            label="Word"
            required
            value={form.word}
            onChange={(e) => setForm({ ...form, word: e.target.value })}
          />

          <TextField
            select
            label="Part of speech"
            value={form.part_of_speech}
            onChange={(e) => setForm({ ...form, part_of_speech: e.target.value as PartOfSpeech })}
          >
            {PARTS_OF_SPEECH.map((pos) => (
              <MenuItem key={pos} value={pos}>
                {pos}
              </MenuItem>
            ))}
          </TextField>

          {form.part_of_speech === "noun" && (
            <TextField
              select
              label="Article"
              value={form.article ?? ""}
              onChange={(e) =>
                setForm({ ...form, article: (e.target.value || null) as Article | null })
              }
            >
              <MenuItem value="">-</MenuItem>
              {ARTICLES.map((article) => (
                <MenuItem key={article} value={article}>
                  {article}
                </MenuItem>
              ))}
            </TextField>
          )}

          <TextField
            label="Plural form"
            value={form.plural_form ?? ""}
            onChange={(e) => setForm({ ...form, plural_form: e.target.value || null })}
          />

          <TextField
            label="Translation"
            required
            value={form.translation}
            onChange={(e) => setForm({ ...form, translation: e.target.value })}
          />

          <TextField
            label="Example sentence (German)"
            multiline
            minRows={2}
            value={form.example_sentence_de ?? ""}
            onChange={(e) => setForm({ ...form, example_sentence_de: e.target.value || null })}
          />

          <TextField
            label="Notes"
            multiline
            minRows={2}
            value={form.notes ?? ""}
            onChange={(e) => setForm({ ...form, notes: e.target.value || null })}
          />

          <Button type="submit" variant="contained" disabled={createVocabulary.isPending}>
            {createVocabulary.isPending ? "Saving..." : "Save"}
          </Button>

          {createVocabulary.isError && <Alert severity="error">Failed to save. Please try again.</Alert>}
        </Stack>
      </Box>
    </Box>
  );
}
