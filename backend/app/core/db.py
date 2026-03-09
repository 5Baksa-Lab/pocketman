"""
DB 연결 관리
"""
import psycopg2
import psycopg2.extras
from app.core.config import DATABASE_URL


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경 변수가 비어 있습니다.")
    return psycopg2.connect(DATABASE_URL)


def get_dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
