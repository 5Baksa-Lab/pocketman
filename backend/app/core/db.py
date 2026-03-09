"""
DB 연결 관리
"""
from __future__ import annotations

import threading

import psycopg2
import psycopg2.extras
from psycopg2 import pool as pgpool

from app.core.config import DATABASE_URL, DB_POOL_MAX_CONN, DB_POOL_MIN_CONN


_pool_lock = threading.Lock()
_pool: pgpool.ThreadedConnectionPool | None = None


def get_pool() -> pgpool.ThreadedConnectionPool:
    global _pool

    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL 환경 변수가 비어 있습니다.")

        if DB_POOL_MIN_CONN < 1 or DB_POOL_MAX_CONN < DB_POOL_MIN_CONN:
            raise RuntimeError(
                "DB_POOL_MIN_CONN/DB_POOL_MAX_CONN 설정이 올바르지 않습니다."
            )

        _pool = pgpool.ThreadedConnectionPool(
            minconn=DB_POOL_MIN_CONN,
            maxconn=DB_POOL_MAX_CONN,
            dsn=DATABASE_URL,
        )
        return _pool


def get_connection():
    return get_pool().getconn()


def release_connection(conn: psycopg2.extensions.connection | None) -> None:
    if conn is None:
        return

    pool = _pool
    if pool is None:
        conn.close()
        return

    try:
        if not conn.closed:
            # Pool 반환 전 세션 상태를 정리해 다음 요청에 트랜잭션이 누수되지 않도록 한다.
            conn.rollback()
        pool.putconn(conn, close=bool(conn.closed))
    except Exception:
        conn.close()


def get_dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
