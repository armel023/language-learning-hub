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
import type { ReadingTeil3Content } from "../../types/api";

export function Teil3Page() {
  return (
    <ExerciseShell<ReadingTeil3Content, number>
      teil={3}
      description="Read a 5-paragraph email, then complete 5 sentence stems by choosing the ending that matches what the email says."
      topicLabel="Topic (optional)"
      topicPlaceholder="e.g. eine Einladung, ein neuer Job, Urlaubspläne"
      maxWidth={720}
      isComplete={(content, answers) => content.questions.every((q) => answers[String(q.question_number)] !== undefined)}
      Body={Teil3Body}
    />
  );
}

function Teil3Body({ content, answers, setAnswer, result }: ExerciseBodyProps<ReadingTeil3Content, number>) {

  return (
    <>
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={2}>
            <Typography>{content.greeting}</Typography>
            {[...content.paragraphs]
              .sort((a, b) => a.paragraph_number - b.paragraph_number)
              .map((paragraph) => (
                <Typography key={paragraph.paragraph_number}>{paragraph.text}</Typography>
              ))}
            <Box>
              {content.closing_phrase.split("\n").map((line, i) => (
                <Typography key={i}>{line}</Typography>
              ))}
              <Typography>{content.email_sender_name}</Typography>
            </Box>
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
