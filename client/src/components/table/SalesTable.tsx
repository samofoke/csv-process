import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Paper,
  Stack,
  Typography,
  TextField,
  Select,
  MenuItem,
  Button,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Alert,
  CircularProgress,
  LinearProgress,
} from "@mui/material";
import type { Edge, PageInfo, SalesFilter } from "../../types/types";
import { gql } from "../../lib/graphql";

const SALES_PAGE_QUERY = `
query SalesPage($first:Int!,$after:String,$filter:SalesFilter,$direction:SortDirection){
  salesPage(first:$first, after:$after, filter:$filter, direction:$direction){
    edges{
      cursor
      node{
        orderId region country itemType salesChannel orderPriority
        orderDate shipDate unitsSold unitPrice unitCost totalRevenue totalCost totalProfit
      }
    }
    pageInfo{ endCursor hasNextPage }
  }
}
`;

function fmt(n: number | undefined | null) {
  if (n === undefined || n === null) return "";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(
    n
  );
}
function useDebouncedValue<T>(value: T, delay = 350): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return v;
}

type Props = {
  onBackToUpload?: () => void;
  skipInitialProbe?: boolean;
};

export default function SalesTable({
  onBackToUpload,
  skipInitialProbe,
}: Props) {
  const [edges, setEdges] = useState<Edge[]>([]);
  const [pageInfo, setPageInfo] = useState<PageInfo>({
    endCursor: null,
    hasNextPage: true,
  });
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadingTop, setLoadingTop] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // filters
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 350);
  const [country, setCountry] = useState("");
  const [direction, setDirection] = useState<"ASC" | "DESC">("DESC");

  const bottomRef = useRef<HTMLDivElement | null>(null);

  const filter: SalesFilter = useMemo(() => {
    const f: any = {};
    if (debouncedSearch.trim()) f.q = debouncedSearch.trim();
    if (country.trim()) f.country = country.trim();
    return Object.keys(f).length ? f : null;
  }, [debouncedSearch, country]);

  const requestTokenRef = useRef(0);
  const page1AbortRef = useRef<AbortController | null>(null);

  const loadFirstPage = useCallback(async () => {
    page1AbortRef.current?.abort();
    page1AbortRef.current = new AbortController();
    const token = ++requestTokenRef.current;

    setError(null);
    setLoadingTop(true);
    try {
      const data = await gql<{
        salesPage: { edges: Edge[]; pageInfo: PageInfo };
      }>(
        SALES_PAGE_QUERY,
        { first: 50, after: null, filter, direction },
        { signal: page1AbortRef.current.signal }
      );

      if (token !== requestTokenRef.current) return;

      setEdges(data.salesPage.edges);
      setPageInfo(data.salesPage.pageInfo);
    } catch (e: any) {
      if (e?.name !== "AbortError") setError(e?.message ?? String(e));
    } finally {
      if (token === requestTokenRef.current) setLoadingTop(false);
    }
  }, [filter, direction]);

  const loadMore = useCallback(async () => {
    if (loadingMore || !pageInfo.hasNextPage) return;
    setLoadingMore(true);
    setError(null);
    try {
      const data = await gql<{
        salesPage: { edges: Edge[]; pageInfo: PageInfo };
      }>(SALES_PAGE_QUERY, {
        first: 50,
        after: pageInfo.endCursor,
        filter,
        direction,
      });
      setEdges((prev) => {
        const seen = new Set(prev.map((e) => e.cursor));
        const add = data.salesPage.edges.filter((e) => !seen.has(e.cursor));
        return [...prev, ...add];
      });
      setPageInfo(data.salesPage.pageInfo);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, pageInfo, filter, direction]);

  useEffect(() => {
    if (skipInitialProbe) {
      loadFirstPage();
      return;
    }
    (async () => {
      try {
        const data = await gql<{
          salesPage: { edges: Edge[]; pageInfo: PageInfo };
        }>(SALES_PAGE_QUERY, {
          first: 1,
          after: null,
          filter: null,
          direction: "DESC",
        });
        if (data.salesPage.edges.length === 0) {
          onBackToUpload?.();
        } else {
          loadFirstPage();
        }
      } catch {
        loadFirstPage();
      }
    })();
  }, []);

  useEffect(() => {
    const el = bottomRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && loadMore(),
      { root: null, rootMargin: "800px 0px 800px 0px", threshold: 0 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [loadMore]);

  useEffect(() => {
    if (
      requestTokenRef.current === 0 &&
      edges.length === 0 &&
      pageInfo.endCursor === null
    )
      return;
    loadFirstPage();
  }, [debouncedSearch, country, direction]);

  async function applyFilters() {
    loadFirstPage();
  }

  return (
    <Stack spacing={4}>
      <Paper elevation={1} sx={{ p: 2, borderRadius: 3 }}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
        >
          <Typography variant="h6">Salees reacords information</Typography>
          {onBackToUpload && (
            <Button variant="text" onClick={onBackToUpload}>
              Import another file
            </Button>
          )}
        </Stack>
      </Paper>

      <Paper elevation={1} sx={{ p: 2, borderRadius: 3 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <TextField
            label="Search Live"
            placeholder="region or country"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            fullWidth
          />
          <TextField
            label="Country Exact Name"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            sx={{ minWidth: 220 }}
          />
        </Stack>
      </Paper>

      <Paper
        elevation={2}
        sx={{ borderRadius: 3, overflow: "hidden", position: "relative" }}
      >
        {/* TOP STRAIGHT LINE LOADER (only for page-1 reloads) */}
        {loadingTop && (
          <LinearProgress
            sx={{
              position: "sticky",
              top: 0,
              left: 0,
              right: 0,
              zIndex: 2,
            }}
          />
        )}

        <TableContainer sx={{ maxHeight: "70vh" }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                {[
                  "Order ID",
                  "Order Date",
                  "Country",
                  "Region",
                  "Item",
                  "Units",
                  "Unit Price",
                  "Unit Cost",
                  "Revenue",
                  "Cost",
                  "Profit",
                ].map((h) => (
                  <TableCell key={h} sx={{ fontWeight: 600 }}>
                    {h}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {edges.map(({ cursor, node }) => (
                <TableRow key={cursor} hover>
                  <TableCell>{node.orderId}</TableCell>
                  <TableCell>{node.orderDate}</TableCell>
                  <TableCell>{node.country}</TableCell>
                  <TableCell>{node.region}</TableCell>
                  <TableCell>{node.itemType}</TableCell>
                  <TableCell>{fmt(node.unitsSold)}</TableCell>
                  <TableCell>{fmt(node.unitPrice)}</TableCell>
                  <TableCell>{fmt(node.unitCost)}</TableCell>
                  <TableCell>{fmt(node.totalRevenue)}</TableCell>
                  <TableCell>{fmt(node.totalCost)}</TableCell>
                  <TableCell>{fmt(node.totalProfit)}</TableCell>
                </TableRow>
              ))}
              {/* sentinel */}
              <TableRow>
                <TableCell colSpan={11}>
                  <div ref={bottomRef} style={{ height: 1 }} />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>

        <Stack direction="row" alignItems="center" spacing={2} sx={{ p: 1.5 }}>
          {loadingMore && (
            <>
              <CircularProgress size={20} />
              <Typography>Loading…</Typography>
            </>
          )}
          {!loadingMore && edges.length === 0 && !pageInfo.hasNextPage && (
            <Typography color="text.secondary">No results.</Typography>
          )}
          {error && (
            <Alert severity="error" sx={{ ml: "auto" }}>
              {error}
            </Alert>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
