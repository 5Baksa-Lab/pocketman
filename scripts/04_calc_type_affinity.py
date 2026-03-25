"""
Step 4. 타입 친화도 자동 계산 스크립트
기획안 v5 §6-5 "Category 3: 타입 친화도 (Type Affinity)" 기준

입력: pokemon_master.primary_type / secondary_type
출력: pokemon_type_affinity (8차원)

8차원: water, fire, grass, electric, psychic, normal, fighting, ghost

계산 규칙:
  - 1타입만 있으면: 해당 타입 친화도 가중치 × 1.0
  - 2타입이면: 1타입 × 0.7 + 2타입 × 0.3

실행 방법:
    python scripts/04_calc_type_affinity.py
    python scripts/04_calc_type_affinity.py --start 1 --end 386
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
COMMIT_BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# 타입 → 8차원 친화도 룰 테이블 (기획안 v5 §6-5)
# ---------------------------------------------------------------------------
# 8개 타입: water, fire, grass, electric, psychic, normal, fighting, ghost
TYPE_TO_AFFINITY: dict[str, dict[str, float]] = {
    # === 기본 8타입 (직접 매핑) ===
    "노말":   {"normal_affinity": 1.0},
    "불꽃":   {"fire_affinity": 1.0},
    "물":     {"water_affinity": 1.0},
    "풀":     {"grass_affinity": 1.0},
    "전기":   {"electric_affinity": 1.0},
    "에스퍼": {"psychic_affinity": 1.0},
    "격투":   {"fighting_affinity": 1.0},
    "고스트": {"ghost_affinity": 1.0},

    # === 나머지 타입 → 8차원으로 근사 매핑 ===
    "얼음":   {"water_affinity": 0.70, "normal_affinity": 0.30},     # 차갑고 순수함
    "독":     {"psychic_affinity": 0.60, "ghost_affinity": 0.40},    # 신비롭고 음침
    "땅":     {"normal_affinity": 0.70, "fighting_affinity": 0.30},  # 단단하고 직선적
    "비행":   {"normal_affinity": 0.50, "water_affinity": 0.30, "ghost_affinity": 0.20},
    "벌레":   {"grass_affinity": 0.70, "normal_affinity": 0.30},     # 자연친화적
    "바위":   {"normal_affinity": 0.50, "fighting_affinity": 0.50},  # 강인함
    "드래곤": {"psychic_affinity": 0.50, "fighting_affinity": 0.50}, # 강력하고 신비
    "악":     {"ghost_affinity": 0.60, "fighting_affinity": 0.40},   # 어둡고 공격적
    "강철":   {"fighting_affinity": 0.50, "normal_affinity": 0.50},  # 강하고 견고
    "페어리": {"psychic_affinity": 0.60, "normal_affinity": 0.40},   # 신비롭고 친근
}

TYPE_NAME_ALIASES: dict[str, str] = {
    "normal": "노말",
    "fire": "불꽃",
    "water": "물",
    "grass": "풀",
    "electric": "전기",
    "ice": "얼음",
    "fighting": "격투",
    "poison": "독",
    "ground": "땅",
    "flying": "비행",
    "psychic": "에스퍼",
    "bug": "벌레",
    "rock": "바위",
    "ghost": "고스트",
    "dragon": "드래곤",
    "dark": "악",
    "steel": "강철",
    "fairy": "페어리",
}

AFFINITY_COLUMNS = [
    "water_affinity", "fire_affinity", "grass_affinity", "electric_affinity",
    "psychic_affinity", "normal_affinity", "fighting_affinity", "ghost_affinity",
]


# ---------------------------------------------------------------------------
# 친화도 계산
# ---------------------------------------------------------------------------
def clamp(v: float) -> float:
    return round(max(0.0, min(1.0, v)), 3)


def normalize_type_name(type_name: Optional[str]) -> Optional[str]:
    if type_name is None:
        return None
    key = str(type_name).strip().lower()
    return TYPE_NAME_ALIASES.get(key, str(type_name).strip())


def calc_type_affinity(
    primary_type: str,
    secondary_type: Optional[str],
) -> dict[str, float]:
    result = {col: 0.0 for col in AFFINITY_COLUMNS}

    primary_weights = TYPE_TO_AFFINITY.get(primary_type, {"normal_affinity": 1.0})
    weight_1 = 0.7 if secondary_type else 1.0
    for col, val in primary_weights.items():
        if col in result:
            result[col] += val * weight_1

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
    log.info(f"===== Step 4: 타입 친화도 계산 시작: #{start}~#{end} =====")

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
    failed = 0
    pending_commits = 0
    for row in rows:
        pokemon_id     = row["pokemon_id"]
        primary_type   = normalize_type_name(row["primary_type"]) or "노말"
        secondary_type = normalize_type_name(row["secondary_type"])

        if primary_type not in TYPE_TO_AFFINITY:
            log.warning(f"  #{pokemon_id} 알 수 없는 타입: {primary_type} → 노말 처리")
            primary_type = "노말"
        if secondary_type and secondary_type not in TYPE_TO_AFFINITY:
            log.warning(f"  #{pokemon_id} 알 수 없는 보조 타입: {secondary_type} → 무시")
            secondary_type = None

        affinity = calc_type_affinity(primary_type, secondary_type)

        cursor.execute("SAVEPOINT sp_affinity_row")
        try:
            cursor.execute("""
                INSERT INTO pokemon_type_affinity (
                    pokemon_id,
                    water_affinity, fire_affinity, grass_affinity, electric_affinity,
                    psychic_affinity, normal_affinity, fighting_affinity, ghost_affinity
                ) VALUES (
                    %(pokemon_id)s,
                    %(water_affinity)s, %(fire_affinity)s,
                    %(grass_affinity)s, %(electric_affinity)s,
                    %(psychic_affinity)s, %(normal_affinity)s,
                    %(fighting_affinity)s, %(ghost_affinity)s
                )
                ON CONFLICT (pokemon_id) DO UPDATE SET
                    water_affinity    = EXCLUDED.water_affinity,
                    fire_affinity     = EXCLUDED.fire_affinity,
                    grass_affinity    = EXCLUDED.grass_affinity,
                    electric_affinity = EXCLUDED.electric_affinity,
                    psychic_affinity  = EXCLUDED.psychic_affinity,
                    normal_affinity   = EXCLUDED.normal_affinity,
                    fighting_affinity = EXCLUDED.fighting_affinity,
                    ghost_affinity    = EXCLUDED.ghost_affinity;
            """, {"pokemon_id": pokemon_id, **affinity})
            cursor.execute("RELEASE SAVEPOINT sp_affinity_row")
            pending_commits += 1
            if pending_commits >= COMMIT_BATCH_SIZE:
                conn.commit()
                pending_commits = 0
        except Exception as e:
            cursor.execute("ROLLBACK TO SAVEPOINT sp_affinity_row")
            cursor.execute("RELEASE SAVEPOINT sp_affinity_row")
            log.error(f"  DB 저장 오류 #{pokemon_id}: {e}")
            failed += 1
            continue

        type_str = primary_type + (f"/{secondary_type}" if secondary_type else "")
        top = sorted(affinity.items(), key=lambda x: x[1], reverse=True)[:2]
        top_str = ", ".join(f"{k}={v}" for k, v in top if v > 0)
        log.info(f"  #{pokemon_id:03d} {row['name_kr']} [{type_str}] → {top_str}")
        success += 1

    if pending_commits > 0:
        conn.commit()

    cursor.close()
    conn.close()
    log.info(f"===== Step 4: 타입 친화도 계산 완료: 성공 {success}마리 | 실패 {failed}마리 =====")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="타입 친화도 자동 계산 스크립트 (v5, 8차원)")
    parser.add_argument("--start", type=int, default=1,   help="시작 번호")
    parser.add_argument("--end",   type=int, default=386, help="끝 번호")
    args = parser.parse_args()
    run(start=args.start, end=args.end)
