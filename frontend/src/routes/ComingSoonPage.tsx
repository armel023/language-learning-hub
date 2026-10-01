import { Box, Typography } from "@mui/material";

export function ComingSoonPage({ skill }: { skill: string }) {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {skill}
      </Typography>
      <Typography color="text.secondary">This module is coming soon.</Typography>
    </Box>
  );
}
