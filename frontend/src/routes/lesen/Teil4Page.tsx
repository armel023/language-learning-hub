import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";

import { ExerciseShell, type ExerciseBodyProps } from "../../components/ExerciseShell";
import type { ReadingTeil4Content } from "../../types/api";

export function Teil4Page() {
  return (
    <ExerciseShell<ReadingTeil4Content, string>
      teil={4}
      description={`6 advertisements are shown. Match each of the 5 situations to the one ad that actually fits it - or "X" if none of them do.`}
      topicLabel="Theme (optional)"
      topicPlaceholder="e.g. Restaurants, Wohnungen, Sprachschulen"
      maxWidth={820}
      isComplete={(content, answers) => content.aufgaben.every((a) => answers[String(a.aufgabe_number)] !== undefined)}
      Body={Teil4Body}
    />
  );
}

function Teil4Body({ content, answers, setAnswer, result }: ExerciseBodyProps<ReadingTeil4Content, string>) {
  const adByCode = Object.fromEntries(content.ads.map((ad) => [ad.code, ad]));

  return (
    <>
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
                    onChange={(e) => setAnswer(aKey, e.target.value)}
                    sx={{ minWidth: 220, width: { xs: "100%", sm: "auto" } }}
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
    </>
  );
}
