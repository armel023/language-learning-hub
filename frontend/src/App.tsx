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
      <AppBar position="sticky" color="primary">
        {/* Phones: title on its own row, tabs below and horizontally scrollable. Desktop: one row. */}
        <Toolbar
          sx={{
            flexDirection: { xs: "column", md: "row" },
            alignItems: { xs: "stretch", md: "center" },
            px: { xs: 0, md: 3 },
            minHeight: { xs: "auto", md: 64 },
          }}
        >
          <Typography variant="h6" noWrap sx={{ mr: { md: 4 }, px: { xs: 2, md: 0 }, pt: { xs: 1, md: 0 } }}>
            A2 Deutsch Hub
          </Typography>
          <Tabs
            value={currentTabValue(location.pathname)}
            onChange={(_, value: string) => navigate(value)}
            textColor="inherit"
            indicatorColor="secondary"
            variant="scrollable"
            scrollButtons={false}
            sx={{ minHeight: { xs: 44, md: 64 }, "& .MuiTab-root": { minHeight: { xs: 44, md: 64 }, minWidth: 0, px: 2 } }}
          >
            {NAV_ITEMS.map((item) => (
              <Tab key={item.path} label={item.label} value={item.path} />
            ))}
          </Tabs>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: { xs: 2, sm: 4 }, px: { xs: 1.5, sm: 3 } }}>
        <Outlet />
      </Container>
    </Box>
  );
}
