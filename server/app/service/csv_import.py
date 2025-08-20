from __future__ import annotations

import io
import time
import logging
from typing import Dict, Tuple, Any

from app.config.db.connection import get_cursor

log = logging.getLogger("app.service.csv_import")


DDL_SALES = """
CREATE TABLE IF NOT EXISTS sales (
  order_id        BIGINT PRIMARY KEY,
  region          TEXT    NOT NULL,
  country         TEXT    NOT NULL,
  item_type       TEXT    NOT NULL,
  sales_channel   TEXT    NOT NULL,
  order_priority  TEXT    NOT NULL,
  order_date      DATE    NOT NULL,
  ship_date       DATE    NOT NULL,
  units_sold      INTEGER NOT NULL,
  unit_price      NUMERIC(10,2)  NOT NULL,
  unit_cost       NUMERIC(10,2)  NOT NULL,
  total_revenue   NUMERIC(18,2)  NOT NULL,
  total_cost      NUMERIC(18,2)  NOT NULL,
  total_profit    NUMERIC(18,2)  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sales_order_date ON sales(order_date);
CREATE INDEX IF NOT EXISTS idx_sales_country    ON sales(country);
CREATE INDEX IF NOT EXISTS idx_sales_item_type  ON sales(item_type);
"""

DDL_STAGE = """
CREATE TEMP TABLE sales_import (
  "Region"          TEXT, "Country"        TEXT, "Item Type"     TEXT,
  "Sales Channel"   TEXT, "Order Priority" TEXT,
  "Order Date"      TEXT, "Order ID"       TEXT, "Ship Date"     TEXT,
  "Units Sold"      TEXT, "Unit Price"     TEXT, "Unit Cost"     TEXT,
  "Total Revenue"   TEXT, "Total Cost"     TEXT, "Total Profit"  TEXT
) ON COMMIT DROP;
"""

COPY_STAGE = "COPY sales_import FROM STDIN WITH (FORMAT csv, HEADER true)"

VALID_TYPED_CTE = """
WITH typed AS (
  SELECT
    "Region"         AS region,
    "Country"        AS country,
    "Item Type"      AS item_type,
    "Sales Channel"  AS sales_channel,
    "Order Priority" AS order_priority,
    to_date("Order Date", 'MM/DD/YYYY')  AS order_date,
    ("Order ID")::bigint                 AS order_id,
    to_date("Ship Date", 'MM/DD/YYYY')   AS ship_date,
    ("Units Sold")::int                  AS units_sold,
    ("Unit Price")::numeric(10,2)        AS unit_price,
    ("Unit Cost")::numeric(10,2)         AS unit_cost,
    ("Total Revenue")::numeric(18,2)     AS total_revenue,
    ("Total Cost")::numeric(18,2)        AS total_cost,
    ("Total Profit")::numeric(18,2)      AS total_profit
  FROM sales_import
  WHERE "Order ID" ~ '^[0-9]+$'
    AND "Units Sold" ~ '^[0-9]+$'
    AND "Unit Price" ~ '^[0-9]+(\\.[0-9]+)?$'
    AND "Unit Cost" ~ '^[0-9]+(\\.[0-9]+)?$'
    AND "Total Revenue" ~ '^[0-9]+(\\.[0-9]+)?$'
    AND "Total Cost" ~ '^[0-9]+(\\.[0-9]+)?$'
    AND "Total Profit" ~ '^-?[0-9]+(\\.[0-9]+)?$'
)
"""

COUNT_TOTAL = "SELECT COUNT(*) FROM sales_import;"
COUNT_VALID = VALID_TYPED_CTE + "SELECT COUNT(*) FROM typed;"
COUNT_DUP_IN_FILE = """
SELECT COALESCE(COUNT(*) - COUNT(DISTINCT NULLIF("Order ID", '')), 0) AS dup_in_file
FROM sales_import;
"""

