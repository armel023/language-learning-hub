import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
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
  LinearProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { describeError } from "../../api/client";
import { schreibenApi } from "../../api/schreiben";
import {
  useGenerateSchreibenExercise,
  useSchreibenExercises,
  useSubmitSchreibenAttempt,
} from "../../hooks/useSchreiben";
import type { ExerciseDetail, SchreibenAttempt, SchreibenContent } from "../../types/api";

function countWords(text: string) {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

export function SchreibenTeilPage({ teil }: { teil: 1 | 2 }) {
  const { data: previousExercises, isLoading: isLoadingList } = useSchreibenExercises(teil);
  const generateExercise = useGenerateSchreibenExercise();
  const submitAttempt = useSubmitSchreibenAttempt();

  const [topic, setTopic] = useState("");
  const [exercise, setExercise] = useState<ExerciseDetail<SchreibenContent> | null>(null);
  const [text, setText] = useState("");
  const [attempt, setAttempt] = useState<SchreibenAttempt | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  function startExercise(ex: ExerciseDetail<SchreibenContent>) {
    setExercise(ex);
    setText("");
    setAttempt(null);
    submitAttempt.reset();
  }

  async function openPrevious(id: string) {
    setOpenError(null);
    try {
      startExercise(await schreibenApi.getExercise(id));
    } catch (error) {
      setOpenError(describeError(error, "Could not open that exercise."));
    }
  }

  if (!exercise) {
    return (
      <Box maxWidth={720}>
        <Typography variant="h4" gutterBottom>
          Schreiben - Teil {teil}
        </Typography>
        <Typography color="text.secondary" mb={3}>
          {teil === 1
            ? "Write a short informal message to a friend or family member."
            : "Write a short semi-formal email to a teacher, landlord, colleague or office."}
        </Typography>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} mb={4} alignItems={{ xs: "stretch", sm: "flex-start" }}>
          <TextField
            label="Topic (optional)"
            placeholder="e.g. Geburtstag, Arzttermin, Umzug"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            size="small"
          />
          <Button
            variant="contained"
            disabled={generateExercise.isPending}
            onClick={() =>
              generateExercise.mutate({ teil, topic: topic || undefined }, { onSuccess: (ex) => startExercise(ex) })
            }
          >
            {generateExercise.isPending ? "Generating..." : "Generate new task"}
          </Button>
        </Stack>
        {generateExercise.isError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {describeError(generateExercise.error, "Failed to generate a task. Please try again.")}
          </Alert>
        )}

        <Typography variant="h6" gutterBottom>
          Or practice a previous task
        </Typography>
        {isLoadingList && <CircularProgress size={24} />}
        {openError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {openError}
          </Alert>
        )}
        {previousExercises && previousExercises.length === 0 && (
          <Typography color="text.secondary">No tasks generated yet.</Typography>
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

  const content = exercise.content;
  const [minWords, maxWords] = content.word_range;
  const words = countWords(text);
  const graded = attempt?.status === "graded" ? attempt : null;

  return (
    <Box maxWidth={760}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1} mb={2}>
        <Typography variant="h4">{exercise.title}</Typography>
        <Button component={RouterLink} to="/schreiben" variant="text">
          Back to Schreiben
        </Button>
      </Stack>

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={1} mb={1} flexWrap="wrap" useFlexGap>
            <Chip size="small" label={content.formality === "formal" ? "Sie (formal)" : "du (informal)"} />
            <Chip size="small" label={`${minWords}-${maxWords} words`} />
          </Stack>
          <Typography mb={1}>{content.situation}</Typography>
          <Typography variant="body2" color="text.secondary" mb={1}>
            An: {content.recipient}
          </Typography>
          <Typography fontWeight="bold">Schreiben Sie zu allen Punkten:</Typography>
          <Box component="ul" sx={{ mt: 0.5, mb: 0 }}>
            {content.content_points.map((point, i) => (
              <li key={i}>
                <Typography>{point}</Typography>
              </li>
            ))}
          </Box>
        </CardContent>
      </Card>

      <TextField
        multiline
        minRows={6}
        fullWidth
        placeholder={content.formality === "formal" ? "Sehr geehrte ..." : "Hallo ..."}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={submitAttempt.isPending || !!graded}
      />
      <Typography
        variant="caption"
        color={words > 0 && (words < minWords || words > maxWords) ? "warning.main" : "text.secondary"}
      >
        {words} words (aim for {minWords}-{maxWords})
      </Typography>

      <Stack direction="row" spacing={2} mt={2}>
        {!graded ? (
          <Button
            variant="contained"
            size="large"
            disabled={words === 0 || submitAttempt.isPending}
            onClick={() =>
              submitAttempt.mutate(
                { exerciseId: exercise.id, responseText: text },
                { onSuccess: (result) => setAttempt(result) },
              )
            }
          >
            {submitAttempt.isPending ? "Grading..." : "Submit for grading"}
          </Button>
        ) : (
          <Button variant="contained" onClick={() => setExercise(null)}>
            Try another task
          </Button>
        )}
      </Stack>
      {submitAttempt.isPending && <LinearProgress sx={{ mt: 2 }} />}

      {submitAttempt.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {describeError(submitAttempt.error, "Failed to submit your answer. Please try again.")}
        </Alert>
      )}
      {attempt?.status === "failed" && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Grading failed: {attempt.feedback?.error ?? "unknown error"}. Your text is still here; please try again.
        </Alert>
      )}

      {graded && <GradeView attempt={graded} content={content} />}
    </Box>
  );
}

function GradeView({ attempt, content }: { attempt: SchreibenAttempt; content: SchreibenContent }) {
  const rubric = attempt.rubric_scores;
  const feedback = attempt.feedback;
  if (!rubric || !feedback) return null;

  return (
    <Box mt={3}>
      <Alert severity={attempt.score === attempt.max_score ? "success" : "info"} sx={{ mb: 2 }}>
        Score: {attempt.score} / {attempt.max_score} (practice rubric)
      </Alert>
      {feedback.summary && <Typography mb={2}>{feedback.summary}</Typography>}

      <Card variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableBody>
            {rubric.content_points.map((point) => (
              <TableRow key={point.point_number}>
                <TableCell sx={{ width: "40%" }}>{content.content_points[point.point_number - 1]}</TableCell>
                <TableCell sx={{ width: 60 }}>{point.score} / 2</TableCell>
                <TableCell>{point.comment}</TableCell>
              </TableRow>
            ))}
            <TableRow>
              <TableCell>Communication</TableCell>
              <TableCell>{rubric.communication.score} / 2</TableCell>
              <TableCell>{rubric.communication.comment}</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>Accuracy</TableCell>
              <TableCell>{rubric.accuracy.score} / 2</TableCell>
              <TableCell>{rubric.accuracy.comment}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>

      {feedback.corrections && feedback.corrections.length > 0 && (
        <>
          <Typography variant="h6" gutterBottom>
            Corrections
          </Typography>
          <Stack spacing={1} mb={2}>
            {feedback.corrections.map((c, i) => (
              <Card key={i} variant="outlined">
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Typography>
                    <Box component="span" sx={{ textDecoration: "line-through", color: "error.main" }}>
                      {c.original}
                    </Box>{" "}
                    →{" "}
                    <Box component="span" sx={{ color: "success.main", fontWeight: "bold" }}>
                      {c.corrected}
                    </Box>
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {c.explanation}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </>
      )}

      {feedback.improved_version && (
        <>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            A stronger version of your answer
          </Typography>
          <Typography sx={{ whiteSpace: "pre-wrap" }}>{feedback.improved_version}</Typography>
        </>
      )}
    </Box>
  );
}
