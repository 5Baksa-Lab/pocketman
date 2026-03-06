"""
Step 4. 타입 친화도 자동 계산 스크립트
입력: pokemon_master.primary_type / secondary_type
출력: pokemon_type_affinity (13개 친화도 차원)

규칙:
  - 1타입만 있으면: 해당 타입 친화도 1.0
  - 2타입이면: 1타입 × 0.7 + 2타입 × 0.3 합산

실행 방법:
    python scripts/04_calc_type_affinity.py
    python scripts/04_calc_type_affinity.py --start 1 --end 30
"""

import os
import logging
import argparse
from typing import Optional

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


# ---------------------------------------------------------------------------
# 타입 → 친화도 룰 테이블
# ---------------------------------------------------------------------------
# 각 타입이 13개 친화도 차원에 미치는 가중치 (합계가 반드시 1.0일 필요 없음)
TYPE_TO_AFFINITY: dict[str, dict[str, float]] = {
    "노말":   {"normal_affinity": 1.0},
    "불꽃":   {"fire_affinity": 1.0},
    "물":     {"water_affinity": 1.0},
    "풀":     {"grass_affinity": 1.0},
    "전기":   {"electric_affinity": 1.0},
    "얼음":   {"ice_affinity": 1.0},
    "격투":   {"fighting_affinity": 1.0},
    "독":     {"poison_affinity": 0.80, "psychic_affinity": 0.20},  # 독 = 신비로움 보조
    "땅":     {"ground_affinity": 1.0},
    "비행":   {"normal_affinity": 0.50, "water_affinity": 0.30, "ghost_affinity": 0.20},
    "에스퍼": {"psychic_affinity": 1.0},
    "벌레":   {"grass_affinity": 0.60, "ground_affinity": 0.40},
    "바위":   {"rock_affinity": 1.0},
    "고스트": {"ghost_affinity": 1.0},
    "드래곤": {"dragon_affinity": 1.0},
    "악":     {"ghost_affinity": 0.50, "fighting_affinity": 0.50},  # 악 = 다크/공격적
    "강철":   {"rock_affinity": 0.50, "ice_affinity": 0.30, "fighting_affinity": 0.20},
    "페어리": {"normal_affinity": 0.40, "psychic_affinity": 0.60},
}

AFFINITY_COLUMNS = [
    "water_affinity", "fire_affinity", "grass_affinity",
    "electric_affinity", "psychic_affinity", "normal_affinity",
    "fighting_affinity", "ghost_affinity", "ice_affinity",
    "ground_affinity", "rock_affinity", "poison_affinity", "dragon_affinity",
]


# ---------------------------------------------------------------------------
# 친화도 계산
# ---------------------------------------------------------------------------
def clamp(v: float) -> float:
    return round(max(0.0, min(1.0, v)), 2)


def calc_type_affinity(
    primary_type: str,
    secondary_type: Optional[str],
) -> dict[str, float]:
    result = {col: 0.0 for col in AFFINITY_COLUMNS}

    # 1타입 기여
    primary_weights = TYPE_TO_AFFINITY.get(primary_type, {"normal_affinity": 1.0})
    weight_1 = 0.7 if secondary_type else 1.0
    for col, val in primary_weights.items():
        if col in result:
            result[col] += val * weight_1

    # 2타입 기여
    if secondary_type:
        secondary_weights = TYPE_TO_AFFINITY.get(secondary_type, {})
        for col, val in secondary_weights.items():
            if col in result:
                result[col] += val * 0.3

    return {k: clamp(v) for k, v in result.items()}


# ---------------------------------------------------------------------------
# DB 처리
# ---------------------------------------------------------------------------
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def run(start: int, end: int):
    log.info(f"===== 타입 친화도 계산 시작: #{start} ~ #{end} =====")

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT pokemon_id, name_kr, primary_type, secondary_type
        FROM pokemon_master
        WHERE pokemon_id BETWEEN %s AND %s
        ORDER BY pokemon_id;
    """, (start, end))

    rows = cursor.fetchall()
    log.info(f"처리 대상: {len(rows)}마리")

    success = 0
    for row in rows:
        pokemon_id     = row["pokemon_id"]
        primary_type   = row["primary_type"]
        secondary_type = row["secondary_type"]

        if primary_type not in TYPE_TO_AFFINITY:
            log.warning(f"  #{pokemon_id} 알 수 없는 타입: {primary_type} → 노말 처리")
            primary_type = "노말"

        affinity = calc_type_affinity(primary_type, secondary_type)

        cursor.execute("""
            INSERT INTO pokemon_type_affinity (
                pokemon_id,
                water_affinity, fire_affinity, grass_affinity,
                electric_affinity, psychic_affinity, normal_affinity,
                fighting_affinity, ghost_affinity, ice_affinity,
                ground_affinity, rock_affinity, poison_affinity, dragon_affinity
            ) VALUES (
                %(pokemon_id)s,
                %(water_affinity)s, %(fire_affinity)s, %(grass_affinity)s,
                %(electric_affinity)s, %(psychic_affinity)s, %(normal_affinity)s,
                %(fighting_affinity)s, %(ghost_affinity)s, %(ice_affinity)s,
                %(ground_affinity)s, %(rock_affinity)s, %(poison_affinity)s,
                %(dragon_affinity)s
            )
            ON CONFLICT (pokemon_id) DO UPDATE SET
                water_affinity    = EXCLUDED.water_affinity,
                fire_affinity     = EXCLUDED.fire_affinity,
                grass_affinity    = EXCLUDED.grass_affinity,
                electric_affinity = EXCLUDED.electric_affinity,
                psychic_affinity  = EXCLUDED.psychic_affinity,
                normal_affinity   = EXCLUDED.normal_affinity,
                fighting_affinity = EXCLUDED.fighting_affinity,
                ghost_affinity    = EXCLUDED.ghost_affinity,
                ice_affinity      = EXCLUDED.ice_affinity,
                ground_affinity   = EXCLUDED.ground_affinity,
                rock_affinity     = EXCLUDED.rock_affinity,
                poison_affinity   = EXCLUDED.poison_affinity,
                dragon_affinity   = EXCLUDED.dragon_affinity;
        """, {"pokemon_id": pokemon_id, **affinity})

        conn.commit()

        type_str = primary_type + (f"/{secondary_type}" if secondary_type else "")
        top_affinities = sorted(affinity.items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ", ".join(f"{k}={v}" for k, v in top_affinities if v > 0)
        log.info(f"  #{pokemon_id:03d} {row['name_kr']} [{type_str}] → {top_str}")
        success += 1

    cursor.close()
    conn.close()

    log.info(f"===== 타입 친화도 계산 완료: {success}마리 =====")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="타입 친화도 자동 계산 스크립트")
    parser.add_argument("--start", type=int, default=1,   help="시작 번호")
    parser.add_argument("--end",   type=int, default=151, help="끝 번호")
    args = parser.parse_args()
    run(start=args.start, end=args.end)
