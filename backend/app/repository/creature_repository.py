"""Creature/Reaction Repository — DB CRUD 전담 레이어."""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from app.core.db import get_connection, get_dict_cursor, release_connection


CREATURE_COLUMNS = """
    c.id,
    c.matched_pokemon_id,
    c.match_rank,
    c.similarity_score,
    c.match_reasons,
    c.name,
    c.story,
    c.image_url,
    c.video_url,
    c.sprite_url,
    c.is_public,
    c.user_id,
    c.created_at,
    m.name_kr AS matched_pokemon_name_kr
"""


def create_creature(payload: dict[str, Any]) -> dict[str, Any]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            INSERT INTO creatures (
                matched_pokemon_id, match_rank, similarity_score, match_reasons,
                name, story, image_url, video_url, is_public, user_id
            ) VALUES (
                %(matched_pokemon_id)s, %(match_rank)s, %(similarity_score)s, %(match_reasons)s::jsonb,
                %(name)s, %(story)s, %(image_url)s, %(video_url)s, %(is_public)s, %(user_id)s
            )
            RETURNING id;
            """,
            {
                **payload,
                "match_reasons": psycopg2.extras.Json(payload.get("match_reasons", [])),
                "user_id": payload.get("user_id"),
            },
        )
        creature_id = cursor.fetchone()["id"]
        conn.commit()

        row = get_creature_by_id(str(creature_id))
        if row is None:
            raise RuntimeError("creature 생성 후 조회에 실패했습니다.")
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def get_creature_by_id(creature_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            f"""
            SELECT {CREATURE_COLUMNS}
            FROM creatures c
            JOIN pokemon_master m ON c.matched_pokemon_id = m.pokemon_id
            WHERE c.id = %s;
            """,
            (creature_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        release_connection(conn)


def get_creature_detail_by_id(
    creature_id: str,
    current_user_id: str | None = None,
) -> dict[str, Any] | None:
    """크리처 상세 조회: owner 정보 + like_count + is_liked 포함."""
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT
                c.id,
                c.matched_pokemon_id,
                c.match_rank,
                c.similarity_score,
                c.match_reasons,
                c.name,
                c.story,
                c.image_url,
                c.video_url,
                c.is_public,
                c.user_id,
                c.created_at,
                m.name_kr  AS matched_pokemon_name_kr,
                m.primary_type,
                m.secondary_type,
                u.id       AS owner_id,
                u.nickname AS owner_nickname,
                COALESCE(lc.cnt, 0)::int AS like_count,
                CASE WHEN ul.user_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_liked
            FROM creatures c
            JOIN pokemon_master m ON c.matched_pokemon_id = m.pokemon_id
            LEFT JOIN users u ON c.user_id = u.id
            LEFT JOIN (
                SELECT creature_id, COUNT(*)::int AS cnt
                FROM likes
                GROUP BY creature_id
            ) lc ON lc.creature_id = c.id
            LEFT JOIN likes ul ON ul.creature_id = c.id AND ul.user_id = %s
            WHERE c.id = %s;
            """,
            (current_user_id, creature_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        release_connection(conn)


def list_public_creatures(limit: int, offset: int) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            f"""
            SELECT {CREATURE_COLUMNS}
            FROM creatures c
            JOIN pokemon_master m ON c.matched_pokemon_id = m.pokemon_id
            WHERE c.is_public = TRUE
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s;
            """,
            (limit, offset),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        release_connection(conn)


def list_my_creatures(user_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT
                c.id, c.name, c.is_public, c.image_url, c.created_at,
                m.name_kr AS matched_pokemon_name_kr
            FROM creatures c
            JOIN pokemon_master m ON c.matched_pokemon_id = m.pokemon_id
            WHERE c.user_id = %s
            ORDER BY c.created_at DESC;
            """,
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        release_connection(conn)


def list_liked_creatures(user_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT
                c.id, c.name, c.is_public, c.image_url, c.created_at,
                m.name_kr AS matched_pokemon_name_kr
            FROM creatures c
            JOIN pokemon_master m ON c.matched_pokemon_id = m.pokemon_id
            JOIN likes l ON l.creature_id = c.id
            WHERE l.user_id = %s
            ORDER BY l.created_at DESC;
            """,
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        release_connection(conn)


def delete_creature(creature_id: str) -> None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute("DELETE FROM creatures WHERE id = %s;", (creature_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def creature_exists(creature_id: str) -> bool:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute("SELECT 1 FROM creatures WHERE id = %s;", (creature_id,))
        return cursor.fetchone() is not None
    finally:
        release_connection(conn)


def add_like(user_id: str, creature_id: str) -> int:
    """좋아요 추가. 이미 좋아요한 경우 무시(UPSERT). 최신 like_count 반환."""
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            INSERT INTO likes (user_id, creature_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, creature_id) DO NOTHING;
            """,
            (user_id, creature_id),
        )
        conn.commit()
        return _get_like_count(cursor, creature_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def remove_like(user_id: str, creature_id: str) -> int:
    """좋아요 취소. 최신 like_count 반환."""
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            "DELETE FROM likes WHERE user_id = %s AND creature_id = %s;",
            (user_id, creature_id),
        )
        conn.commit()
        return _get_like_count(cursor, creature_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def _get_like_count(cursor: Any, creature_id: str) -> int:
    cursor.execute(
        "SELECT COUNT(*)::int AS cnt FROM likes WHERE creature_id = %s;",
        (creature_id,),
    )
    row = cursor.fetchone()
    return row["cnt"] if row else 0


def create_reaction(creature_id: str, emoji_type: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            INSERT INTO reactions (creature_id, emoji_type)
            VALUES (%s, %s)
            RETURNING id, creature_id, emoji_type, created_at;
            """,
            (creature_id, emoji_type),
        )
        row = cursor.fetchone()
        conn.commit()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def get_reaction_summary(creature_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT emoji_type, COUNT(*)::int AS count
            FROM reactions
            WHERE creature_id = %s
            GROUP BY emoji_type
            ORDER BY count DESC, emoji_type ASC;
            """,
            (creature_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        release_connection(conn)


def get_creature_generation_context(creature_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT
                c.id,
                c.name,
                c.story,
                c.image_url,
                c.video_url,
                c.match_rank,
                c.similarity_score,
                c.match_reasons,
                c.created_at,
                m.pokemon_id AS matched_pokemon_id,
                m.name_kr AS matched_pokemon_name_kr,
                m.name_en AS matched_pokemon_name_en,
                m.primary_type,
                m.secondary_type,
                m.pokedex_text_kr
            FROM creatures c
            JOIN pokemon_master m ON c.matched_pokemon_id = m.pokemon_id
            WHERE c.id = %s;
            """,
            (creature_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        release_connection(conn)


def update_creature_generated_fields(
    creature_id: str,
    name: str | None,
    story: str | None,
    image_url: str | None,
) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            f"""
            UPDATE creatures c
            SET
                name = COALESCE(%s, c.name),
                story = COALESCE(%s, c.story),
                image_url = COALESCE(%s, c.image_url)
            FROM pokemon_master m
            WHERE c.matched_pokemon_id = m.pokemon_id
              AND c.id = %s
            RETURNING {CREATURE_COLUMNS};
            """,
            (name, story, image_url, creature_id),
        )
        row = cursor.fetchone()
        if row:
            conn.commit()
            return dict(row)
        conn.rollback()
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def patch_creature(creature_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    if not fields:
        return get_creature_by_id(creature_id)

    set_parts = []
    params: list[Any] = []
    if "name" in fields:
        set_parts.append("name = %s")
        params.append(fields["name"])
    if "is_public" in fields:
        set_parts.append("is_public = %s")
        params.append(fields["is_public"])

    if not set_parts:
        return get_creature_by_id(creature_id)

    params.append(creature_id)
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            f"""
            UPDATE creatures c
            SET {", ".join(set_parts)}
            FROM pokemon_master m
            WHERE c.matched_pokemon_id = m.pokemon_id
              AND c.id = %s
            RETURNING {CREATURE_COLUMNS};
            """,
            params,
        )
        row = cursor.fetchone()
        if row:
            conn.commit()
            return dict(row)
        conn.rollback()
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def update_creature_sprite_url(creature_id: str, sprite_url: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            f"""
            UPDATE creatures c
            SET sprite_url = %s
            FROM pokemon_master m
            WHERE c.matched_pokemon_id = m.pokemon_id
              AND c.id = %s
            RETURNING {CREATURE_COLUMNS};
            """,
            (sprite_url, creature_id),
        )
        row = cursor.fetchone()
        if row:
            conn.commit()
            return dict(row)
        conn.rollback()
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def update_creature_video_url(creature_id: str, video_url: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            f"""
            UPDATE creatures c
            SET video_url = %s
            FROM pokemon_master m
            WHERE c.matched_pokemon_id = m.pokemon_id
              AND c.id = %s
            RETURNING {CREATURE_COLUMNS};
            """,
            (video_url, creature_id),
        )
        row = cursor.fetchone()
        if row:
            conn.commit()
            return dict(row)
        conn.rollback()
        return None
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
