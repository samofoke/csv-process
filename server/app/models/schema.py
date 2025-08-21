from __future__ import annotations
import strawberry
from typing import Optional, List
from enum import Enum
from strawberry.file_uploads import Upload
from ..config.db.connection import get_cursor, ping
from ..service.csv_import import import_sales_csv_detailed
from ..service.sales_query import query_sales_page, get_sales_by_id

@strawberry.type
class ImportResult:
    inserted: int
    skipped_conflicts: int
    dup_in_file: int
    invalid_rows: int
    total_rows: int
    duration_ms: float
    source: str
    update_mode: str


@strawberry.type
class Sales:
    order_id: strawberry.ID
    region: str
    country: str
    item_type: str
    sales_channel: str
    order_priority: str
    order_date: str
    ship_date: str
    units_sold: int
    unit_price: float
    unit_cost: float
    total_revenue: float
    total_cost: float
    total_profit: float


@strawberry.type
class PageInfo:
    end_cursor: Optional[str] = strawberry.field(name="endCursor", default=None)
    has_next_page: bool       = strawberry.field(name="hasNextPage", default=False)

@strawberry.type
class SalesEdge: cursor: str; node: Sales
@strawberry.type
class SalesConnection:
    edges: List[SalesEdge]
    page_info: PageInfo = strawberry.field(name="pageInfo")

@strawberry.enum
class SortDirection(Enum):
    ASC = "ASC"
    DESC = "DESC"

@strawberry.input
class SalesFilter:
    region: Optional[str] = None
    country: Optional[str] = None
    item_type: Optional[str] = strawberry.field(name="itemType", default=None)
    sales_channel: Optional[str] = strawberry.field(name="salesChannel", default=None)
    order_priority: Optional[str] = strawberry.field(name="orderPriority", default=None)
    order_date_from: Optional[str] = strawberry.field(name="orderDateFrom", default=None)
    order_date_to: Optional[str] = strawberry.field(name="orderDateTo", default=None)
    min_profit: Optional[float] = strawberry.field(name="minProfit", default=None)
    max_profit: Optional[float] = strawberry.field(name="maxProfit", default=None)
    q: Optional[str] = None

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "hello from Flask using Strawberry graphql and PostgreSQL"

    @strawberry.field
    def db_status(self) -> bool:
        return ping()

    @strawberry.field
    def db_version(self) -> str:
        with get_cursor() as cur:
            cur.execute("SELECT version()")
            (ver,) = cur.fetchone()
            return ver

    @strawberry.field
    def sales_page(self, first: int = 50, after: Optional[str] = None,
                   filter: Optional[SalesFilter] = None,
                   direction: SortDirection = SortDirection.DESC) -> SalesConnection:
        payload = query_sales_page(first, after, vars(filter) if filter else None, direction.value)
        edges = [SalesEdge(cursor=e["cursor"], node=Sales(**e["node"])) for e in payload["edges"]]
        pi = PageInfo(end_cursor=payload["pageInfo"]["endCursor"], has_next_page=payload["pageInfo"]["hasNextPage"])
        return SalesConnection(edges=edges, page_info=pi)

    @strawberry.field
    def sales_by_id(self, order_id: strawberry.ID) -> Optional[Sales]:
        row = get_sales_by_id(int(order_id))
        return Sales(**row) if row else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def import_sales(
        self,
        file: Upload,
        source: str,
        update_on_conflict: bool = False,
    ) -> ImportResult:
        result = import_sales_csv_detailed(
            file,
            source,
            update_on_conflict=update_on_conflict,
            speed_optimize=True,
        )
        return ImportResult(
            inserted=result["inserted"],
            skipped_conflicts=result["skipped_conflicts"],
            dup_in_file=result["dup_in_file"],
            invalid_rows=result["invalid_rows"],
            total_rows=result["total_rows"],
            duration_ms=result["duration_ms"],
            source=result["source"],
            update_mode=result["update_mode"],
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)

