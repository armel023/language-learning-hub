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
import type { ReadingTeil1Content } from "../../types/api";

export function Teil1Page() {
  return (
    <ExerciseShell<ReadingTeil1Content, number>
      teil={1}
      description="Read a 5-paragraph article and answer one 3-choice question per paragraph."
      topicLabel="Topic (optional)"
      topicPlaceholder="e.g. Einkaufen, Reisen, Wetter"
      maxWidth={720}
      isComplete={(content, answers) => content.questions.every((q) => answers[String(q.question_number)] !== undefined)}
      Body={Teil1Body}
    />
  );
}

function Teil1Body({ content, answers, setAnswer, result }: ExerciseBodyProps<ReadingTeil1Content, number>) {

  return (
    <>
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="overline" color="text.secondary">
            Text
          </Typography>
          <Stack spacing={2} mt={1}>
            {[...content.paragraphs]
              .sort((a, b) => a.paragraph_number - b.paragraph_number)
              .map((paragraph) => (
                <Box key={paragraph.paragraph_number}>
                  <Typography variant="caption" color="text.secondary">
                    Absatz {paragraph.paragraph_number}
                  </Typography>
                  <Typography>{paragraph.text}</Typography>
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
        {[...content.questions]
          .sort((a, b) => a.question_number - b.question_number)
          .map((question) => {
            const qKey = String(question.question_number);
            const isCorrect = result?.is_correct_per_question[qKey];
            const correctIndex = result?.correct_answers[qKey];

            return (
              <Card key={question.question_number} variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    Refers to Absatz {question.paragraph_number}
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                    <Typography fontWeight="bold">
                      {question.question_number}. {question.prompt}
                    </Typography>
                    {result && (isCorrect ? <CheckCircleIcon color="success" /> : <CancelIcon color="error" />)}
                  </Stack>

                  <FormControl disabled={!!result}>
                    <RadioGroup
                      value={answers[qKey] ?? ""}
                      onChange={(e) => setAnswer(qKey, Number(e.target.value))}
                    >
                      {question.options.map((option, idx) => (
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
                      {result.explanations[qKey]}
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
