"""User Repository — DB CRUD 전담 레이어."""

from __future__ import annotations

from typing import Any

from app.core.db import get_connection, get_dict_cursor, release_connection


def create_user(email: str, nickname: str, password_hash: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            INSERT INTO users (email, nickname, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id, email, nickname, created_at;
            """,
            (email, nickname, password_hash),
        )
        row = cursor.fetchone()
        conn.commit()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT id, email, nickname, password_hash, created_at
            FROM users
            WHERE email = %s;
            """,
            (email,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        release_connection(conn)


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT id, email, nickname, created_at
            FROM users
            WHERE id = %s;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        release_connection(conn)


def get_user_profile(user_id: str) -> dict[str, Any] | None:
    """프로필 정보(bio, dark_mode, font_size, avatar 포함) + 통계 조회."""
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT
                u.id, u.email, u.nickname, u.bio,
                u.avatar_creature_id, u.dark_mode, u.font_size, u.created_at,
                av.image_url AS avatar_url,
                COALESCE(cc.cnt, 0)::int AS creature_count,
                COALESCE(lc.cnt, 0)::int AS like_received_count
            FROM users u
            LEFT JOIN creatures av ON av.id = u.avatar_creature_id
            LEFT JOIN (
                SELECT user_id, COUNT(*)::int AS cnt
                FROM creatures
                GROUP BY user_id
            ) cc ON cc.user_id = u.id
            LEFT JOIN (
                SELECT c.user_id, COUNT(*)::int AS cnt
                FROM likes l
                JOIN creatures c ON c.id = l.creature_id
                WHERE c.user_id IS NOT NULL
                GROUP BY c.user_id
            ) lc ON lc.user_id = u.id
            WHERE u.id = %s;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        release_connection(conn)


def check_nickname_available(nickname: str, exclude_user_id: str | None = None) -> bool:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        if exclude_user_id:
            cursor.execute(
                "SELECT 1 FROM users WHERE nickname = %s AND id != %s;",
                (nickname, exclude_user_id),
            )
        else:
            cursor.execute(
                "SELECT 1 FROM users WHERE nickname = %s;",
                (nickname,),
            )
        return cursor.fetchone() is None
    finally:
        release_connection(conn)


def update_user_profile(user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    if not fields:
        return get_user_profile(user_id)

    set_parts = []
    params: list[Any] = []
    allowed = {"nickname", "bio", "avatar_creature_id", "dark_mode", "font_size"}
    for key in allowed:
        if key in fields:
            set_parts.append(f"{key} = %s")
            params.append(fields[key])

    if not set_parts:
        return get_user_profile(user_id)

    params.append(user_id)
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            f"UPDATE users SET {', '.join(set_parts)} WHERE id = %s;",
            params,
        )
        conn.commit()
        return get_user_profile(user_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def get_user_password_hash(user_id: str) -> str | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = %s;",
            (user_id,),
        )
        row = cursor.fetchone()
        return row["password_hash"] if row else None
    finally:
        release_connection(conn)


def update_password_hash(user_id: str, new_hash: str) -> None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s;",
            (new_hash, user_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def delete_user(user_id: str) -> None:
    """회원 탈퇴: 사용자 및 연관 데이터 삭제 (CASCADE)."""
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        # likes, comments, creatures는 FK CASCADE로 자동 삭제
        cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
