import { useState, type ComponentType, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { describeError } from "../api/client";
import { readingApi } from "../api/reading";
import type {
  ReadingAttemptResult,
  ReadingAttemptSubmit,
  ReadingExerciseDetail,
  ReadingExerciseGenerateRequest,
  ReadingExerciseSummary,
} from "../types/api";

/** The endpoints a skill with objectively scored Teile provides (Lesen, Hören). */
export interface ExerciseApi<TResult extends ReadingAttemptResult> {
  listExercises: (teil: number) => Promise<ReadingExerciseSummary[]>;
  getExercise: (id: string) => Promise<ReadingExerciseDetail>;
  generateExercise: (payload: ReadingExerciseGenerateRequest) => Promise<ReadingExerciseDetail>;
  submitAttempt: (payload: ReadingAttemptSubmit) => Promise<TResult>;
}

export interface ExerciseBodyProps<TContent, TAnswer, TResult extends ReadingAttemptResult = ReadingAttemptResult> {
  content: TContent;
  answers: Record<string, TAnswer>;
  setAnswer: (key: string, value: TAnswer) => void;
  /** Set once the attempt is submitted; bodies use it to show corrections and lock inputs. */
  result: TResult | null;
}

interface ExerciseShellProps<TContent, TAnswer, TResult extends ReadingAttemptResult> {
  teil: ReadingExerciseGenerateRequest["teil"];
  description: ReactNode;
  topicLabel: string;
  topicPlaceholder: string;
  maxWidth?: number;
  isComplete: (content: TContent, answers: Record<string, TAnswer>) => boolean;
  Body: ComponentType<ExerciseBodyProps<TContent, TAnswer, TResult>>;
  /** Defaults to Lesen. */
  api?: ExerciseApi<TResult>;
  skillLabel?: string;
  basePath?: string;
  generatingLabel?: string;
  /** Extra panel under a submitted exercise, e.g. Hören's vocabulary list. */
  ResultExtras?: ComponentType<{ result: TResult }>;
}

/**
 * Everything a Lesen or Hören Teil page shares: picking or generating an exercise, the header and
 * score, submitting, and error handling. Each Teil only supplies how its exercise body renders.
 */
export function ExerciseShell<
  TContent,
  TAnswer extends string | number,
  TResult extends ReadingAttemptResult = ReadingAttemptResult,
>({
  teil,
  description,
  topicLabel,
  topicPlaceholder,
  maxWidth = 720,
  isComplete,
  Body,
  api = readingApi as unknown as ExerciseApi<TResult>,
  skillLabel = "Lesen",
  basePath = "/lesen",
  generatingLabel = "Generating and checking...",
  ResultExtras,
}: ExerciseShellProps<TContent, TAnswer, TResult>) {
  const { data: previousExercises, isLoading: isLoadingList } = useQuery({
    queryKey: [basePath, "exercises", teil],
    queryFn: () => api.listExercises(teil),
  });
  const generateExercise = useMutation({ mutationFn: api.generateExercise });
  const submitAttempt = useMutation({ mutationFn: api.submitAttempt });

  const [topic, setTopic] = useState("");
  const [exercise, setExercise] = useState<ReadingExerciseDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, TAnswer>>({});
  const [result, setResult] = useState<TResult | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  function startExercise(ex: ReadingExerciseDetail) {
    setExercise(ex);
    setAnswers({});
    setResult(null);
  }

  function handleGenerate() {
    generateExercise.mutate(
      { teil, topic: topic || undefined, level: "A2" },
      { onSuccess: (ex) => startExercise(ex) },
    );
  }

  async function openPrevious(id: string) {
    setOpenError(null);
    try {
      startExercise(await api.getExercise(id));
    } catch (error) {
      setOpenError(describeError(error, "Could not open that exercise."));
    }
  }

  function handleSubmit() {
    if (!exercise) return;
    submitAttempt.mutate({ exercise_id: exercise.id, answers }, { onSuccess: (res) => setResult(res) });
  }

  if (!exercise) {
    return (
      <Box maxWidth={maxWidth}>
        <Typography variant="h4" gutterBottom>
          {skillLabel} - Teil {teil}
        </Typography>
        <Typography color="text.secondary" mb={3}>
          {description}
        </Typography>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} mb={4} alignItems={{ xs: "stretch", sm: "flex-start" }}>
          <TextField
            label={topicLabel}
            placeholder={topicPlaceholder}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            size="small"
          />
          <Button variant="contained" onClick={handleGenerate} disabled={generateExercise.isPending}>
            {generateExercise.isPending ? generatingLabel : "Generate new exercise"}
          </Button>
        </Stack>
        {generateExercise.isError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {describeError(generateExercise.error, "Failed to generate an exercise. Please try again.")}
          </Alert>
        )}

        <Typography variant="h6" gutterBottom>
          Or practice a previous exercise
        </Typography>
        {isLoadingList && <CircularProgress size={24} />}
        {openError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {openError}
          </Alert>
        )}
        {previousExercises && previousExercises.length === 0 && (
          <Typography color="text.secondary">No exercises generated yet.</Typography>
        )}
        <Stack spacing={1}>
          {previousExercises?.map((ex) => (
            <Card key={ex.id} variant="outlined">
              <CardActionArea onClick={() => openPrevious(ex.id)}>
                <CardContent>
                  <Typography variant="subtitle1">{ex.title}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {ex.topic ? `Topic: ${ex.topic}` : "No topic"} · {new Date(ex.created_at).toLocaleString()}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          ))}
        </Stack>
      </Box>
    );
  }

  const content = exercise.content as TContent;

  return (
    <Box maxWidth={maxWidth}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1} mb={2}>
        <Typography variant="h4">{exercise.title}</Typography>
        <Button component={RouterLink} to={basePath} variant="text">
          Back to {skillLabel}
        </Button>
      </Stack>

      {result && (
        <Alert severity={result.score === result.max_score ? "success" : "info"} sx={{ mb: 3 }}>
          Score: {result.score} / {result.max_score}
        </Alert>
      )}

      <Body
        content={content}
        answers={answers}
        setAnswer={(key, value) => setAnswers((prev) => ({ ...prev, [key]: value }))}
        result={result}
      />
      {result && ResultExtras && <ResultExtras result={result} />}

      <Stack direction="row" spacing={2} mt={3}>
        {!result ? (
          <Button
            variant="contained"
            size="large"
            disabled={!isComplete(content, answers) || submitAttempt.isPending}
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
          {describeError(submitAttempt.error, "Failed to submit your answers. Please try again.")}
        </Alert>
      )}
    </Box>
  );
}
