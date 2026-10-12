import { Link as RouterLink } from "react-router-dom";
import { Box, Card, CardActionArea, CardContent, Grid, Typography } from "@mui/material";

const TILES = [
  { teil: 1, description: "Five short texts (messages, announcements), each played twice. One question per text." },
  { teil: 2, description: "One conversation, played once. Match five times (6-10) to pictures a-i." },
  { teil: 3, description: "Five short conversations, played once. Pick the right picture; all three are mentioned." },
  { teil: 4, description: "One interview, played twice. Decide Ja or Nein for five statements." },
];

export function HoerenHomePage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Hören
      </Typography>
      <Typography color="text.secondary" mb={3}>
        Choose a Teil to practice. After you submit, you can replay the audio, read the transcript and add
        new words to your flashcards.
      </Typography>
      <Grid container spacing={2}>
        {TILES.map((tile) => (
          <Grid key={tile.teil} item xs={12} sm={6}>
            <Card variant="outlined">
              <CardActionArea component={RouterLink} to={`/hoeren/teil${tile.teil}`}>
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
