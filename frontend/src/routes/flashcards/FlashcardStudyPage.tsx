import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";

import { useRecordStudyReview, useStartStudySession } from "../../hooks/useStudy";
import type { StudyOutcome, VocabularyItem } from "../../types/api";

type Phase = "intro" | "studying" | "summary";
type StudyDirection = "de_en" | "en_de";

export function FlashcardStudyPage() {
  const startSession = useStartStudySession();
  const recordReview = useRecordStudyReview();

  const [phase, setPhase] = useState<Phase>("intro");
  const [direction, setDirection] = useState<StudyDirection>("de_en");
  const [words, setWords] = useState<VocabularyItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [tally, setTally] = useState<Record<StudyOutcome, number>>({
    correct: 0,
    incorrect_hard: 0,
    incorrect_moderate: 0,
  });

  function handleStart(chosenDirection: StudyDirection) {
    setDirection(chosenDirection);
    startSession.mutate(undefined, {
      onSuccess: (result) => {
        setWords(result.words);
        setCurrentIndex(0);
        setRevealed(false);
        setTally({ correct: 0, incorrect_hard: 0, incorrect_moderate: 0 });
        setPhase("studying");
      },
    });
  }

  function handleAnswer(outcome: StudyOutcome) {
    const word = words[currentIndex];
    recordReview.mutate({ vocabularyId: word.id, outcome });
    setTally((prev) => ({ ...prev, [outcome]: prev[outcome] + 1 }));

    if (currentIndex + 1 >= words.length) {
      setPhase("summary");
    } else {
      setCurrentIndex((i) => i + 1);
      setRevealed(false);
    }
  }

  const directionDialog = (
    <Dialog open={phase === "intro"} disableEscapeKeyDown>
      <DialogTitle>Choose study direction</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Study the default direction (German word, recall the English meaning), or reverse it
          (English meaning, recall the German word).
        </DialogContentText>
        {startSession.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            Failed to start a study session. Please try again.
          </Alert>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button
          variant="outlined"
          onClick={() => handleStart("en_de")}
          disabled={startSession.isPending}
        >
          Reverse (English → German)
        </Button>
        <Button
          variant="contained"
          onClick={() => handleStart("de_en")}
          disabled={startSession.isPending}
        >
          Default (German → English)
        </Button>
      </DialogActions>
    </Dialog>
  );

  if (phase === "intro") {
    return (
      <Box maxWidth={480}>
        <Typography variant="h4" mb={2}>
          Study
        </Typography>
        <Typography color="text.secondary" mb={3}>
          20 words will be randomly selected, prioritizing words you previously marked hard or
          moderate. For each word, try to recall the meaning yourself, then reveal it and grade
          how you did.
        </Typography>
        {directionDialog}
      </Box>
    );
  }

  if (phase === "summary") {
    return (
      <Box maxWidth={480}>
        <Typography variant="h4" mb={2}>
          Session complete
        </Typography>
        <Stack direction="row" spacing={1} mb={3}>
          <Chip color="success" label={`Correct: ${tally.correct}`} />
          <Chip color="error" label={`Hard: ${tally.incorrect_hard}`} />
          <Chip color="warning" label={`Moderate: ${tally.incorrect_moderate}`} />
        </Stack>
        <Stack direction="row" spacing={2}>
          <Button variant="contained" onClick={() => setPhase("intro")}>
            Study again
          </Button>
          <Button component={RouterLink} to="/flashcards" variant="outlined">
            Back to flashcards
          </Button>
        </Stack>
      </Box>
    );
  }

  const word = words[currentIndex];
  const germanSide = `${word.article ? `${word.article} ` : ""}${word.word}`;
  const promptText = direction === "de_en" ? germanSide : word.translation;
  const answerText = direction === "de_en" ? word.translation : germanSide;

  return (
    <Box maxWidth={520}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="h6">
          Word {currentIndex + 1} of {words.length}
        </Typography>
        <Chip
          size="small"
          variant="outlined"
          label={direction === "de_en" ? "German → English" : "English → German"}
        />
      </Stack>
      <LinearProgress variant="determinate" value={(currentIndex / words.length) * 100} sx={{ mb: 3 }} />

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent sx={{ textAlign: "center", py: 5 }}>
          <Typography variant="h4" gutterBottom>
            {promptText}
          </Typography>

          {revealed ? (
            <Box mt={2}>
              <Typography variant="h6" color="primary">
                {answerText}
              </Typography>
              {word.example_sentence_de && (
                <Box mt={2}>
                  <Typography color="text.secondary">{word.example_sentence_de}</Typography>
                  {word.example_sentence_translation && (
                    <Typography color="text.secondary" fontStyle="italic">
                      {word.example_sentence_translation}
                    </Typography>
                  )}
                </Box>
              )}
            </Box>
          ) : (
            <Button variant="outlined" sx={{ mt: 2 }} onClick={() => setRevealed(true)}>
              Show meaning
            </Button>
          )}
        </CardContent>
      </Card>

      {revealed && (
        <Stack direction="row" spacing={2} justifyContent="center">
          <Button variant="contained" color="success" onClick={() => handleAnswer("correct")}>
            Correct
          </Button>
          <Button variant="contained" color="warning" onClick={() => handleAnswer("incorrect_moderate")}>
            Incorrect - Moderate
          </Button>
          <Button variant="contained" color="error" onClick={() => handleAnswer("incorrect_hard")}>
            Incorrect - Hard
          </Button>
        </Stack>
      )}
    </Box>
  );
}
