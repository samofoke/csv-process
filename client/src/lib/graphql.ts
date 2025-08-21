import type { ImportResult } from "../types/types";

const GQL_ENDPOINT = "http://localhost:5010/graphql";

export async function gql<T>(
  query: string,
  variables: Record<string, any>,
  opts?: { signal?: AbortSignal },
): Promise<T> {
  const res = await fetch(GQL_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query, variables }),
    credentials: "include",
    signal: opts?.signal,
  });
  const json = await res.json();
  if (json.errors) {
    throw new Error(json.errors.map((e: any) => e.message).join(" | "));
  }
  return json.data as T;
}

const HAS_DATA_QUERY = `
query HasSales {
  salesPage(first: 1, after: null, filter: null, direction: DESC) { edges { cursor } }
}
`;

const IMPORT_MUTATION = `
mutation($file: Upload!, $source: String!, $up: Boolean){
  importSales(file:$file, source:$source, updateOnConflict:$up){
    inserted
    skippedConflicts
    dupInFile
    invalidRows
    totalRows
    durationMs
    source
    updateMode
  }
}
`;

export async function uploadImport(
  file: File,
  opts: { source?: string; upsert?: boolean } = {},
): Promise<ImportResult> {
  const source = (opts.source ?? file.name).trim();
  const up = !!opts.upsert;

  const fd = new FormData();
  fd.append(
    "operations",
    JSON.stringify({
      query: IMPORT_MUTATION,
      variables: { file: null, source, up },
    }),
  );
  fd.append("map", JSON.stringify({ "0": ["variables.file"] }));
  fd.append("0", file, file.name);

  const res = await fetch(GQL_ENDPOINT, {
    method: "POST",
    body: fd,
    credentials: "include",
  });

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    const text = await res.text();
    throw new Error(
      `Unexpected response (${res.status}): ${text.slice(0, 400)}`,
    );
  }
  const json = await res.json();
  if (json.errors?.length)
    throw new Error(json.errors.map((e: any) => e.message).join(" | "));
  const data = json.data?.importSales as ImportResult | undefined;
  if (!data) throw new Error("No data.importSales in response");
  return data;
}

export async function hasAnySales(): Promise<boolean> {
  const data = await gql<{ salesPage: { edges: Array<{ cursor: string }> } }>(
    HAS_DATA_QUERY,
    {},
  );
  return data.salesPage.edges.length > 0;
}
