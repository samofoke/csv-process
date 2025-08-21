import { useMemo, useState } from "react";
import {
  Paper,
  Stack,
  Typography,
  Button,
  TextField,
  FormControlLabel,
  Switch,
  Alert,
  LinearProgress,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import type { ImportResult } from "../../types/types";
import { uploadImport } from "../../lib/graphql";

type Props = {
  onSuccess: (result: ImportResult) => void;
};

export default function UploadCsv({ onSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState("");
  const [upsert, setUpsert] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pretty = useMemo(() => {
    if (!file) return "";
    const kb = file.size / 1024;
    return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(2)} MB`;
  }, [file]);

  async function handleUpload() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await uploadImport(file, {
        source: source || file.name,
        upsert,
      });
      onSuccess(result);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Paper elevation={2} sx={{ p: 3, borderRadius: 3 }}>
      <Stack spacing={2}>
        <Typography variant="h5">Upload CSV</Typography>

        <Button
          variant="outlined"
          component="label"
          startIcon={<CloudUploadIcon />}
          sx={{ alignSelf: "flex-start" }}
        >
          Choose file
          <input
            type="file"
            accept=".csv,text/csv"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0] || null;
              setFile(f);
              if (f && !source) setSource(f.name);
            }}
          />
        </Button>

        {file && (
          <Typography variant="body2" color="text.secondary">
            Selected: <strong>{file.name}</strong> • {pretty}
          </Typography>
        )}

        <TextField
          label="Source label (optional)"
          value={source}
          onChange={(e) => setSource(e.target.value)}
          fullWidth
        />

        <FormControlLabel
          control={
            <Switch
              checked={upsert}
              onChange={(e) => setUpsert(e.target.checked)}
            />
          }
          label="Update on conflict (upsert)"
        />

        <Stack direction="row" spacing={2} alignItems="center">
          <Button
            variant="contained"
            disabled={!file || busy}
            onClick={handleUpload}
          >
            {busy ? "Uploading…" : "Upload"}
          </Button>
          {busy && <LinearProgress sx={{ flex: 1 }} />}
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        <Typography variant="body2" color="text.secondary">
          The file is streamed to PostgreSQL via COPY (no full-file buffering).
        </Typography>
      </Stack>
    </Paper>
  );
}
