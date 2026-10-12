import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import { Typography } from "@mui/material";

import { hoerenApi } from "../../api/hoeren";
import { HoerenVocabulary } from "../../components/HoerenVocabulary";

/** Props every Hören Teil page passes to ExerciseShell. */
export const hoerenShellProps = {
  api: hoerenApi,
  skillLabel: "Hören",
  basePath: "/hoeren",
  generatingLabel: "Writing, checking and recording...",
  ResultExtras: HoerenVocabulary,
} as const;

export function ResultIcon({ correct }: { correct: boolean | undefined }) {
  if (correct === undefined) return null;
  return correct ? <CheckCircleIcon color="success" /> : <CancelIcon color="error" />;
}

export function Explanation({ text }: { text: string | undefined }) {
  if (!text) return null;
  return (
    <Typography variant="body2" color="text.secondary" fontStyle="italic" mt={1}>
      {text}
    </Typography>
  );
}
