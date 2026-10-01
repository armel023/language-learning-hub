import { useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Paper,
} from "@mui/material";

import { useConfirmExtraction, useUploadFile } from "../../hooks/useVocabExtraction";
import type { ExtractedVocabEntry, VocabExtractionJob } from "../../types/api";

interface ReviewRow extends ExtractedVocabEntry {
  included: boolean;
}

export function FlashcardUploadPage() {
  const navigate = useNavigate();
  const uploadFile = useUploadFile();
  const confirmExtraction = useConfirmExtraction();

  const [job, setJob] = useState<VocabExtractionJob | null>(null);
  const [rows, setRows] = useState<ReviewRow[]>([]);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setJob(null);
    setRows([]);
    uploadFile.mutate(file, {
      onSuccess: (result) => {
        setJob(result);
        const entries = result.raw_ai_output?.entries ?? [];
        setRows(entries.map((entry) => ({ ...entry, included: true })));
      },
    });
  }

  function updateRow(index: number, fields: Partial<ReviewRow>) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...fields } : row)));
  }

  function handleConfirm() {
    if (!job) return;
    const entries = rows.filter((row) => row.included).map(({ included, ...entry }) => entry);
    confirmExtraction.mutate({ jobId: job.id, entries }, { onSuccess: () => navigate("/flashcards") });
  }

  return (
    <Box>
      <Typography variant="h4" mb={1}>
        Upload file for vocabulary extraction
      </Typography>
      <Typography color="text.secondary" mb={2}>
        Upload a PDF, Word document, or text file. AI will suggest vocabulary to add.
      </Typography>

      <Button variant="outlined" component="label" startIcon={<UploadFileIcon />}>
        Choose file
        <input type="file" hidden accept=".pdf,.docx,.txt" onChange={handleFileChange} />
      </Button>

      {uploadFile.isPending && (
        <Stack direction="row" spacing={1} alignItems="center" mt={2}>
          <CircularProgress size={20} />
          <Typography>Uploading and extracting vocabulary... this can take a minute for large files.</Typography>
        </Stack>
      )}
      {uploadFile.isError && <Alert severity="error" sx={{ mt: 2 }}>Upload failed. Please try again.</Alert>}

      {job?.status === "failed" && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Extraction failed: {job.error_message}
        </Alert>
      )}

      {job?.status === "completed" && job.error_message && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {job.error_message}
        </Alert>
      )}

      {job?.status === "completed" && rows.length === 0 && (
        <Typography sx={{ mt: 2 }}>No vocabulary was found in this file.</Typography>
      )}

      {job?.status === "completed" && rows.length > 0 && (
        <Box mt={3}>
          <Typography variant="h5" mb={2}>
            Review extracted vocabulary ({rows.length} found)
          </Typography>
          <Paper variant="outlined">
            <TableContainer sx={{ maxHeight: 500 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">Include</TableCell>
                    <TableCell>Word</TableCell>
                    <TableCell>Article</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Translation</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row, index) => (
                    <TableRow key={index} hover>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={row.included}
                          onChange={(e) => updateRow(index, { included: e.target.checked })}
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          variant="standard"
                          value={row.word}
                          onChange={(e) => updateRow(index, { word: e.target.value })}
                        />
                      </TableCell>
                      <TableCell>{row.article ?? "-"}</TableCell>
                      <TableCell>{row.part_of_speech}</TableCell>
                      <TableCell>
                        <TextField
                          variant="standard"
                          value={row.translation}
                          onChange={(e) => updateRow(index, { translation: e.target.value })}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>

          <Button
            onClick={handleConfirm}
            variant="contained"
            disabled={confirmExtraction.isPending}
            sx={{ mt: 2 }}
          >
            {confirmExtraction.isPending ? "Saving..." : "Confirm & Save"}
          </Button>

          {confirmExtraction.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Failed to save vocabulary. Please try again.
            </Alert>
          )}
        </Box>
      )}
    </Box>
  );
}
