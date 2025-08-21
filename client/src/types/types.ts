export type SalesNode = {
  orderId: string;
  region: string;
  country: string;
  itemType: string;
  salesChannel: string;
  orderPriority: string;
  orderDate: string;
  shipDate: string;
  unitsSold: number;
  unitPrice: number;
  unitCost: number;
  totalRevenue: number;
  totalCost: number;
  totalProfit: number;
};

export type Edge = { cursor: string; node: SalesNode };
export type PageInfo = { endCursor?: string | null; hasNextPage: boolean };

export type SalesFilter = {
  q?: string | null;
  country?: string | null;
  itemType?: string | null;
  orderDateFrom?: string | null;
  orderDateTo?: string | null;
} | null;

export type ImportResult = {
  inserted: number;
  skippedConflicts: number;
  dupInFile: number;
  invalidRows: number;
  totalRows: number;
  durationMs: number;
  source: string;
  updateMode: string;
};
