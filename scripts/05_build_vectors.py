"""
Step 5. 28차원 특징 벡터 생성 및 pgvector 저장 스크립트
기획안 v5 §6-1 "28차원 공통 특징 벡터" 기준

입력: pokemon_visual + pokemon_impression + pokemon_type_affinity
출력: pokemon_vectors (vector(28))

벡터 차원 구성 (순서 고정):
  [0-9]   visual (10차원):
            eye_size_score, eye_distance_score, eye_roundness_score, eye_tail_score,
            face_roundness_score, face_proportion_score, feature_size_score,
            feature_emphasis_score, mouth_curve_score, overall_symmetry
  [10-18] impression (9차원):
            cute, calm, smart, fierce, gentle, lively, innocent, confident, unique
  [19-26] type_affinity (8차원):
            water, fire, grass, electric, psychic, normal, fighting, ghost
  [27]    glasses (1차원): 0.0 or 1.0

실행 방법:
    python scripts/05_build_vectors.py
    python scripts/05_build_vectors.py --start 1 --end 386
"""

import os
import logging
import argparse

import numpy as np
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

VECTOR_DIM = 28
COMMIT_BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# 벡터 조합 및 L2 정규화
# ---------------------------------------------------------------------------
def build_vector(row: dict) -> np.ndarray:
    """
    DB에서 JOIN 조회된 row를 받아 28차원 numpy 벡터를 반환합니다.
    L2 정규화(단위 벡터)를 적용합니다 → 코사인 유사도 = 내적.
    """
    def f(key: str, default: float = 0.5) -> float:
        val = row.get(key)
        return float(val) if val is not None else default

    vector = np.array([
        # [0-9] visual 10차원
        f("eye_size_score"),
        f("eye_distance_score"),
        f("eye_roundness_score"),
        f("eye_tail_score"),
        f("face_roundness_score"),
        f("face_proportion_score"),
        f("feature_size_score"),
        f("feature_emphasis_score"),
        f("mouth_curve_score"),
        f("overall_symmetry"),

        # [10-18] impression 9차원
        f("cute_score"),
        f("calm_score"),
        f("smart_score"),
        f("fierce_score"),
        f("gentle_score"),
        f("lively_score"),
        f("innocent_score"),
        f("confident_score"),
        f("unique_score"),

        # [19-26] type_affinity 8차원
        f("water_affinity",    0.0),
        f("fire_affinity",     0.0),
        f("grass_affinity",    0.0),
        f("electric_affinity", 0.0),
        f("psychic_affinity",  0.0),
        f("normal_affinity",   0.0),
        f("fighting_affinity", 0.0),
        f("ghost_affinity",    0.0),

        # [27] glasses 1차원
        1.0 if row.get("has_glasses") else 0.0,
    ], dtype=np.float32)

    assert len(vector) == VECTOR_DIM, f"벡터 차원 오류: {len(vector)} != {VECTOR_DIM}"

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector


def vector_to_pg_literal(vec: np.ndarray) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


# ---------------------------------------------------------------------------
# DB 처리
# ---------------------------------------------------------------------------
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def run(start: int, end: int):
    log.info(f"===== Step 5: 28차원 벡터 생성 시작: #{start}~#{end} =====")

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT
            m.pokemon_id, m.name_kr,
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
        FROM pokemon_master m
        JOIN pokemon_visual        v  ON m.pokemon_id = v.pokemon_id
        JOIN pokemon_impression    i  ON m.pokemon_id = i.pokemon_id
        JOIN pokemon_type_affinity ta ON m.pokemon_id = ta.pokemon_id
        WHERE m.pokemon_id BETWEEN %s AND %s
        ORDER BY m.pokemon_id;
    """, (start, end))

    rows = cursor.fetchall()
    log.info(f"처리 대상: {len(rows)}마리")

    if len(rows) == 0:
        log.warning("처리할 데이터가 없습니다. Steps 2~4를 먼저 실행하세요.")

    success, errors = 0, []
    pending_commits = 0

    for row in rows:
        pokemon_id = row["pokemon_id"]
        cursor.execute("SAVEPOINT sp_vector_row")

        try:
            vec = build_vector(row)
            vec_literal = vector_to_pg_literal(vec)

            cursor.execute("""
                INSERT INTO pokemon_vectors
                    (pokemon_id, feature_vector, vector_version, generated_at)
                VALUES (%s, %s::vector, 1, NOW())
                ON CONFLICT (pokemon_id) DO UPDATE SET
                    feature_vector = EXCLUDED.feature_vector,
                    vector_version = EXCLUDED.vector_version,
                    generated_at   = NOW();
            """, (pokemon_id, vec_literal))
            cursor.execute("RELEASE SAVEPOINT sp_vector_row")
            pending_commits += 1
            if pending_commits >= COMMIT_BATCH_SIZE:
                conn.commit()
                pending_commits = 0
            log.info(
                f"  #{pokemon_id:03d} {row['name_kr']} | "
                f"norm={np.linalg.norm(vec):.4f} dim={len(vec)}"
            )
            success += 1

        except Exception as e:
            cursor.execute("ROLLBACK TO SAVEPOINT sp_vector_row")
            cursor.execute("RELEASE SAVEPOINT sp_vector_row")
            log.error(f"  #{pokemon_id} 벡터 생성 오류: {e}")
            errors.append(pokemon_id)

    if pending_commits > 0:
        conn.commit()

    # 선행 Step 미완료 포켓몬 확인
    cursor.execute("""
        SELECT m.pokemon_id, m.name_kr
        FROM pokemon_master m
        WHERE m.pokemon_id BETWEEN %s AND %s
          AND (
            m.pokemon_id NOT IN (SELECT pokemon_id FROM pokemon_visual)
            OR m.pokemon_id NOT IN (SELECT pokemon_id FROM pokemon_impression)
            OR m.pokemon_id NOT IN (SELECT pokemon_id FROM pokemon_type_affinity)
          )
        ORDER BY m.pokemon_id;
    """, (start, end))

    incomplete = cursor.fetchall()
    if incomplete:
        log.warning(f"선행 Step 미완료 포켓몬 (벡터 생성 건너뜀) {len(incomplete)}마리:")
        for r in incomplete[:10]:
            log.warning(f"  #{r['pokemon_id']:03d} {r['name_kr']}")
        log.warning("→ Steps 2~4를 먼저 완료한 후 재실행하세요.")

    cursor.close()
    conn.close()

    log.info(f"===== Step 5: 벡터 생성 완료: {success}마리 | 오류: {len(errors)} =====")
    if errors:
        log.warning(f"오류 목록: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="28차원 특징 벡터 생성 스크립트 (v5)")
    parser.add_argument("--start", type=int, default=1,   help="시작 번호")
    parser.add_argument("--end",   type=int, default=386, help="끝 번호")
    args = parser.parse_args()
    run(start=args.start, end=args.end)
