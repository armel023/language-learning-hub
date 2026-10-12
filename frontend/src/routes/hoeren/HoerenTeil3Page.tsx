import { Card, CardContent, Grid, Stack, Typography } from "@mui/material";

import { AudioPlayer } from "../../components/AudioPlayer";
import { ExerciseShell, type ExerciseBodyProps } from "../../components/ExerciseShell";
import { PictureCard } from "../../components/PictureCard";
import { Transcript } from "../../components/Transcript";
import type { HoerenAttemptResult, HoerenTeil3Content } from "../../types/api";
import { Explanation, ResultIcon, hoerenShellProps } from "./shared";

const LETTERS = ["a", "b", "c"];

export function HoerenTeil3Page() {
  return (
    <ExerciseShell<HoerenTeil3Content, number, HoerenAttemptResult>
      {...hoerenShellProps}
      teil={3}
      description="Five short conversations, each played once. Choose the right picture. Careful: all three are mentioned."
      topicLabel="Topic (optional)"
      topicPlaceholder="e.g. Einkaufen, Freizeit, Kleidung"
      isComplete={(content, answers) => content.items.every((i) => answers[String(i.item_number)] !== undefined)}
      Body={Teil3Body}
    />
  );
}

function Teil3Body({ content, answers, setAnswer, result }: ExerciseBodyProps<HoerenTeil3Content, number, HoerenAttemptResult>) {
  return (
    <Stack spacing={2}>
      {content.items.map((item) => {
        const key = String(item.item_number);
        const correctIndex = result?.correct_answers[key];
        return (
          <Card key={key} variant="outlined">
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                {item.context}
              </Typography>
              <AudioPlayer src={item.audio.url} plays={content.plays} unlocked={!!result} />
              <Stack direction="row" spacing={1} alignItems="center" mt={2} mb={1}>
                <Typography fontWeight="bold" sx={{ flexGrow: 1 }}>
                  {item.item_number}. {item.prompt}
                </Typography>
                <ResultIcon correct={result?.is_correct_per_question[key]} />
              </Stack>
              <Grid container spacing={1}>
                {item.options.map((option, idx) => (
                  <Grid item xs={4} key={idx}>
                    <PictureCard
                      picture={option}
                      label={LETTERS[idx]}
                      selected={answers[key] === idx}
                      state={result ? (idx === correctIndex ? "correct" : answers[key] === idx ? "wrong" : undefined) : undefined}
                      onClick={result ? undefined : () => setAnswer(key, idx)}
                    />
                  </Grid>
                ))}
              </Grid>
              {result && (
                <>
                  <Explanation text={result.explanations[key]} />
                  <Transcript lines={result.transcripts[key]} />
                </>
              )}
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
}
