import { useEffect, useRef, useState } from "react";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import GraphicEqIcon from "@mui/icons-material/GraphicEq";
import { Box, Button, Stack, Typography } from "@mui/material";

const PAUSE_BETWEEN_PLAYS_MS = 2500;

interface AudioPlayerProps {
  src: string;
  /** Exam rule: how often this audio is played (1 or 2). One click plays all repetitions. */
  plays: number;
  /** After submitting: a normal player with unlimited replays. */
  unlocked: boolean;
}

/**
 * Plays an exam recording the way the exam does: once you start it, it plays `plays` times in a
 * row with a short pause, and then it is used up. Unlocked after the attempt is submitted.
 */
export function AudioPlayer({ src, plays, unlocked }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const timerRef = useRef<number | null>(null);
  const [played, setPlayed] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
  }, []);

  if (unlocked) {
    return <Box component="audio" controls src={src} preload="none" sx={{ width: "100%", mt: 1 }} />;
  }

  const usedUp = played >= plays;

  function start() {
    audioRef.current?.play();
    setPlaying(true);
  }

  function handleEnded() {
    const next = played + 1;
    setPlayed(next);
    if (next < plays) {
      timerRef.current = window.setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.currentTime = 0;
          audioRef.current.play();
        }
      }, PAUSE_BETWEEN_PLAYS_MS);
    } else {
      setPlaying(false);
    }
  }

  return (
    <Stack direction="row" spacing={1.5} alignItems="center" mt={1} flexWrap="wrap" useFlexGap>
      <audio ref={audioRef} src={src} preload="auto" onEnded={handleEnded} />
      <Button
        variant={usedUp ? "outlined" : "contained"}
        size="small"
        startIcon={playing ? <GraphicEqIcon /> : <PlayArrowIcon />}
        onClick={start}
        disabled={playing || usedUp}
      >
        {playing ? `Läuft (${Math.min(played + 1, plays)}/${plays})` : usedUp ? "Gehört" : "Abspielen"}
      </Button>
      <Typography variant="caption" color="text.secondary">
        {plays === 2 ? "Sie hören den Text zweimal." : "Sie hören den Text einmal."}
      </Typography>
    </Stack>
  );
}
