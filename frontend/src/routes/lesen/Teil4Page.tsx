import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { readingApi } from "../../api/reading";
import { useGenerateReadingExercise, useReadingExercises, useSubmitReadingAttempt } from "../../hooks/useReading";
import type { ReadingAttemptResult, ReadingExerciseDetail, ReadingTeil4Content } from "../../types/api";

export function Teil4Page() {
  const { data: previousExercises, isLoading: isLoadingList } = useReadingExercises(4);
  const generateExercise = useGenerateReadingExercise();
  const submitAttempt = useSubmitReadingAttempt();

  const [theme, setTheme] = useState("");
  const [exercise, setExercise] = useState<ReadingExerciseDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ReadingAttemptResult | null>(null);

  function startExercise(ex: ReadingExerciseDetail) {
    setExercise(ex);
    setAnswers({});
    setResult(null);
  }

  function handleGenerate() {
    generateExercise.mutate(
      { teil: 4, topic: theme || undefined, level: "A2" },
      { onSuccess: (ex) => startExercise(ex) },
    );
  }

  function handleSubmit() {
    if (!exercise) return;
    submitAttempt.mutate(
      { exercise_id: exercise.id, answers },
      { onSuccess: (res) => setResult(res) },
    );
  }

  if (!exercise) {
    return (
      <Box maxWidth={820}>
        <Typography variant="h4" gutterBottom>
          Lesen - Teil 4
        </Typography>
        <Typography color="text.secondary" mb={3}>
          6 advertisements are shown. Match each of the 5 situations to the one ad that actually
          fits it - or "X" if none of them do.
        </Typography>

        <Stack direction="row" spacing={2} mb={4} alignItems="flex-start">
          <TextField
            label="Theme (optional)"
            placeholder="e.g. Restaurants, Wohnungen, Sprachschulen"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            size="small"
          />
          <Button variant="contained" onClick={handleGenerate} disabled={generateExercise.isPending}>
            {generateExercise.isPending ? "Generating..." : "Generate new exercise"}
          </Button>
        </Stack>
        {generateExercise.isError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            Failed to generate an exercise. Please try again.
          </Alert>
        )}

        <Typography variant="h6" gutterBottom>
          Or practice a previous exercise
        </Typography>
        {isLoadingList && <CircularProgress size={24} />}
        {previousExercises && previousExercises.length === 0 && (
          <Typography color="text.secondary">No exercises generated yet.</Typography>
        )}
        <Stack spacing={1}>
          {previousExercises?.map((ex) => (
            <Card key={ex.id} variant="outlined">
              <CardActionArea
                onClick={async () => {
                  const full = await readingApi.getExercise(ex.id);
                  startExercise(full);
                }}
              >
                <CardContent>
                  <Typography variant="subtitle1">{ex.title}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(ex.created_at).toLocaleString()}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      </Box>
    );
  }

  const content = exercise.content as ReadingTeil4Content;
  const allAnswered = content.aufgaben.every((a) => answers[String(a.aufgabe_number)] !== undefined);
  const adByCode = Object.fromEntries(content.ads.map((ad) => [ad.code, ad]));

  return (
    <Box maxWidth={820}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{exercise.title}</Typography>
        <Button component={RouterLink} to="/lesen" variant="text">
          Back to Lesen
        </Button>
      </Stack>

      {result && (
        <Alert severity={result.score === result.max_score ? "success" : "info"} sx={{ mb: 3 }}>
          Score: {result.score} / {result.max_score}
        </Alert>
      )}

      <Typography variant="overline" color="text.secondary">
        Anzeigen
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3, mt: 0 }}>
        {[...content.ads]
          .sort((a, b) => a.code.localeCompare(b.code))
          .map((ad) => (
            <Grid item xs={12} sm={6} key={ad.code}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <Chip label={ad.code} size="small" />
                    <Box
                      sx={{
                        border: "1px solid",
                        borderColor: "divider",
                        borderRadius: 1,
                        px: 1,
                        py: 0.25,
                        flexGrow: 1,
                        bgcolor: "action.hover",
                      }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        {ad.url}
                      </Typography>
                    </Box>
                  </Stack>
                  <Typography variant="body2">{ad.text}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
      </Grid>

      <Card variant="outlined" sx={{ mb: 3, bgcolor: "action.hover" }}>
        <CardContent>
          <Chip size="small" label="Beispiel (solved example)" sx={{ mb: 1 }} />
          <Typography fontWeight="bold" gutterBottom>
            {content.beispiel.prompt}
          </Typography>
          <Typography color="success.main" fontWeight="bold">
            ✓ {content.beispiel.correct_ad_code} ({adByCode[content.beispiel.correct_ad_code]?.url})
          </Typography>
          <Typography variant="body2" color="text.secondary" fontStyle="italic" mt={1}>
            {content.beispiel.explanation}
          </Typography>
        </CardContent>
      </Card>

      <Divider sx={{ mb: 3 }} />

      <Stack spacing={3}>
        {[...content.aufgaben]
          .sort((a, b) => a.aufgabe_number - b.aufgabe_number)
          .map((aufgabe) => {
            const aKey = String(aufgabe.aufgabe_number);
            const isCorrect = result?.is_correct_per_question[aKey];
            const correctCode = result?.correct_answers[aKey];

            return (
              <Card key={aufgabe.aufgabe_number} variant="outlined">
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <Typography fontWeight="bold" sx={{ flexGrow: 1 }}>
                      {aufgabe.aufgabe_number}. {aufgabe.prompt}
                    </Typography>
                    {result && (isCorrect ? <CheckCircleIcon color="success" /> : <CancelIcon color="error" />)}
                  </Stack>

                  <Select
                    size="small"
                    displayEmpty
                    value={answers[aKey] ?? ""}
                    disabled={!!result}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [aKey]: e.target.value }))}
                    sx={{ minWidth: 220 }}
                  >
                    <MenuItem value="" disabled>
                      Wählen...
                    </MenuItem>
                    {content.ads.map((ad) => (
                      <MenuItem key={ad.code} value={ad.code}>
                        {ad.code} - {ad.url}
                      </MenuItem>
                    ))}
                    <MenuItem value="X">X - Keine passende Anzeige</MenuItem>
                  </Select>

                  {result && !isCorrect && (
                    <Typography color="success.main" fontWeight="bold" mt={1}>
                      Richtige Antwort: {correctCode}
                      {correctCode !== "X" ? ` (${adByCode[String(correctCode)]?.url})` : ""}
                    </Typography>
                  )}

                  {result && (
                    <Typography variant="body2" color="text.secondary" fontStyle="italic" mt={1}>
                      {result.explanations[aKey]}
                    </Typography>
                  )}
                </CardContent>
              </Card>
            );
          })}
      </Stack>

      <Stack direction="row" spacing={2} mt={3}>
        {!result ? (
          <Button
            variant="contained"
            size="large"
            disabled={!allAnswered || submitAttempt.isPending}
            onClick={handleSubmit}
          >
            {submitAttempt.isPending ? "Submitting..." : "Submit answers"}
          </Button>
        ) : (
          <Button variant="contained" onClick={() => setExercise(null)}>
            Try another exercise
          </Button>
        )}
      </Stack>

      {submitAttempt.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Failed to submit your answers. Please try again.
        </Alert>
      )}
    </Box>
  );
}
