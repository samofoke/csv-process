from __future__ import annotations
import strawberry
from strawberry.file_uploads import Upload
from ..config.db.connection import get_cursor, ping
from ..service.csv_import import import_sales_csv_detailed

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
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "hello from Flask using Strawberry and PostgreSQL"

    @strawberry.field
    def db_status(self) -> bool:
        return ping()

    @strawberry.field
    def db_version(self) -> str:
        with get_cursor() as cur:
            cur.execute("SELECT version()")
            (ver,) = cur.fetchone()
            return ver

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