INSERT_FROM_TYPED_DO_NOTHING = VALID_TYPED_CTE + """
INSERT INTO sales (
  region, country, item_type, sales_channel, order_priority,
  order_date, order_id, ship_date, units_sold,
  unit_price, unit_cost, total_revenue, total_cost, total_profit
)
SELECT region, country, item_type, sales_channel, order_priority,
       order_date, order_id, ship_date, units_sold,
       unit_price, unit_cost, total_revenue, total_cost, total_profit
FROM typed
ON CONFLICT (order_id) DO NOTHING
RETURNING 1;
"""

INSERT_FROM_TYPED_DO_UPDATE = VALID_TYPED_CTE + """
INSERT INTO sales (
  region, country, item_type, sales_channel, order_priority,
  order_date, order_id, ship_date, units_sold,
  unit_price, unit_cost, total_revenue, total_cost, total_profit
)
SELECT region, country, item_type, sales_channel, order_priority,
       order_date, order_id, ship_date, units_sold,
       unit_price, unit_cost, total_revenue, total_cost, total_profit
FROM typed
ON CONFLICT (order_id) DO UPDATE SET
  region        = EXCLUDED.region,
  country       = EXCLUDED.country,
  item_type     = EXCLUDED.item_type,
  sales_channel = EXCLUDED.sales_channel,
  order_priority= EXCLUDED.order_priority,
  order_date    = EXCLUDED.order_date,
  ship_date     = EXCLUDED.ship_date,
  units_sold    = EXCLUDED.units_sold,
  unit_price    = EXCLUDED.unit_price,
  unit_cost     = EXCLUDED.unit_cost,
  total_revenue = EXCLUDED.total_revenue,
  total_cost    = EXCLUDED.total_cost,
  total_profit  = EXCLUDED.total_profit
RETURNING 1;
"""

def import_sales_csv(upload_file: Any, source: str) -> Tuple[int, float]:
    
    result = import_sales_csv_detailed(upload_file, source)
    return result["inserted"], result["duration_ms"]


def import_sales_csv_detailed(
    upload_file: Any,
    source: str,
    *,
    update_on_conflict: bool = False,
    speed_optimize: bool = True,
) -> Dict[str, Any]:
    
    start = time.perf_counter()

    with get_cursor() as cur:

        if speed_optimize:
            cur.execute("SET LOCAL synchronous_commit = off")

        cur.execute(DDL_SALES)

        cur.execute(DDL_STAGE)

        file_obj = getattr(upload_file, "file", upload_file)
        if hasattr(file_obj, "seek"):
            try:
                file_obj.seek(0)
            except Exception:
                pass

        text_stream = io.TextIOWrapper(file_obj, encoding="utf-8", newline="")
        with cur.copy(COPY_STAGE) as cp:
            for chunk in iter(lambda: text_stream.read(1024 * 1024), ""):
                if not chunk:
                    break
                cp.write(chunk)

        cur.execute(COUNT_TOTAL)
        total_rows = int(cur.fetchone()[0])

        cur.execute(COUNT_VALID)
        valid_rows = int(cur.fetchone()[0])

        cur.execute(COUNT_DUP_IN_FILE)
        dup_in_file = int(cur.fetchone()[0] or 0)

        insert_sql = (
            INSERT_FROM_TYPED_DO_UPDATE if update_on_conflict else INSERT_FROM_TYPED_DO_NOTHING
        )
        cur.execute(insert_sql)
        inserted = int(cur.rowcount or 0)

        invalid_rows = max(0, total_rows - valid_rows)
        skipped_conflicts = max(0, valid_rows - inserted)

    duration_ms = (time.perf_counter() - start) * 1000.0

    payload: Dict[str, Any] = {
        "inserted": inserted,
        "skipped_conflicts": skipped_conflicts,
        "dup_in_file": dup_in_file,
        "invalid_rows": invalid_rows,
        "total_rows": total_rows,
        "duration_ms": duration_ms,
        "source": source,
        "update_mode": "DO_UPDATE" if update_on_conflict else "DO_NOTHING",
    }
    log.info(
        "Imported CSV source=%s total=%d valid=%d inserted=%d dup_in_file=%d skipped_conflicts=%d invalid=%d in %.2f ms",
        source, total_rows, valid_rows, inserted, dup_in_file, skipped_conflicts, invalid_rows, duration_ms
    )
    return payload

