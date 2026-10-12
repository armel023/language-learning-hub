import { Card, CardContent, Chip, Grid, MenuItem, Select, Stack, Typography } from "@mui/material";

import { AudioPlayer } from "../../components/AudioPlayer";
import { ExerciseShell, type ExerciseBodyProps } from "../../components/ExerciseShell";
import { PictureCard } from "../../components/PictureCard";
import { Transcript } from "../../components/Transcript";
import type { HoerenAttemptResult, HoerenTeil2Content } from "../../types/api";
import { Explanation, ResultIcon, hoerenShellProps } from "./shared";

export function HoerenTeil2Page() {
  return (
    <ExerciseShell<HoerenTeil2Content, string, HoerenAttemptResult>
      {...hoerenShellProps}
      teil={2}
      description="One conversation, played once. Match each time (6-10) to a picture a-i. Use each letter only once."
      topicLabel="Topic (optional)"
      topicPlaceholder="e.g. Wochenplan, Urlaub, Familienfeier"
      maxWidth={820}
      isComplete={(content, answers) => content.aufgaben.every((a) => !!answers[String(a.aufgabe_number)])}
      Body={Teil2Body}
    />
  );
}

function Teil2Body({ content, answers, setAnswer, result }: ExerciseBodyProps<HoerenTeil2Content, string, HoerenAttemptResult>) {
  const pictureByCode = Object.fromEntries(content.pictures.map((p) => [p.code, p]));
  // Each letter only once: the Beispiel's and other Aufgaben's choices are taken.
  const taken = (except: string) =>
    new Set([content.beispiel.correct_code, ...Object.entries(answers).filter(([k]) => k !== except).map(([, v]) => v)]);

  return (
    <>
      <Typography mb={1}>{content.context}</Typography>
      <AudioPlayer src={content.audio.url} plays={content.plays} unlocked={!!result} />
      <Typography variant="body2" color="text.secondary" mt={2} mb={1}>
        Wählen Sie für Aufgabe 6 bis 10 ein passendes Bild aus a bis i. Wählen Sie jeden Buchstaben nur einmal.
      </Typography>

      <Grid container spacing={1} mb={3}>
        {content.pictures.map((p) => (
          <Grid item xs={4} sm={4} md={4} key={p.code}>
            <PictureCard picture={p} label={p.code} dimmed={p.code === content.beispiel.correct_code} />
          </Grid>
        ))}
      </Grid>

      <Card variant="outlined" sx={{ mb: 2, bgcolor: "action.hover" }}>
        <CardContent>
          <Chip size="small" label="Beispiel" sx={{ mb: 1 }} />
          <Typography>
            <b>0 · {content.beispiel.label}:</b> {content.beispiel.correct_code} ({pictureByCode[content.beispiel.correct_code]?.caption})
          </Typography>
        </CardContent>
      </Card>

      <Stack spacing={1.5}>
        {content.aufgaben.map((a) => {
          const key = String(a.aufgabe_number);
          const correct = result?.correct_answers[key] as string | undefined;
          const blocked = taken(key);
          return (
            <Card key={key} variant="outlined">
              <CardContent>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography fontWeight="bold" sx={{ minWidth: 120, flexGrow: 1 }}>
                    {a.aufgabe_number} · {a.label}
                  </Typography>
                  <Select
                    size="small"
                    displayEmpty
                    value={answers[key] ?? ""}
                    disabled={!!result}
                    onChange={(e) => setAnswer(key, e.target.value)}
                    sx={{ minWidth: 180, width: { xs: "100%", sm: "auto" } }}
                  >
                    <MenuItem value="" disabled>
                      Bild wählen...
                    </MenuItem>
                    {content.pictures.map((p) => (
                      <MenuItem key={p.code} value={p.code} disabled={blocked.has(p.code)}>
                        {p.code} · {p.emoji} {p.caption}
                      </MenuItem>
                    ))}
                  </Select>
                  <ResultIcon correct={result?.is_correct_per_question[key]} />
                </Stack>
                {result && correct && (
                  <>
                    <Typography variant="body2" color="success.main" mt={1}>
                      Richtig: {correct} · {pictureByCode[correct]?.emoji} {pictureByCode[correct]?.caption}
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
