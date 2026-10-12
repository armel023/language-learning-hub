import { Box, Card, CardActionArea, Typography } from "@mui/material";

import type { IconPicture } from "../types/api";

interface PictureCardProps {
  picture: IconPicture;
  label?: string;
  selected?: boolean;
  /** After submitting: highlight the right answer green and a wrong selection red. */
  state?: "correct" | "wrong";
  dimmed?: boolean;
  onClick?: () => void;
}

/** An exam "picture" rendered as a large emoji with a short German caption. */
export function PictureCard({ picture, label, selected, state, dimmed, onClick }: PictureCardProps) {
  const borderColor =
    state === "correct" ? "success.main" : state === "wrong" ? "error.main" : selected ? "primary.main" : "divider";
  const body = (
    <Box sx={{ p: 1, textAlign: "center", opacity: dimmed ? 0.45 : 1 }}>
      {label && (
        <Typography variant="caption" fontWeight="bold" color="text.secondary">
          {label}
        </Typography>
      )}
      <Typography sx={{ fontSize: { xs: 34, sm: 40 }, lineHeight: 1.2 }} aria-hidden>
        {picture.emoji}
      </Typography>
      <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
        {picture.caption}
      </Typography>
    </Box>
  );
  return (
    <Card
      variant="outlined"
      sx={{ height: "100%", borderWidth: selected || state ? 2 : 1, borderColor }}
    >
      {onClick ? <CardActionArea onClick={onClick} sx={{ height: "100%" }}>{body}</CardActionArea> : body}
    </Card>
  );
}
