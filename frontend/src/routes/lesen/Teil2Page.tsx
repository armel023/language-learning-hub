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
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { readingApi } from "../../api/reading";
import { useGenerateReadingExercise, useReadingExercises, useSubmitReadingAttempt } from "../../hooks/useReading";
import type { ReadingAttemptResult, ReadingExerciseDetail, ReadingTeil2Content } from "../../types/api";

export function Teil2Page() {
  const { data: previousExercises, isLoading: isLoadingList } = useReadingExercises(2);
  const generateExercise = useGenerateReadingExercise();
  const submitAttempt = useSubmitReadingAttempt();

  const [storeType, setStoreType] = useState("");
  const [exercise, setExercise] = useState<ReadingExerciseDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<ReadingAttemptResult | null>(null);

  function startExercise(ex: ReadingExerciseDetail) {
    setExercise(ex);
    setAnswers({});
    setResult(null);
  }

  function handleGenerate() {
    generateExercise.mutate(
      { teil: 2, topic: storeType || undefined, level: "A2" },
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
      <Box maxWidth={720}>
        <Typography variant="h4" gutterBottom>
          Lesen - Teil 2
        </Typography>
        <Typography color="text.secondary" mb={3}>
          A department store's floor directory is shown. For each situation, pick which floor it
          belongs to - or "Anderer Stock" if it's neither of the two offered.
        </Typography>

        <Stack direction="row" spacing={2} mb={4} alignItems="flex-start">
          <TextField
            label="Store type (optional)"
            placeholder="e.g. Kaufhaus, Baumarkt, Möbelhaus"
            value={storeType}
            onChange={(e) => setStoreType(e.target.value)}
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

  const content = exercise.content as ReadingTeil2Content;
  const allAnswered = content.aufgaben.every((a) => answers[String(a.aufgabe_number)] !== undefined);

  return (
    <Box maxWidth={720}>
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

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="overline" color="text.secondary">
            Stockverzeichnis (floor directory)
          </Typography>
          <Stack spacing={1} mt={1}>
            {content.groups.map((group) => (
              <Box key={group.floor}>
                <Typography component="span" fontWeight="bold">
                  {group.floor}:{" "}
                </Typography>
                <Typography component="span" color="text.secondary">
                  {group.items.join(", ")}
                </Typography>
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 3, bgcolor: "action.hover" }}>
        <CardContent>
          <Chip size="small" label="Beispiel (solved example)" sx={{ mb: 1 }} />
          <Typography fontWeight="bold" gutterBottom>
            {content.beispiel.prompt}
          </Typography>
          <Stack spacing={0.5}>
            {content.beispiel.options.map((option, idx) => (
              <Typography
                key={idx}
                color={idx === content.beispiel.correct_option_index ? "success.main" : "text.secondary"}
                fontWeight={idx === content.beispiel.correct_option_index ? "bold" : "normal"}
              >
                {idx === content.beispiel.correct_option_index ? "✓ " : ""}
                {option}
              </Typography>
            ))}
          </Stack>
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
            const correctIndex = result?.correct_answers[aKey];

            return (
              <Card key={aufgabe.aufgabe_number} variant="outlined">
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <Typography fontWeight="bold">
                      {aufgabe.aufgabe_number}. {aufgabe.prompt}
                    </Typography>
                    {result && (isCorrect ? <CheckCircleIcon color="success" /> : <CancelIcon color="error" />)}
                  </Stack>

                  <FormControl disabled={!!result}>
                    <RadioGroup
                      value={answers[aKey] ?? ""}
                      onChange={(e) => setAnswers((prev) => ({ ...prev, [aKey]: Number(e.target.value) }))}
                    >
                      {aufgabe.options.map((option, idx) => (
                        <FormControlLabel
                          key={idx}
                          value={idx}
                          control={<Radio />}
                          label={option}
                          sx={
                            result && idx === correctIndex
                              ? { color: "success.main", fontWeight: "bold" }
                              : undefined
                          }
                        />
                      ))}
                    </RadioGroup>
                  </FormControl>

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
