import { Card, CardContent, FormControl, FormControlLabel, Radio, RadioGroup, Stack, Typography } from "@mui/material";

import { AudioPlayer } from "../../components/AudioPlayer";
import { ExerciseShell, type ExerciseBodyProps } from "../../components/ExerciseShell";
import { Transcript } from "../../components/Transcript";
import type { HoerenAttemptResult, HoerenTeil1Content } from "../../types/api";
import { Explanation, ResultIcon, hoerenShellProps } from "./shared";

export function HoerenTeil1Page() {
  return (
    <ExerciseShell<HoerenTeil1Content, number, HoerenAttemptResult>
      {...hoerenShellProps}
      teil={1}
      description="Five short texts (messages, announcements). Each is played twice; answer one question per text."
      topicLabel="Topic (optional)"
      topicPlaceholder="e.g. Bahnhof, Arztpraxis, Wetter"
      isComplete={(content, answers) => content.items.every((i) => answers[String(i.item_number)] !== undefined)}
      Body={Teil1Body}
    />
  );
}

function Teil1Body({ content, answers, setAnswer, result }: ExerciseBodyProps<HoerenTeil1Content, number, HoerenAttemptResult>) {
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
              <FormControl disabled={!!result}>
                <RadioGroup value={answers[key] ?? ""} onChange={(e) => setAnswer(key, Number(e.target.value))}>
                  {item.options.map((option, idx) => (
                    <FormControlLabel
                      key={idx}
                      value={idx}
                      control={<Radio />}
                      label={option}
                      sx={result && idx === correctIndex ? { color: "success.main", fontWeight: "bold" } : undefined}
                    />
                  ))}
                </RadioGroup>
              </FormControl>
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
