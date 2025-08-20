from contextlib import contextmanager
from typing import Iterator, Optional
from ..db_setup import settings
import logging
import time
from psycopg_pool import ConnectionPool
import psycopg

log = logging.getLogger("app.db")

_pool: Optional[ConnectionPool] = None
_READY: bool = False
_LAST_ERROR: Optional[Exception] = None

def init_pool(min_size: int = 1, max_size: int = 10, *, wait_timeout_sec: int = 30) -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=min_size,
            max_size=max_size,
        )
        wait_until_ready(timeout_sec=wait_timeout_sec, interval_sec=1.0)


def wait_until_ready(*, timeout_sec: int = 30, interval_sec: float = 1.0) -> bool:
    global _READY, _LAST_ERROR
    if _READY:
        return True

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with get_cursor() as cur:
                cur.execute("SELECT current_database(), current_user")
                dbname, dbuser = cur.fetchone()
            _READY = True
            _LAST_ERROR = None
            msg = f"PostgreSQL ready (db={dbname}, user={dbuser}, host={settings.db_host}:{settings.db_port})"
            print(msg, flush=True)
            log.info(msg)
            return True
        except Exception as e:
            _LAST_ERROR = e
            time.sleep(interval_sec)

    log.error("PostgreSQL not ready after %ss (last error: %r)", timeout_sec, _LAST_ERROR)
    return False

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
