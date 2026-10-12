import { Link as RouterLink } from "react-router-dom";
import { Alert, Box, Card, CardActionArea, CardContent, Grid, Typography } from "@mui/material";

const TILES = [
  { teil: 1, description: "Fragen zur Person: ask four questions with your cards, then answer your partner's four." },
  { teil: 2, description: "Von sich erzählen: talk about your life using one card. Cover every point." },
  { teil: 3, description: "Gemeinsam etwas planen: find a time or plan something with your partner." },
];

export function SprechenHomePage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Sprechen
      </Typography>
      <Typography color="text.secondary" mb={2}>
        A live voice conversation with an AI exam partner, then feedback from the transcript.
      </Typography>
      {!window.isSecureContext && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          The microphone only works on a secure page. Open the app via its HTTPS Tailscale address, or via localhost on
          this computer.
        </Alert>
      )}
      <Grid container spacing={2}>
        {TILES.map((tile) => (
          <Grid key={tile.teil} item xs={12} sm={4}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardActionArea component={RouterLink} to={`/sprechen/teil${tile.teil}`} sx={{ height: "100%" }}>
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
