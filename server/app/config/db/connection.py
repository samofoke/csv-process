from contextlib import contextmanager
from typing import Iterator, Optional
from ..db_setup import settings 
from psycopg_pool import ConnectionPool
import psycopg


_pool: Optional[ConnectionPool] = None

def init_pool(min_size: int = 1, max_size: int = 10) -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=min_size,
            max_size=max_size,
        )

@contextmanager
def get_cursor() -> Iterator[psycopg.Cursor]:
    if _pool is None:
        raise RuntimeError("DB pool not initialized")
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise

def ping() -> bool:
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False
