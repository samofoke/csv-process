from __future__ import annotations
import base64, json
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from app.config.db.connection import get_cursor


def _enc(od: date, oid: int) -> str:
    return base64.urlsafe_b64encode(
        json.dumps({"od": od.isoformat(), "id": int(oid)}).encode("utf-8")
    ).decode("ascii")

def _dec(cur: str) -> Tuple[date, int]:
    d = json.loads(base64.urlsafe_b64decode(cur.encode("ascii")).decode("utf-8"))
    return date.fromisoformat(d["od"]), int(d["id"])

def _where(f: Optional[Dict[str, Any]]) -> Tuple[str, List[Any]]:
    if not f: return "", []
    c, p = [], []
    if (v := f.get("region")):         c += ["region = %s"];         p += [v]
    if (v := f.get("country")):        c += ["country = %s"];        p += [v]
    if (v := f.get("item_type")):      c += ["item_type = %s"];      p += [v]
    if (v := f.get("sales_channel")):  c += ["sales_channel = %s"];  p += [v]
    if (v := f.get("order_priority")): c += ["order_priority = %s"]; p += [v]
    if (v := f.get("order_date_from")):c += ["order_date >= %s"];    p += [v]
    if (v := f.get("order_date_to")):  c += ["order_date <= %s"];    p += [v]
    if (v := f.get("min_profit")):     c += ["total_profit >= %s"];  p += [v]
    if (v := f.get("max_profit")):     c += ["total_profit <= %s"];  p += [v]
    if (v := f.get("q")):              c += ["(country ILIKE %s OR region ILIKE %s OR item_type ILIKE %s)"]; p += [f"%{v}%", f"%{v}%", f"%{v}%"]
    return ("WHERE " + " AND ".join(c)) if c else "", p


def query_sales_page(first: int, after: Optional[str], filter: Optional[Dict[str, Any]], direction: str = "DESC") -> Dict[str, Any]:
    first = max(1, min(first, 200))
    direction = "ASC" if str(direction).upper() == "ASC" else "DESC"

    ws, params = _where(filter)
    cur_pred, cur_params = "", []

    if after:
        od, oid = _dec(after)
        comp = "<" if direction == "DESC" else ">"
        joiner = "AND" if ws else "WHERE"
        cur_pred = f" {joiner} (order_date, order_id) {comp} (%s, %s)"
        cur_params = [od, oid]

    order_sql = f"ORDER BY order_date {direction}, order_id {direction}"
    sql = f"""
      SELECT order_id, region, country, item_type, sales_channel, order_priority,
             order_date, ship_date, units_sold, unit_price, unit_cost,
             total_revenue, total_cost, total_profit
      FROM sales
      {ws}{cur_pred}
      {order_sql}
      LIMIT %s
    """
    params2 = params + cur_params + [first + 1]
    with get_cursor() as cur:
        cur.execute(sql, params2)
        rows = cur.fetchall()

    has_next = len(rows) > first
    if has_next:
        rows = rows[:first]

    def node(r):
        to_f = lambda x: float(x) if isinstance(x, Decimal) else x
        return {
            "order_id": r[0], "region": r[1], "country": r[2], "item_type": r[3],
            "sales_channel": r[4], "order_priority": r[5],
            "order_date": r[6].isoformat(), "ship_date": r[7].isoformat(),
            "units_sold": int(r[8]), "unit_price": to_f(r[9]), "unit_cost": to_f(r[10]),
            "total_revenue": to_f(r[11]), "total_cost": to_f(r[12]), "total_profit": to_f(r[13]),
        }

    edges = [{"cursor": _enc(r[6], r[0]), "node": node(r)} for r in rows]
    return {
        "edges": edges,
        "pageInfo": {"endCursor": (edges[-1]["cursor"] if edges else after), "hasNextPage": has_next},
    }


def get_sales_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute("""
          SELECT order_id, region, country, item_type, sales_channel, order_priority,
                 order_date, ship_date, units_sold, unit_price, unit_cost,
                 total_revenue, total_cost, total_profit
          FROM sales WHERE order_id = %s
        """, [order_id])
        r = cur.fetchone()
    if not r:
        return None
    to_f = lambda x: float(x) if isinstance(x, Decimal) else x
    return {
        "order_id": r[0], "region": r[1], "country": r[2], "item_type": r[3],
        "sales_channel": r[4], "order_priority": r[5],
        "order_date": r[6].isoformat(), "ship_date": r[7].isoformat(),
        "units_sold": int(r[8]), "unit_price": to_f(r[9]), "unit_cost": to_f(r[10]),
        "total_revenue": to_f(r[11]), "total_cost": to_f(r[12]), "total_profit": to_f(r[13]),
    }

