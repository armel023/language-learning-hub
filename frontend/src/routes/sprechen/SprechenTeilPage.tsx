import { useEffect, useRef, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import MicIcon from "@mui/icons-material/Mic";
import StopIcon from "@mui/icons-material/Stop";
import LightbulbIcon from "@mui/icons-material/Lightbulb";
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
  Drawer,
  LinearProgress,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";

import { describeError } from "../../api/client";
import { sprechenApi } from "../../api/sprechen";
import { SprechenCardView, instructionFor } from "../../components/SprechenCards";
import { useLiveSession, type LiveCaption } from "../../hooks/useLiveSession";
import type { ExerciseDetail, SprechenAttempt, SprechenContent } from "../../types/api";
import { HINTS } from "./hints";

const PREP_SECONDS: Record<number, number> = { 1: 0, 2: 0, 3: 20 };

const DESCRIPTIONS: Record<number, string> = {
  1: "Ask your partner four questions with your cards, then answer their four questions (2–3 sentences each).",
  2: "Talk about your life using your card. Cover every point. Your partner only listens.",
  3: "Plan something with your partner. You can't see their card; stick to the details on yours.",
};

export function SprechenTeilPage({ teil }: { teil: 1 | 2 | 3 }) {
  const [exercise, setExercise] = useState<ExerciseDetail<SprechenContent> | null>(null);

  if (!exercise) return <Picker teil={teil} onOpen={setExercise} />;
  return <Session key={exercise.id} teil={teil} exercise={exercise} onBack={() => setExercise(null)} />;
}

// --- choose or generate cards ---------------------------------------------------------------------

function Picker({ teil, onOpen }: { teil: 1 | 2 | 3; onOpen: (ex: ExerciseDetail<SprechenContent>) => void }) {
  const [topic, setTopic] = useState("");
  const [variant, setVariant] = useState<"termin" | "planen" | "any">("any");
  const [openError, setOpenError] = useState<string | null>(null);
  const previous = useQuery({ queryKey: ["/sprechen", "exercises", teil], queryFn: () => sprechenApi.listExercises(teil) });
  const generate = useMutation({ mutationFn: sprechenApi.generateExercise, onSuccess: onOpen });

  return (
    <Box maxWidth={720}>
      <Typography variant="h4" gutterBottom>
        Sprechen - Teil {teil}
      </Typography>
      <Typography color="text.secondary" mb={3}>
        {DESCRIPTIONS[teil]}
      </Typography>

      {teil === 3 && (
        <ToggleButtonGroup exclusive size="small" value={variant} onChange={(_, v) => v && setVariant(v)} sx={{ mb: 2, flexWrap: "wrap" }}>
          <ToggleButton value="any">Either</ToggleButton>
          <ToggleButton value="termin">Termin finden</ToggleButton>
          <ToggleButton value="planen">Etwas planen</ToggleButton>
        </ToggleButtonGroup>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} mb={4} alignItems={{ xs: "stretch", sm: "flex-start" }}>
        <TextField label="Topic (optional)" value={topic} onChange={(e) => setTopic(e.target.value)} size="small" />
        <Button
          variant="contained"
          disabled={generate.isPending}
          onClick={() =>
            generate.mutate({ teil, topic: topic || undefined, variant: teil === 3 && variant !== "any" ? variant : undefined })
          }
        >
          {generate.isPending ? "Generating cards..." : "Generate new cards"}
        </Button>
      </Stack>
      {generate.isError && <Alert severity="error" sx={{ mb: 3 }}>{describeError(generate.error, "Failed to generate cards.")}</Alert>}

      <Typography variant="h6" gutterBottom>
        Or practice previous cards
      </Typography>
      {previous.isLoading && <CircularProgress size={24} />}
      {openError && <Alert severity="error" sx={{ mb: 2 }}>{openError}</Alert>}
      {previous.data?.length === 0 && <Typography color="text.secondary">No cards generated yet.</Typography>}
      <Stack spacing={1}>
        {previous.data?.map((ex) => (
          <Card key={ex.id} variant="outlined">
            <CardActionArea
              onClick={async () => {
                setOpenError(null);
                try {
                  onOpen(await sprechenApi.getExercise(ex.id));
                } catch (e) {
                  setOpenError(describeError(e, "Could not open these cards."));
                }
              }}
            >
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

// --- prepare, talk, get feedback ------------------------------------------------------------------

function Session({ teil, exercise, onBack }: { teil: number; exercise: ExerciseDetail<SprechenContent>; onBack: () => void }) {
  const live = useLiveSession(exercise.id);
  const [prepLeft, setPrepLeft] = useState(PREP_SECONDS[teil]);
  const [hintsOpen, setHintsOpen] = useState(false);
  const feedback = useMutation({ mutationFn: sprechenApi.waitForFeedback });
  const requested = useRef(false);

  useEffect(() => {
    if (prepLeft <= 0) return;
    const t = window.setTimeout(() => setPrepLeft((s) => s - 1), 1000);
    return () => window.clearTimeout(t);
  }, [prepLeft]);

  useEffect(() => {
    if (live.attemptId && !requested.current) {
      requested.current = true;
      feedback.mutate(live.attemptId);
    }
  }, [live.attemptId, feedback]);

  const isLive = live.status === "live" || live.status === "connecting" || live.status === "ending";
  const finished = live.status === "ended" || live.status === "error";

  return (
    <Box maxWidth={760}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1} mb={1}>
        <Typography variant="h4">{exercise.title}</Typography>
        <Button component={RouterLink} to="/sprechen" variant="text" onClick={onBack} disabled={isLive}>
          Back to Sprechen
        </Button>
      </Stack>
      <Typography mb={2}>{instructionFor(teil, exercise.content)}</Typography>

      <Box mb={3}>
        <SprechenCardView teil={teil} content={exercise.content} />
      </Box>

      {live.status === "idle" && (
        <Stack spacing={1.5} alignItems="flex-start">
          {prepLeft > 0 && (
            <Alert severity="info" sx={{ width: "100%" }}>
              Sehen Sie sich Ihre Karte an: noch {prepLeft} Sekunden.{" "}
              <Button size="small" onClick={() => setPrepLeft(0)}>
                Skip
              </Button>
            </Alert>
          )}
          <Button variant="contained" size="large" startIcon={<MicIcon />} disabled={prepLeft > 0} onClick={live.start}>
            Start conversation
          </Button>
          <Typography variant="caption" color="text.secondary">
            Use headphones if you can, so your partner doesn't hear itself. {teil === 3 ? "Your partner starts." : "You start."}
          </Typography>
        </Stack>
      )}

      {isLive && (
        <LivePanel
          captions={live.captions}
          status={live.status}
          elapsed={live.elapsed}
          maxSeconds={live.maxSeconds}
          partnerSpeaking={live.partnerSpeaking}
          onStop={live.stop}
          onHints={() => setHintsOpen(true)}
        />
      )}

      {live.error && <Alert severity="error" sx={{ mt: 2 }}>{live.error}</Alert>}

      {finished && live.attemptId && (
        <Box mt={3}>
          {feedback.isPending && (
            <Stack direction="row" spacing={1} alignItems="center">
              <CircularProgress size={20} />
              <Typography>Creating your feedback...</Typography>
            </Stack>
          )}
          {feedback.isError && <Alert severity="error">{describeError(feedback.error, "Could not load the feedback.")}</Alert>}
          {feedback.data && <FeedbackView attempt={feedback.data} />}
        </Box>
      )}
      {finished && (
        <Button variant="outlined" sx={{ mt: 3 }} onClick={onBack}>
          Practice other cards
        </Button>
      )}

      <Drawer anchor="bottom" open={hintsOpen} onClose={() => setHintsOpen(false)}>
        <Box sx={{ p: 2, maxHeight: "60vh", overflow: "auto" }}>
          {HINTS[teil].map((group) => (
            <Box key={group.title} mb={2}>
              <Typography fontWeight="bold" gutterBottom>
                {group.title}
              </Typography>
              {group.phrases.map((p) => (
                <Typography key={p} variant="body2" sx={{ mb: 0.5 }}>
                  • {p}
                </Typography>
              ))}
            </Box>
          ))}
        </Box>
      </Drawer>
    </Box>
  );
}

function LivePanel(props: {
  captions: LiveCaption[];
  status: string;
  elapsed: number;
  maxSeconds: number;
  partnerSpeaking: boolean;
  onStop: () => void;
  onHints: () => void;
}) {
  const bottom = useRef<HTMLDivElement>(null);
  // Braces matter: scrollIntoView() returns a Promise in current browsers, and an effect must
  // return nothing or a cleanup function.
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [props.captions]);
  const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap mb={1}>
          <Chip
            size="small"
            color={props.status === "live" ? "success" : "default"}
            label={props.status === "connecting" ? "Connecting..." : props.status === "ending" ? "Saving..." : props.partnerSpeaking ? "Partner spricht" : "Sie sind dran"}
          />
          <Typography variant="body2" color="text.secondary">
            {mmss(props.elapsed)} / {mmss(props.maxSeconds)}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Button size="small" startIcon={<LightbulbIcon />} onClick={props.onHints}>
            Hint
          </Button>
          <Button size="small" variant="contained" color="error" startIcon={<StopIcon />} onClick={props.onStop} disabled={props.status !== "live"}>
            End
          </Button>
        </Stack>
        {props.status === "connecting" && <LinearProgress sx={{ mb: 1 }} />}
        <Box sx={{ maxHeight: 320, overflow: "auto" }}>
          {props.captions.length === 0 && props.status === "live" && (
            <Typography color="text.secondary" variant="body2">
              Sprechen Sie jetzt...
            </Typography>
          )}
          {props.captions.map((c) => (
            <Box key={c.index} sx={{ display: "flex", justifyContent: c.role === "candidate" ? "flex-end" : "flex-start", mb: 1 }}>
              <Box
                sx={{
                  maxWidth: "85%",
                  px: 1.5,
                  py: 1,
                  borderRadius: 2,
                  bgcolor: c.role === "candidate" ? "primary.main" : "action.hover",
                  color: c.role === "candidate" ? "primary.contrastText" : "text.primary",
                }}
              >
                <Typography variant="body2">{c.text}</Typography>
              </Box>
            </Box>
          ))}
          <div ref={bottom} />
        </Box>
      </CardContent>
    </Card>
  );
}

function FeedbackView({ attempt }: { attempt: SprechenAttempt }) {
  if (attempt.status === "failed") {
    return <Alert severity="error">Feedback failed: {attempt.feedback?.error ?? "unknown error"}</Alert>;
  }
  const rubric = attempt.rubric_scores;
  const fb = attempt.feedback;
  if (!rubric || !fb) return null;
  return (
    <Box>
      <Alert severity={attempt.score === attempt.max_score ? "success" : "info"} sx={{ mb: 2 }}>
        Score: {attempt.score} / {attempt.max_score} (practice rubric · task {rubric.task}/{rubric.task_max}, interaction{" "}
        {rubric.interaction.score}/3, accuracy {rubric.accuracy.score}/3)
      </Alert>
      {fb.summary && <Typography mb={2}>{fb.summary}</Typography>}

      <Typography variant="h6" gutterBottom>
        Checklist
      </Typography>
      <Stack spacing={1} mb={2}>
        {rubric.checklist.map((c) => (
          <Stack key={c.item} direction="row" spacing={1} alignItems="flex-start">
            {c.done ? <CheckCircleIcon color="success" fontSize="small" /> : <CancelIcon color="error" fontSize="small" />}
            <Box>
              <Typography variant="body2" fontWeight="bold">
                {c.item}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {c.comment}
              </Typography>
            </Box>
          </Stack>
        ))}
      </Stack>
      <Typography variant="body2" mb={0.5}>
        <b>Interaction:</b> {rubric.interaction.comment}
      </Typography>
      <Typography variant="body2" mb={2}>
        <b>Accuracy:</b> {rubric.accuracy.comment}
      </Typography>

      {fb.corrections && fb.corrections.length > 0 && (
        <>
          <Typography variant="h6" gutterBottom>
            Corrections
          </Typography>
          <Stack spacing={1} mb={2}>
            {fb.corrections.map((c, i) => (
              <Card key={i} variant="outlined">
                <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                  <Typography>
                    <Box component="span" sx={{ textDecoration: "line-through", color: "error.main" }}>{c.original}</Box> →{" "}
                    <Box component="span" sx={{ color: "success.main", fontWeight: "bold" }}>{c.corrected}</Box>
                  </Typography>
                  <Typography variant="body2" color="text.secondary">{c.explanation}</Typography>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </>
      )}
      {fb.better_phrases && fb.better_phrases.length > 0 && (
        <>
          <Typography variant="h6" gutterBottom>
            You could also say
          </Typography>
          {fb.better_phrases.map((p) => (
            <Typography key={p} variant="body2" sx={{ mb: 0.5 }}>
              • {p}
            </Typography>
          ))}
        </>
      )}
      {attempt.transcript && attempt.transcript.length > 0 && (
        <Box sx={{ mt: 2, p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
          <Typography variant="overline" color="text.secondary">
            Transkript
          </Typography>
          {attempt.transcript.map((t, i) => (
            <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>
              <b>{t.role === "candidate" ? "Sie" : "Partner"}:</b> {t.text}
            </Typography>
          ))}
        </Box>
      )}
    </Box>
  );
}
