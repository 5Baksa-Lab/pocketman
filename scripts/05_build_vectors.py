"""
Step 5. 28차원 특징 벡터 생성 및 pgvector 저장 스크립트
입력: pokemon_impression_scores + pokemon_type_affinity + pokemon_style_features
출력: pokemon_feature_vectors (vector(28))

벡터 차원 구성 (순서 고정):
  [0-1]   face_shape:      face_aspect_ratio, jawline_angle
  [2-4]   eye:             eye_size_ratio, eye_distance_ratio, eye_slant_angle
  [5-9]   nose_mouth:      nose_length_ratio, nose_width_ratio, mouth_width_ratio,
                           lip_thickness_ratio, philtrum_ratio
  [10-12] style (bool):    has_glasses, has_facial_hair, has_bangs
  [13-21] impression:      cute, calm, smart, fierce, gentle,
                           lively, innocent, confident, unique
  [22-27] type_affinity:   water, fire, grass, electric, psychic, ghost

실행 방법:
    python scripts/05_build_vectors.py
    python scripts/05_build_vectors.py --start 1 --end 30
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

# 벡터 차원 수 (스키마와 반드시 일치)
VECTOR_DIM = 28


# ---------------------------------------------------------------------------
# 벡터 조합 및 정규화
# ---------------------------------------------------------------------------
def build_vector(row: dict) -> np.ndarray:
    """
    DB에서 JOIN 조회된 row를 받아 28차원 numpy 벡터를 반환합니다.
    L2 정규화(unit vector)를 적용합니다.
    """
    def f(key: str, default: float = 0.0) -> float:
        val = row.get(key)
        return float(val) if val is not None else default

    def b(key: str) -> float:
        return 1.0 if row.get(key) else 0.0

    vector = np.array([
        # [0-1] face_shape
        f("face_aspect_ratio"),
        f("jawline_angle"),

        # [2-4] eye
        f("eye_size_ratio"),
        f("eye_distance_ratio"),
        f("eye_slant_angle", 0.5),

        # [5-9] nose_mouth
        f("nose_length_ratio", 0.1),
        f("nose_width_ratio",  0.1),
        f("mouth_width_ratio"),
        f("lip_thickness_ratio"),
        f("philtrum_ratio",    0.1),

        # [10-12] style boolean
        b("has_glasses"),
        b("has_facial_hair"),
        b("has_bangs"),

        # [13-21] impression scores
        f("cute_score"),
        f("calm_score"),
        f("smart_score"),
        f("fierce_score"),
        f("gentle_score"),
        f("lively_score"),
        f("innocent_score"),
        f("confident_score"),
        f("unique_score"),

        # [22-27] type affinity (핵심 6개)
        f("water_affinity"),
        f("fire_affinity"),
        f("grass_affinity"),
        f("electric_affinity"),
        f("psychic_affinity"),
        f("ghost_affinity"),
    ], dtype=np.float32)

    assert len(vector) == VECTOR_DIM, f"벡터 차원 오류: {len(vector)} != {VECTOR_DIM}"

    # L2 정규화 (단위 벡터로 변환 → 코사인 유사도 = 내적)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector


def vector_to_pg_literal(vec: np.ndarray) -> str:
    """pgvector INSERT 형식: '[0.1, 0.2, ...]' """
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
    log.info(f"===== 28차원 벡터 생성 시작: #{start} ~ #{end} =====")

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 모든 테이블 JOIN
    cursor.execute("""
        SELECT
            m.pokemon_id,
            m.name_kr,
            -- face_shape
            fs.face_aspect_ratio,
            fs.jawline_angle,
            -- eye
            ey.eye_size_ratio,
            ey.eye_distance_ratio,
            ey.eye_slant_angle,
            -- nose_mouth
            nm.nose_length_ratio,
            nm.nose_width_ratio,
            nm.mouth_width_ratio,
            nm.lip_thickness_ratio,
            nm.philtrum_ratio,
            -- style
            st.has_glasses,
            st.has_facial_hair,
            st.has_bangs,
            -- impression
            im.cute_score,
            im.calm_score,
            im.smart_score,
            im.fierce_score,
            im.gentle_score,
            im.lively_score,
            im.innocent_score,
            im.confident_score,
            im.unique_score,
            -- type_affinity
            ta.water_affinity,
            ta.fire_affinity,
            ta.grass_affinity,
            ta.electric_affinity,
            ta.psychic_affinity,
            ta.ghost_affinity
        FROM pokemon_master m
        JOIN pokemon_face_shape          fs ON m.pokemon_id = fs.pokemon_id
        JOIN pokemon_eye_features        ey ON m.pokemon_id = ey.pokemon_id
        JOIN pokemon_nose_mouth_features nm ON m.pokemon_id = nm.pokemon_id
        JOIN pokemon_style_features      st ON m.pokemon_id = st.pokemon_id
        JOIN pokemon_impression_scores   im ON m.pokemon_id = im.pokemon_id
        JOIN pokemon_type_affinity       ta ON m.pokemon_id = ta.pokemon_id
        WHERE m.pokemon_id BETWEEN %s AND %s
        ORDER BY m.pokemon_id;
    """, (start, end))

    rows = cursor.fetchall()
    log.info(f"처리 대상: {len(rows)}마리")

    success = 0
    missing = []

    for row in rows:
        pokemon_id = row["pokemon_id"]

        try:
            vec = build_vector(row)
            vec_literal = vector_to_pg_literal(vec)

            cursor.execute("""
                INSERT INTO pokemon_feature_vectors
                    (pokemon_id, feature_vector, vector_version, generated_at)
                VALUES (%s, %s::vector, 1, NOW())
                ON CONFLICT (pokemon_id) DO UPDATE SET
                    feature_vector = EXCLUDED.feature_vector,
                    vector_version = EXCLUDED.vector_version,
                    generated_at   = NOW();
            """, (pokemon_id, vec_literal))

            conn.commit()
            log.info(
                f"  #{pokemon_id:03d} {row['name_kr']} | "
                f"norm={np.linalg.norm(vec):.4f} | "
                f"dim={len(vec)}"
            )
            success += 1

        except Exception as e:
            conn.rollback()
            log.error(f"  #{pokemon_id} 벡터 생성 오류: {e}")
            missing.append(pokemon_id)

    # 누락된 포켓몬 확인 (JOIN 실패 = 선행 Step 미완료)
    cursor.execute("""
        SELECT m.pokemon_id, m.name_kr
        FROM pokemon_master m
        WHERE m.pokemon_id BETWEEN %s AND %s
          AND m.pokemon_id NOT IN (
              SELECT pokemon_id FROM pokemon_face_shape
              INTERSECT SELECT pokemon_id FROM pokemon_eye_features
              INTERSECT SELECT pokemon_id FROM pokemon_nose_mouth_features
              INTERSECT SELECT pokemon_id FROM pokemon_style_features
              INTERSECT SELECT pokemon_id FROM pokemon_impression_scores
              INTERSECT SELECT pokemon_id FROM pokemon_type_affinity
          )
        ORDER BY m.pokemon_id;
    """, (start, end))

    incomplete = cursor.fetchall()
    if incomplete:
        log.warning(f"선행 Step 미완료 포켓몬 (벡터 생성 건너뜀):")
        for r in incomplete:
            log.warning(f"  #{r['pokemon_id']:03d} {r['name_kr']}")
        log.warning("→ Step 1~4 를 먼저 완료한 후 재실행하세요.")

    cursor.close()
    conn.close()

    log.info(f"===== 벡터 생성 완료: {success}마리 | 오류: {len(missing)} =====")
    if missing:
        log.warning(f"오류 목록: {missing}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="28차원 특징 벡터 생성 스크립트")
    parser.add_argument("--start", type=int, default=1,   help="시작 번호")
    parser.add_argument("--end",   type=int, default=151, help="끝 번호")
    args = parser.parse_args()
    run(start=args.start, end=args.end)
