import { Link as RouterLink } from "react-router-dom";
import { Box, Card, CardActionArea, CardContent, Grid, Typography } from "@mui/material";

const TILES = [
  {
    teil: 1,
    path: "/schreiben/teil1",
    description: "Write a short informal message (20-30 words) to a friend, covering 3 points.",
  },
  {
    teil: 2,
    path: "/schreiben/teil2",
    description: "Write a short semi-formal email (30-40 words), covering 3 points.",
  },
];

export function SchreibenHomePage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Schreiben
      </Typography>
      <Typography color="text.secondary" mb={3}>
        Choose a Teil to practice. Your answer is graded by AI with feedback and corrections.
      </Typography>

      <Grid container spacing={2}>
        {TILES.map((tile) => (
          <Grid key={tile.teil} item xs={12} sm={6}>
            <Card variant="outlined">
              <CardActionArea component={RouterLink} to={tile.path}>
                <CardContent>
                  <Typography variant="h6" mb={1}>
                    Teil {tile.teil}
                  </Typography>
                  <Typography color="text.secondary">{tile.description}</Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
