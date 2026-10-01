import { AppBar, Box, Container, Tab, Tabs, Toolbar, Typography } from "@mui/material";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Flashcards", path: "/flashcards" },
  { label: "Lesen", path: "/lesen" },
  { label: "Hören", path: "/hoeren" },
  { label: "Schreiben", path: "/schreiben" },
  { label: "Sprechen", path: "/sprechen" },
];

function currentTabValue(pathname: string): string {
  const match = NAV_ITEMS.find((item) => pathname.startsWith(item.path));
  return match?.path ?? "/flashcards";
}

export function App() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="static" color="primary">
        <Toolbar>
          <Typography variant="h6" sx={{ mr: 4 }}>
            A2 Deutsch Hub
          </Typography>
          <Tabs
            value={currentTabValue(location.pathname)}
            onChange={(_, value: string) => navigate(value)}
            textColor="inherit"
            indicatorColor="secondary"
          >
            {NAV_ITEMS.map((item) => (
              <Tab key={item.path} label={item.label} value={item.path} />
            ))}
          </Tabs>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
