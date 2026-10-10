import { Box, Typography } from "@mui/material";

import type { ScriptLine } from "../types/api";

/** What was said in a recording, shown after the attempt is submitted. */
export function Transcript({ lines }: { lines: ScriptLine[] | undefined }) {
  if (!lines?.length) return null;
  return (
    <Box sx={{ mt: 1.5, p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}>
      <Typography variant="overline" color="text.secondary">
        Transkript
      </Typography>
      {lines.map((line, i) => (
        <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>
          <Box component="span" sx={{ fontWeight: "bold" }}>
            {line.speaker}:
          </Box>{" "}
          {line.text}
        </Typography>
      ))}
    </Box>
  );
}
