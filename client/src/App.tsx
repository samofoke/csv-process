import { useEffect, useState } from "react";
import {
  CssBaseline,
  Container,
  AppBar,
  Typography,
  Box,
  CircularProgress,
} from "@mui/material";
import UploadCsv from "./components/uploads/UploadCsv";
import SalesTable from "./components/table/SalesTable";
import type { ImportResult } from "./types/types";
import { hasAnySales } from "./lib/graphql";
import "./App.css";

type View = "checking" | "upload" | "table";

export default function App() {
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [view, setView] = useState<View>("checking");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const exists = await hasAnySales();
        if (!cancelled) setView(exists ? "table" : "upload");
      } catch {
        if (!cancelled) setView("upload");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <CssBaseline />
      <AppBar
        position="sticky"
        color="transparent"
        elevation={0}
        sx={{
          backgroundColor: "transparent",
          boxShadow: "none",
          backdropFilter: "saturate(180%) blur(8px)",
        }}
      >
        {importResult && (
          <Typography variant="body2" color="text.secondary">
            Inserted: {importResult.inserted.toLocaleString()} • Duration:{" "}
            {importResult.durationMs.toFixed(0)} ms
          </Typography>
        )}
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 3 }}>
        {view === "checking" && (
          <Box sx={{ py: 8, display: "flex", justifyContent: "center" }}>
            <CircularProgress />
          </Box>
        )}

        {view === "upload" && (
          <UploadCsv
            onSuccess={(r) => {
              setImportResult(r);
              setView("table");
            }}
          />
        )}

        {view === "table" && (
          <Box>
            <SalesTable
              skipInitialProbe
              onBackToUpload={() => {
                setImportResult(null);
                setView("upload");
              }}
            />
          </Box>
        )}
      </Container>
    </>
  );
}
