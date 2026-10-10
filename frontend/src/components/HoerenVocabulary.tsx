import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import CheckIcon from "@mui/icons-material/Check";
import { Alert, Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";

import { describeError } from "../api/client";
import { flashcardsApi } from "../api/flashcards";
import type { HoerenAttemptResult, HoerenVocabEntry } from "../types/api";

/** Key words from the recordings, each addable to the flashcards with one tap. */
export function HoerenVocabulary({ result }: { result: HoerenAttemptResult }) {
  const queryClient = useQueryClient();
  const [added, setAdded] = useState<Record<string, boolean>>({});
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!result.vocabulary?.length) return null;

  async function add(entry: HoerenVocabEntry) {
    setPending(entry.word);
    setError(null);
    try {
      const { already_in_cards: _ignored, ...card } = entry;
      await flashcardsApi.create(card);
      setAdded((prev) => ({ ...prev, [entry.word]: true }));
      queryClient.invalidateQueries({ queryKey: ["vocabulary"] });
    } catch (e) {
      setError(describeError(e, `Could not add "${entry.word}".`));
    } finally {
      setPending(null);
    }
  }

  return (
    <Card variant="outlined" sx={{ mt: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Wortschatz aus dem Hörtext
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 1 }}>
            {error}
          </Alert>
        )}
        <Stack spacing={1}>
          {result.vocabulary.map((entry) => {
            const inCards = entry.already_in_cards || added[entry.word];
            return (
              <Stack key={entry.word} direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                <Box sx={{ minWidth: 0 }}>
                  <Typography fontWeight="bold" sx={{ overflowWrap: "anywhere" }}>
                    {entry.article ? `${entry.article} ` : ""}
                    {entry.word}
                    {entry.plural_form ? `, ${entry.plural_form}` : ""}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {entry.translation}
                  </Typography>
                </Box>
                <Button
                  size="small"
                  variant={inCards ? "text" : "outlined"}
                  startIcon={inCards ? <CheckIcon /> : <AddIcon />}
                  disabled={inCards || pending === entry.word}
                  onClick={() => add(entry)}
                  sx={{ flexShrink: 0 }}
                >
                  {inCards ? "In cards" : "Add"}
                </Button>
              </Stack>
            );
          })}
        </Stack>
      </CardContent>
    </Card>
  );
}
