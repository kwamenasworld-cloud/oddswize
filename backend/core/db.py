import os
import psycopg2
from contextlib import contextmanager


def get_pg_dsn() -> str:
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("POSTGRES_DSN not set")
    return dsn


@contextmanager
def get_conn():
    conn = psycopg2.connect(get_pg_dsn())
    try:
        yield conn
    finally:
        conn.close()

