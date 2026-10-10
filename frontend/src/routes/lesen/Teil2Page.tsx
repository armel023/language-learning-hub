import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
  Stack,
  Typography,
} from "@mui/material";

import { ExerciseShell, type ExerciseBodyProps } from "../../components/ExerciseShell";
import type { ReadingTeil2Content } from "../../types/api";

export function Teil2Page() {
  return (
    <ExerciseShell<ReadingTeil2Content, number>
      teil={2}
      description={`A department store's floor directory is shown. For each situation, pick which floor it belongs to - or "Anderer Stock" if it's neither of the two offered.`}
      topicLabel="Store type (optional)"
      topicPlaceholder="e.g. Kaufhaus, Baumarkt, Möbelhaus"
      maxWidth={720}
      isComplete={(content, answers) => content.aufgaben.every((a) => answers[String(a.aufgabe_number)] !== undefined)}
      Body={Teil2Body}
    />
  );
}

function Teil2Body({ content, answers, setAnswer, result }: ExerciseBodyProps<ReadingTeil2Content, number>) {

  return (
    <>
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
                      onChange={(e) => setAnswer(aKey, Number(e.target.value))}
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
    </>
  );
}
