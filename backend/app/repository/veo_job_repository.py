"""Veo Job Repository — 비동기 영상 작업 상태 CRUD."""

from __future__ import annotations

from typing import Any

from app.core.db import get_connection, get_dict_cursor


VALID_STATUSES = {"queued", "running", "succeeded", "failed", "canceled"}


def create_veo_job(creature_id: str) -> dict[str, Any]:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            INSERT INTO veo_jobs (creature_id, status)
            VALUES (%s, 'queued')
            RETURNING id, creature_id, status, video_url, error_message, requested_at, updated_at;
            """,
            (creature_id,),
        )
        row = cursor.fetchone()
        conn.commit()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_veo_job(job_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            SELECT id, creature_id, status, video_url, error_message, requested_at, updated_at
            FROM veo_jobs
            WHERE id = %s;
            """,
            (job_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_veo_job(
    job_id: str,
    status: str,
    video_url: str | None,
    error_message: str | None,
) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute(
            """
            UPDATE veo_jobs
            SET status = %s,
                video_url = %s,
                error_message = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, creature_id, status, video_url, error_message, requested_at, updated_at;
            """,
            (status, video_url, error_message, job_id),
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


def creature_exists_for_job(creature_id: str) -> bool:
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute("SELECT 1 FROM creatures WHERE id = %s;", (creature_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()
