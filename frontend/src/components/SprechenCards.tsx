import type { ReactNode } from "react";
import { Box, Grid, Paper, Typography } from "@mui/material";

import type { CalendarEntry, SprechenContent } from "../types/api";

/** The exam card frame: dark/light header strip, a subtitle bar, then the card's content. */
export function GoetheCard({ teil, subtitle, children }: { teil: number; subtitle: string; children: ReactNode }) {
  return (
    <Paper variant="outlined" sx={{ overflow: "hidden", borderColor: "grey.500", height: "100%" }}>
      <Box sx={{ display: "flex", fontSize: { xs: 9, sm: 12 }, fontWeight: "bold", whiteSpace: "nowrap" }}>
        <Box sx={{ bgcolor: "grey.600", color: "white", px: { xs: 0.75, sm: 1 }, py: 0.5, flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
          GOETHE-ZERTIFIKAT A2
        </Box>
        <Box sx={{ bgcolor: "grey.300", px: { xs: 0.75, sm: 1 }, py: 0.5, flex: 1, textAlign: "center", overflow: "hidden", textOverflow: "ellipsis" }}>
          Sprechen Teil {teil}
        </Box>
      </Box>
      <Box sx={{ bgcolor: "grey.200", textAlign: "center", fontSize: 13, fontWeight: "bold", py: 0.5 }}>{subtitle}</Box>
      <Box sx={{ p: { xs: 1.5, sm: 2 } }}>{children}</Box>
    </Paper>
  );
}

function Teil1Cards({ cards }: { cards: string[] }) {
  return (
    <Grid container spacing={1.5}>
      {cards.map((card) => (
        <Grid item xs={6} key={card}>
          <GoetheCard teil={1} subtitle="Fragen zur Person">
            <Typography lang="de" align="center" sx={{ fontWeight: 800, fontSize: { xs: 17, sm: 28 }, py: { xs: 1.5, sm: 3 }, hyphens: "auto", overflowWrap: "break-word" }}>
              {card}
            </Typography>
          </GoetheCard>
        </Grid>
      ))}
    </Grid>
  );
}

function Teil2Card({ question, prompts }: { question: string; prompts: string[] }) {
  const corner = (text: string | undefined, align: "left" | "right") => (
    <Typography sx={{ fontWeight: 800, fontSize: { xs: 16, sm: 20 }, textAlign: align }}>{text}</Typography>
  );
  return (
    <GoetheCard teil={2} subtitle="von sich erzählen">
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1.5, alignItems: "center" }}>
        {corner(prompts[0], "left")}
        {corner(prompts[1], "right")}
        <Box sx={{ gridColumn: "1 / span 2", border: 1, borderColor: "grey.500", borderRadius: 2, p: 1.5, mx: { xs: 0, sm: 4 } }}>
          <Typography align="center" sx={{ fontWeight: 800, fontSize: { xs: 18, sm: 22 } }}>
            {question}
          </Typography>
        </Box>
        {corner(prompts[2], "left")}
        {corner(prompts[3], "right")}
      </Box>
    </GoetheCard>
  );
}

function TerminCalendar({ day, calendar }: { day: string; calendar: CalendarEntry[] }) {
  const hours = Array.from({ length: 15 }, (_, i) => 7 + i);
  const entryAt = (hour: number) => calendar.find((e) => e.start === hour);
  const covered = (hour: number) => calendar.some((e) => e.start < hour && hour < e.end);
  return (
    <Paper variant="outlined" sx={{ p: 1.5, maxWidth: 420 }}>
      <Typography fontWeight="bold" mb={1}>
        {day}
      </Typography>
      {hours.map((hour) => {
        const entry = entryAt(hour);
        return (
          <Box key={hour} sx={{ display: "flex", borderTop: 1, borderColor: "divider", minHeight: 28 }}>
            <Box sx={{ width: 52, flexShrink: 0, bgcolor: hour % 2 ? "grey.100" : "grey.300", fontSize: 13, px: 1, py: 0.5 }}>
              {hour}.00
            </Box>
            <Box sx={{ px: 1, py: 0.5, fontStyle: "italic", fontFamily: "'Segoe Print', 'Comic Sans MS', cursive" }}>
              {entry ? `${entry.text}${entry.end - entry.start > 1 ? ` (bis ${entry.end}.00)` : ""}` : covered(hour) ? "⋮" : ""}
            </Box>
          </Box>
        );
      })}
    </Paper>
  );
}

function PlanenMap({ center, points }: { center: string; points: string[] }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5, py: 1 }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 1 }}>
        {[...points, "…?"].map((p) => (
          <Paper key={p} variant="outlined" sx={{ px: 2, py: 1, fontWeight: "bold", borderColor: "grey.600" }}>
            {p}
          </Paper>
        ))}
      </Box>
      <Box sx={{ border: 2, borderColor: "grey.700", borderRadius: "50%", px: 5, py: 2 }}>
        <Typography sx={{ fontWeight: 800, fontSize: 26 }}>{center}</Typography>
      </Box>
    </Box>
  );
}

/** The candidate's card(s) for any Sprechen Teil. */
export function SprechenCardView({ teil, content }: { teil: number; content: SprechenContent }) {
  if ("cards" in content) return <Teil1Cards cards={content.cards} />;
  if ("question" in content) return <Teil2Card question={content.question} prompts={content.prompts} />;
  if (content.variant === "termin") return <TerminCalendar day={content.day} calendar={content.calendar} />;
  return teil === 3 ? <PlanenMap center={content.center} points={content.points} /> : null;
}

/** The exam's instruction line for each Teil. */
export function instructionFor(teil: number, content: SprechenContent): string {
  if (teil === 1) {
    return "Sie bekommen vier Karten und stellen mit diesen Karten vier Fragen. Ihr Partner antwortet. Dann stellt Ihr Partner vier Fragen und Sie antworten (2–3 Sätze).";
  }
  if (teil === 2) return "Sie bekommen eine Karte und erzählen etwas über Ihr Leben. Sprechen Sie zu allen Punkten.";
  return "situation" in content ? content.situation : "";
}
