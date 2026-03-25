"""Comment Repository — DB CRUD 전담 레이어."""

from __future__ import annotations

from typing import Any

from app.core.db import get_connection, get_dict_cursor, release_connection


def list_comments(
    creature_id: str,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """댓글 목록 조회 (최신순). (items, total) 반환."""
    offset = (page - 1) * limit
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            "SELECT COUNT(*)::int AS total FROM comments WHERE creature_id = %s;",
            (creature_id,),
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT
                c.id,
                c.content,
                c.created_at,
                u.id       AS author_id,
                u.nickname AS author_nickname
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.creature_id = %s
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s;
            """,
            (creature_id, limit, offset),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        return rows, total
    finally:
        release_connection(conn)


def create_comment(creature_id: str, user_id: str, content: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            INSERT INTO comments (creature_id, user_id, content)
            VALUES (%s, %s, %s)
            RETURNING id, content, created_at, user_id;
            """,
            (creature_id, user_id, content),
        )
        row = dict(cursor.fetchone())
        conn.commit()

        # author 정보 포함
        cursor.execute(
            "SELECT id, nickname FROM users WHERE id = %s;",
            (user_id,),
        )
        user_row = cursor.fetchone()
        row["author_id"] = str(user_row["id"])
        row["author_nickname"] = user_row["nickname"]
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def get_comment_owner(comment_id: str) -> str | None:
    """댓글의 user_id 반환. 댓글 없으면 None."""
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            "SELECT user_id FROM comments WHERE id = %s;",
            (comment_id,),
        )
        row = cursor.fetchone()
        return str(row["user_id"]) if row else None
    finally:
        release_connection(conn)


def delete_comment(comment_id: str) -> None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute("DELETE FROM comments WHERE id = %s;", (comment_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
