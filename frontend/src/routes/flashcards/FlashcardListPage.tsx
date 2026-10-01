import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import SchoolIcon from "@mui/icons-material/School";
import {
  Alert,
  Box,
  Button,
  Chip,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { useDeleteVocabulary, useVocabularyList } from "../../hooks/useFlashcards";

const cellTextSx = {
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
} as const;

export function FlashcardListPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    const handle = setTimeout(() => {
      setSearch(searchInput);
      setPage(0);
    }, 300);
    return () => clearTimeout(handle);
  }, [searchInput]);

  const { data, isLoading, isError } = useVocabularyList({
    search: search || undefined,
    page: page + 1,
    pageSize,
  });
  const deleteVocabulary = useDeleteVocabulary();

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2} mb={3}>
        <Typography variant="h4">Flashcards</Typography>
        <Stack direction="row" spacing={1}>
          <Button
            component={RouterLink}
            to="/flashcards/study"
            variant="contained"
            color="secondary"
            startIcon={<SchoolIcon />}
          >
            Study
          </Button>
          <Button component={RouterLink} to="/flashcards/add" variant="outlined">
            + Add vocabulary
          </Button>
          <Button component={RouterLink} to="/flashcards/upload" variant="outlined">
            Upload file
          </Button>
        </Stack>
      </Stack>

      <TextField
        label="Search word or translation"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        fullWidth
        size="small"
        sx={{ mb: 2 }}
      />

      {isError && <Alert severity="error">Failed to load vocabulary.</Alert>}

      {!isLoading && data && data.total === 0 && (
        <Typography color="text.secondary">
          {search ? "No vocabulary matches your search." : "No vocabulary yet. Add your first word above."}
        </Typography>
      )}

      {data && data.total > 0 && (
        <Paper variant="outlined">
          <TableContainer>
            <Table size="small" sx={{ tableLayout: "fixed" }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: "22%" }}>Word</TableCell>
                  <TableCell sx={{ width: "12%" }}>Type</TableCell>
                  <TableCell sx={{ width: "26%" }}>Translation</TableCell>
                  <TableCell sx={{ width: "30%" }}>Progress</TableCell>
                  <TableCell sx={{ width: "10%" }} align="right" />
                </TableRow>
              </TableHead>
              <TableBody>
                {data.items.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell sx={cellTextSx} title={`${item.article ? `${item.article} ` : ""}${item.word}`}>
                      {item.article ? `${item.article} ` : ""}
                      {item.word}
                    </TableCell>
                    <TableCell sx={cellTextSx}>{item.part_of_speech}</TableCell>
                    <TableCell sx={cellTextSx} title={item.translation}>
                      {item.translation}
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        <Chip size="small" color="success" label={`✓ ${item.correct_count}`} />
                        {item.incorrect_hard_count > 0 && (
                          <Chip size="small" color="error" label={`hard ${item.incorrect_hard_count}`} />
                        )}
                        {item.incorrect_moderate_count > 0 && (
                          <Chip
                            size="small"
                            color="warning"
                            label={`mod ${item.incorrect_moderate_count}`}
                          />
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => deleteVocabulary.mutate(item.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={data.total}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(e) => {
              setPageSize(parseInt(e.target.value, 10));
              setPage(0);
            }}
            rowsPerPageOptions={[10, 20, 50, 100]}
          />
        </Paper>
      )}
    </Box>
  );
}
