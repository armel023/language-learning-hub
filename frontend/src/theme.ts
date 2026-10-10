import { createTheme, responsiveFontSizes } from "@mui/material/styles";

// responsiveFontSizes scales headings down on small screens (an h4 title would otherwise wrap
// awkwardly on a phone).
export const theme = responsiveFontSizes(
  createTheme({
    palette: {
      mode: "light",
      primary: { main: "#2f5f8f" },
      secondary: { main: "#b4654a" },
    },
    shape: {
      borderRadius: 8,
    },
  }),
);
