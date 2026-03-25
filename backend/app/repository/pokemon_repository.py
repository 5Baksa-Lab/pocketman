"""
Pokemon Repository — DB 쿼리 전담 레이어
"""
import numpy as np
from app.core.db import get_connection, get_dict_cursor, release_connection
from app.core.config import TOP_K


def vector_to_pg(vec: np.ndarray) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


def search_top_k(user_vector: np.ndarray, k: int = TOP_K) -> list[dict]:
    """
    pgvector 코사인 유사도 검색 → Top-K 포켓몬 반환

    Returns: [
        {
            pokemon_id, name_kr, name_en, primary_type, secondary_type,
            sprite_url, similarity,
            eye_size_score, ..., ghost_affinity  ← 비교용 visual/impression/affinity 값
        },
        ...
    ]
    """
    vec_literal = vector_to_pg(user_vector)

    sql = """
        SELECT
            m.pokemon_id,
            m.name_kr,
            m.name_en,
            m.primary_type,
            m.secondary_type,
            m.sprite_url,
            ROUND((1 - (vec.feature_vector <=> %(vec)s::vector))::numeric, 4) AS similarity,
            -- visual 10차원
            v.eye_size_score, v.eye_distance_score, v.eye_roundness_score,
            v.eye_tail_score, v.face_roundness_score, v.face_proportion_score,
            v.feature_size_score, v.feature_emphasis_score,
            v.mouth_curve_score, v.overall_symmetry,
            v.has_glasses,
            -- impression 9차원
            i.cute_score, i.calm_score, i.smart_score, i.fierce_score,
            i.gentle_score, i.lively_score, i.innocent_score,
            i.confident_score, i.unique_score,
            -- type_affinity 8차원
            ta.water_affinity, ta.fire_affinity, ta.grass_affinity,
            ta.electric_affinity, ta.psychic_affinity, ta.normal_affinity,
            ta.fighting_affinity, ta.ghost_affinity
        FROM pokemon_vectors vec
        JOIN pokemon_master        m  ON vec.pokemon_id = m.pokemon_id
        JOIN pokemon_visual        v  ON vec.pokemon_id = v.pokemon_id
        JOIN pokemon_impression    i  ON vec.pokemon_id = i.pokemon_id
        JOIN pokemon_type_affinity ta ON vec.pokemon_id = ta.pokemon_id
        ORDER BY vec.feature_vector <=> %(vec)s::vector
        LIMIT %(k)s;
    """

    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute("SET ivfflat.probes = 10")
        cursor.execute(sql, {"vec": vec_literal, "k": k})
        return [dict(r) for r in cursor.fetchall()]
    finally:
        release_connection(conn)


def get_db_stats() -> dict:
    """헬스체크용 DB 통계"""
    conn = get_connection()
    try:
        cursor = get_dict_cursor(conn)
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM pokemon_master)  AS pokemon_count,
                (SELECT COUNT(*) FROM pokemon_vectors) AS vector_count;
        """)
        return dict(cursor.fetchone())
    finally:
        release_connection(conn)
