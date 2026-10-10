import { Card, CardContent, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";

import { AudioPlayer } from "../../components/AudioPlayer";
import { ExerciseShell, type ExerciseBodyProps } from "../../components/ExerciseShell";
import { Transcript } from "../../components/Transcript";
import type { HoerenAttemptResult, HoerenTeil4Content } from "../../types/api";
import { Explanation, ResultIcon, hoerenShellProps } from "./shared";

export function HoerenTeil4Page() {
  return (
    <ExerciseShell<HoerenTeil4Content, string, HoerenAttemptResult>
      {...hoerenShellProps}
      teil={4}
      description="One interview, played twice. For each statement (16-20) choose Ja or Nein."
      topicLabel="Topic (optional)"
      topicPlaceholder="e.g. Beruf, Hobby, Umzug"
      isComplete={(content, answers) => content.statements.every((s) => !!answers[String(s.number)])}
      Body={Teil4Body}
    />
  );
}

function Teil4Body({ content, answers, setAnswer, result }: ExerciseBodyProps<HoerenTeil4Content, string, HoerenAttemptResult>) {
  return (
    <>
      <Typography mb={1}>{content.context}</Typography>
      <AudioPlayer src={content.audio.url} plays={content.plays} unlocked={!!result} />
      <Stack spacing={1.5} mt={3}>
        {content.statements.map((s) => {
          const key = String(s.number);
          const correct = result?.correct_answers[key];
          return (
            <Card key={key} variant="outlined">
              <CardContent>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ xs: "stretch", sm: "center" }}>
                  <Typography sx={{ flexGrow: 1 }}>
                    <b>{s.number}.</b> {s.statement}
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <ToggleButtonGroup
                      exclusive
                      size="small"
                      value={answers[key] ?? null}
                      disabled={!!result}
                      onChange={(_, value: string | null) => value && setAnswer(key, value)}
                    >
                      <ToggleButton value="ja" sx={{ px: 2.5 }}>
                        Ja
                      </ToggleButton>
                      <ToggleButton value="nein" sx={{ px: 2.5 }}>
                        Nein
                      </ToggleButton>
                    </ToggleButtonGroup>
                    <ResultIcon correct={result?.is_correct_per_question[key]} />
                  </Stack>
                </Stack>
                {result && (
                  <>
                    <Typography variant="body2" color="success.main" mt={1}>
                      Richtig: {correct === "ja" ? "Ja" : "Nein"}
                    </Typography>
                    <Explanation text={result.explanations[key]} />
                  </>
                )}
              </CardContent>
            </Card>
          );
        })}
      </Stack>
      {result && <Transcript lines={result.transcripts.all} />}
    </>
  );
}
