from __future__ import annotations
import strawberry
from ..config.db.connection import get_cursor, ping

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "hello from Flask + Strawberry + PostgreSQL"

    @strawberry.field
    def db_status(self) -> bool:
        return ping()

    @strawberry.field
    def db_version(self) -> str:
        with get_cursor() as cur:
            cur.execute("SELECT version()")
            (ver,) = cur.fetchone()
            return ver

schema = strawberry.Schema(query=Query)
