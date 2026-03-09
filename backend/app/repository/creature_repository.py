"""Creature/Reaction Repository — DB CRUD 전담 레이어."""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from app.core.db import get_connection, get_dict_cursor


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
    c.is_public,
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
                name, story, image_url, video_url, is_public
            ) VALUES (
                %(matched_pokemon_id)s, %(match_rank)s, %(similarity_score)s, %(match_reasons)s::jsonb,
                %(name)s, %(story)s, %(image_url)s, %(video_url)s, %(is_public)s
            )
            RETURNING id;
            """,
            {
                **payload,
                "match_reasons": psycopg2.extras.Json(payload.get("match_reasons", [])),
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
        conn.close()


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
        conn.close()


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
        conn.close()


def creature_exists(creature_id: str) -> bool:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute("SELECT 1 FROM creatures WHERE id = %s;", (creature_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()


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
        conn.close()
