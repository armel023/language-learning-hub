import { Link as RouterLink } from "react-router-dom";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

interface TeilTile {
  teil: number;
  path: string;
  title: string;
  description: string;
  available: boolean;
}

const TILES: TeilTile[] = [
  {
    teil: 1,
    path: "/lesen/teil1",
    title: "Teil 1",
    description: "Read a short article in 5 paragraphs and answer 5 multiple-choice questions.",
    available: true,
  },
  {
    teil: 2,
    path: "/lesen/teil2",
    title: "Teil 2",
    description: "Match 5 situations to the correct floor in a department store directory.",
    available: true,
  },
  {
    teil: 3,
    path: "/lesen/teil3",
    title: "Teil 3",
    description: "Read an email and complete 5 sentence stems, one per paragraph.",
    available: true,
  },
  {
    teil: 4,
    path: "/lesen/teil4",
    title: "Teil 4",
    description: "Match 5 situations to the correct advertisement (one has no match).",
    available: true,
  },
];

export function LesenHomePage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Lesen
      </Typography>
      <Typography color="text.secondary" mb={3}>
        Choose a Teil to practice.
      </Typography>

      <Grid container spacing={2}>
        {TILES.map((tile) => (
          <Grid key={tile.teil} item xs={12} sm={6}>
            <Card variant="outlined">
              <CardActionArea component={RouterLink} to={tile.path}>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="h6">{tile.title}</Typography>
                    {!tile.available && <Chip size="small" label="Coming soon" />}
                  </Stack>
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
