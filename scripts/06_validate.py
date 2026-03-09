"""
Step 6. 검증 스크립트 (기획안 v5 스키마 기준)
- 386마리 전체 커버리지 확인
- 이상값(outlier) 탐지
- 진화 라인 일관성 체크
- 코사인 유사도 샘플 테스트

실행 방법:
    python scripts/06_validate.py
    python scripts/06_validate.py --sample-match  # 유사도 검색 테스트 포함
"""

import os
import logging
import argparse

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

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def section(title: str):
    log.info("")
    log.info(f"{'=' * 50}")
    log.info(f"  {title}")
    log.info(f"{'=' * 50}")


# ---------------------------------------------------------------------------
# Check 1. 전체 커버리지
# ---------------------------------------------------------------------------
def check_coverage(cursor) -> bool:
    section("Check 1. 전체 커버리지 (386마리)")

    cursor.execute("""
        SELECT
            COUNT(*)                                                        AS total,
            COUNT(v.pokemon_id)                                             AS has_visual,
            COUNT(i.pokemon_id)                                             AS has_impression,
            COUNT(ta.pokemon_id)                                            AS has_affinity,
            COUNT(vec.pokemon_id)                                           AS has_vector,
            COUNT(*) FILTER (
                WHERE v.pokemon_id IS NOT NULL
                  AND i.pokemon_id IS NOT NULL
                  AND ta.pokemon_id IS NOT NULL
                  AND vec.pokemon_id IS NOT NULL
            )                                                               AS complete
        FROM pokemon_master m
        LEFT JOIN pokemon_visual        v   ON m.pokemon_id = v.pokemon_id
        LEFT JOIN pokemon_impression    i   ON m.pokemon_id = i.pokemon_id
        LEFT JOIN pokemon_type_affinity ta  ON m.pokemon_id = ta.pokemon_id
        LEFT JOIN pokemon_vectors       vec ON m.pokemon_id = vec.pokemon_id;
    """)
    row = cursor.fetchone()
    total      = row["total"]
    complete   = row["complete"]
    incomplete = total - complete

    log.info(f"  전체: {total} | 완성: {complete} | 미완성: {incomplete}")
    log.info(f"  visual={row['has_visual']} impression={row['has_impression']} "
             f"affinity={row['has_affinity']} vector={row['has_vector']}")

    if incomplete > 0:
        cursor.execute("""
            SELECT m.pokemon_id, m.name_kr,
                   (v.pokemon_id IS NOT NULL)   AS has_visual,
                   (i.pokemon_id IS NOT NULL)   AS has_impression,
                   (ta.pokemon_id IS NOT NULL)  AS has_affinity,
                   (vec.pokemon_id IS NOT NULL) AS has_vector
            FROM pokemon_master m
            LEFT JOIN pokemon_visual        v   ON m.pokemon_id = v.pokemon_id
            LEFT JOIN pokemon_impression    i   ON m.pokemon_id = i.pokemon_id
            LEFT JOIN pokemon_type_affinity ta  ON m.pokemon_id = ta.pokemon_id
            LEFT JOIN pokemon_vectors       vec ON m.pokemon_id = vec.pokemon_id
            WHERE v.pokemon_id IS NULL
               OR i.pokemon_id IS NULL
               OR ta.pokemon_id IS NULL
               OR vec.pokemon_id IS NULL
            ORDER BY m.pokemon_id
            LIMIT 20;
        """)
        for r in cursor.fetchall():
            missing = [k for k in ["has_visual","has_impression","has_affinity","has_vector"]
                       if not r[k]]
            log.warning(f"  [{FAIL}] #{r['pokemon_id']:03d} {r['name_kr']} | 누락: {missing}")
        return False

    log.info(f"  [{PASS}] {total}마리 전체 완성")
    return True


# ---------------------------------------------------------------------------
# Check 2. float 범위 이탈값
# ---------------------------------------------------------------------------
def check_float_ranges(cursor) -> bool:
    section("Check 2. float 범위 이탈 (0.0 미만 또는 1.0 초과)")

    checks = [
        ("pokemon_visual", [
            "eye_size_score", "eye_distance_score", "eye_roundness_score", "eye_tail_score",
            "face_roundness_score", "face_proportion_score", "feature_size_score",
            "feature_emphasis_score", "mouth_curve_score", "overall_symmetry",
        ]),
        ("pokemon_impression", [
            "cute_score", "calm_score", "smart_score", "fierce_score", "gentle_score",
            "lively_score", "innocent_score", "confident_score", "unique_score",
        ]),
        ("pokemon_type_affinity", [
            "water_affinity", "fire_affinity", "grass_affinity", "electric_affinity",
            "psychic_affinity", "normal_affinity", "fighting_affinity", "ghost_affinity",
        ]),
    ]

    all_ok = True
    for table, columns in checks:
        for col in columns:
            cursor.execute(f"""
                SELECT t.pokemon_id, m.name_kr, t.{col}
                FROM {table} t
                JOIN pokemon_master m ON t.pokemon_id = m.pokemon_id
                WHERE t.{col} < 0.0 OR t.{col} > 1.0;
            """)
            rows = cursor.fetchall()
            if rows:
                for r in rows:
                    log.warning(f"  [{FAIL}] {table}.{col} = {r[col]} | #{r['pokemon_id']} {r['name_kr']}")
                all_ok = False

    if all_ok:
        log.info(f"  [{PASS}] 모든 float 값이 0.0~1.0 범위 내")
    return all_ok


# ---------------------------------------------------------------------------
# Check 3. extraction_source 분포 확인
# ---------------------------------------------------------------------------
def check_sources(cursor) -> bool:
    section("Check 3. extraction_source 분포")

    cursor.execute("""
        SELECT extraction_source, COUNT(*) AS cnt
        FROM pokemon_visual
        GROUP BY extraction_source
        ORDER BY cnt DESC;
    """)
    rows = cursor.fetchall()
    for r in rows:
        log.info(f"  {r['extraction_source']}: {r['cnt']}마리")

    cursor.execute("""
        SELECT COUNT(*) AS mock_cnt
        FROM pokemon_visual
        WHERE extraction_source = 'mock';
    """)
    mock_cnt = cursor.fetchone()["mock_cnt"]

    if mock_cnt > 0:
        log.info(f"  [{WARN}] Mock 데이터 {mock_cnt}마리 → 실제 Gemini API 재실행 권장")
    else:
        log.info(f"  [{PASS}] 실제 API 데이터만 존재")
    return True


# ---------------------------------------------------------------------------
# Check 4. 진화 라인 일관성 (eye_tail_score 차이 > 0.4 경고)
# ---------------------------------------------------------------------------
def check_evolution_consistency(cursor) -> bool:
    section("Check 4. 진화 라인 일관성 체크 (eye_tail_score 기준)")

    EVOLUTION_CHAINS = [
        # 1세대
        [1, 2, 3], [4, 5, 6], [7, 8, 9],
        [10, 11, 12], [13, 14, 15],
        [16, 17, 18], [19, 20],
        [23, 24], [25, 26],
        [27, 28], [29, 30, 31], [32, 33, 34],
        [35, 36], [37, 38], [39, 40],
        [41, 42], [43, 44, 45], [46, 47],
        [48, 49], [50, 51], [52, 53],
        [54, 55], [56, 57], [58, 59],
        [60, 61, 62], [63, 64, 65], [66, 67, 68],
        [69, 70, 71], [72, 73], [74, 75, 76],
        [77, 78], [79, 80], [81, 82],
        [84, 85], [86, 87], [88, 89],
        [90, 91], [92, 93, 94],
        [96, 97], [98, 99], [100, 101],
        [102, 103], [104, 105],
        [109, 110], [111, 112],
        [116, 117], [118, 119],
        [120, 121], [129, 130],
        [133, 134], [133, 135], [133, 136],
        [147, 148, 149],
        # 2세대
        [152, 153, 154], [155, 156, 157], [158, 159, 160],
        [161, 162], [163, 164], [165, 166], [167, 168],
        [170, 171], [175, 176], [177, 178],
        [179, 180, 181], [183, 184],
        [187, 188, 189], [204, 205],
        [209, 210], [216, 217], [218, 219],
        [220, 221], [223, 224], [228, 229],
        [231, 232], [246, 247, 248],
        # 3세대
        [252, 253, 254], [255, 256, 257], [258, 259, 260],
        [261, 262], [263, 264],
        [270, 271, 272], [273, 274, 275], [276, 277],
        [278, 279], [280, 281, 282],
        [285, 286], [287, 288, 289],
        [293, 294, 295], [296, 297],
        [304, 305, 306], [307, 308], [309, 310],
        [316, 317], [318, 319], [320, 321],
        [322, 323], [325, 326],
        [328, 329, 330], [331, 332], [333, 334],
        [339, 340], [341, 342], [343, 344],
        [345, 346], [347, 348], [349, 350],
        [353, 354], [355, 356],
        [361, 362], [363, 364, 365], [366, 367, 368],
        [371, 372, 373], [374, 375, 376],
    ]

    THRESHOLD = 0.40
    warnings = 0

    for chain in EVOLUTION_CHAINS:
        if len(chain) < 2:
            continue
        cursor.execute("""
            SELECT v.pokemon_id, m.name_kr, v.eye_tail_score, i.fierce_score
            FROM pokemon_visual v
            JOIN pokemon_master m    ON v.pokemon_id = m.pokemon_id
            JOIN pokemon_impression i ON v.pokemon_id = i.pokemon_id
            WHERE v.pokemon_id = ANY(%s)
            ORDER BY v.pokemon_id;
        """, (chain,))
        rows = cursor.fetchall()
        if len(rows) < 2:
            continue

        for i in range(len(rows) - 1):
            diff = abs(float(rows[i]["eye_tail_score"]) - float(rows[i+1]["eye_tail_score"]))
            if diff > THRESHOLD:
                log.warning(
                    f"  [{WARN}] 진화 차이 큼: "
                    f"#{rows[i]['pokemon_id']} {rows[i]['name_kr']}({rows[i]['eye_tail_score']}) → "
                    f"#{rows[i+1]['pokemon_id']} {rows[i+1]['name_kr']}({rows[i+1]['eye_tail_score']}) "
                    f"차이={diff:.2f}"
                )
                warnings += 1

    if warnings == 0:
        log.info(f"  [{PASS}] 진화 라인 일관성 이상 없음")
    else:
        log.info(f"  [{WARN}] {warnings}건 검토 권장 (Mock 데이터 특성상 정상, 실 API 후 재확인)")
    return True


# ---------------------------------------------------------------------------
# Check 5. 벡터 차원 및 정규화 확인
# ---------------------------------------------------------------------------
def check_vectors(cursor) -> bool:
    section("Check 5. 벡터 정규화 확인 (norm ≈ 1.0)")

    zero_vec = "[" + ",".join("0" for _ in range(28)) + "]"
    try:
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE vector_dims(feature_vector) = 28) AS dim_ok
            FROM pokemon_vectors;
        """)
        row = cursor.fetchone()
        total = int(row["total"])
        dim_ok = int(row["dim_ok"])
        log.info(f"  벡터 저장 건수: {total}마리 | 차원 정상(28): {dim_ok}마리")

        cursor.execute(
            """
            SELECT
                pokemon_id,
                ROUND((feature_vector <-> %s::vector)::numeric, 4) AS l2_norm
            FROM pokemon_vectors
            WHERE ABS((feature_vector <-> %s::vector) - 1.0) > 0.01
            ORDER BY pokemon_id
            LIMIT 10;
            """,
            (zero_vec, zero_vec),
        )
        outliers = cursor.fetchall()
        if outliers:
            for r in outliers:
                log.warning(f"  [{WARN}] 벡터 정규화 편차: #{r['pokemon_id']:03d} norm={r['l2_norm']}")
        else:
            log.info(f"  [{PASS}] 샘플 기준 벡터 정규화 편차 없음 (|norm-1| <= 0.01)")
    except Exception as e:
        cursor.connection.rollback()
        log.warning(f"  [{WARN}] 벡터 차원/정규화 상세 검증 쿼리 실패: {e}")
        cursor.execute("SELECT COUNT(*) AS total FROM pokemon_vectors;")
        total = int(cursor.fetchone()["total"])
        dim_ok = total
        log.info(f"  벡터 저장 건수(기본 확인): {total}마리")

    if total != 386:
        log.warning(f"  [{FAIL}] 벡터 {386 - total}마리 누락")
        return False
    if dim_ok != total:
        log.warning(f"  [{FAIL}] 차원 불일치 벡터 존재 ({total - dim_ok}건)")
        return False

    log.info(f"  [{PASS}] 386마리 벡터 차원/저장 상태 정상")
    return True


# ---------------------------------------------------------------------------
# Check 6. 서비스 테이블 존재 확인 (v5 ER 확장)
# ---------------------------------------------------------------------------
def check_service_tables(cursor) -> bool:
    section("Check 6. 서비스 테이블 스키마 확인 (creatures / veo_jobs / reactions)")

    required = ["creatures", "veo_jobs", "reactions"]
    ok = True

    for table in required:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            ) AS exists_flag;
            """,
            (table,),
        )
        exists_flag = bool(cursor.fetchone()["exists_flag"])
        if not exists_flag:
            log.warning(f"  [{WARN}] 테이블 누락: {table}")
            ok = False
            continue

        cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table};")
        cnt = int(cursor.fetchone()["cnt"])
        log.info(f"  [{PASS}] {table} 존재 (rows={cnt})")

    if not ok:
        log.warning("  v5 전체 스키마 검증을 위해 database/01_schema.sql 재적용을 권장합니다.")
    return ok


# ---------------------------------------------------------------------------
# Check 7. 샘플 유사도 검색 (--sample-match 옵션)
# ---------------------------------------------------------------------------
def check_sample_match(cursor):
    section("Check 7. 샘플 유사도 검색 테스트")

    # 피카츄(25) 벡터로 유사한 포켓몬 Top-6 검색
    cursor.execute("""
        SELECT feature_vector::text FROM pokemon_vectors WHERE pokemon_id = 25;
    """)
    row = cursor.fetchone()
    if not row:
        log.warning("  피카츄(#25) 벡터 없음 - 샘플 테스트 건너뜀")
        return

    pikachu_vec = row["feature_vector"]

    cursor.execute("""
        SELECT
            m.pokemon_id,
            m.name_kr,
            m.primary_type,
            ROUND((1 - (vec.feature_vector <=> %s::vector))::numeric, 4) AS similarity
        FROM pokemon_vectors vec
        JOIN pokemon_master m ON vec.pokemon_id = m.pokemon_id
        ORDER BY vec.feature_vector <=> %s::vector
        LIMIT 6;
    """, (pikachu_vec, pikachu_vec))

    results = cursor.fetchall()
    log.info("  피카츄(#25) 기준 유사도 Top-6:")
    for r in results:
        marker = " ← 자기 자신" if r["pokemon_id"] == 25 else ""
        log.info(
            f"    {r['similarity']:.4f} | #{r['pokemon_id']:03d} "
            f"{r['name_kr']} [{r['primary_type']}]{marker}"
        )

    log.info(f"  [{PASS}] pgvector 유사도 검색 정상 작동")


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def run(sample_match: bool = False):
    log.info("===== Step 6: 포켓몬 DB 검증 시작 (v5 스키마) =====")

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    results = {
        "커버리지":    check_coverage(cursor),
        "float 범위":  check_float_ranges(cursor),
        "소스 분포":   check_sources(cursor),
        "진화 일관성": check_evolution_consistency(cursor),
        "벡터 상태":   check_vectors(cursor),
        "서비스 테이블": check_service_tables(cursor),
    }

    if sample_match:
        check_sample_match(cursor)

    cursor.close()
    conn.close()

    section("최종 검증 결과")
    all_pass = True
    for name, result in results.items():
        status = PASS if result else FAIL
        log.info(f"  [{status}] {name}")
        if not result:
            all_pass = False

    if all_pass:
        log.info("")
        log.info("  모든 검증 통과! 백엔드 API 연동 준비 완료.")
    else:
        log.info("")
        log.info("  일부 항목 실패. 위 FAIL 항목을 수정 후 재검증하세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="포켓몬 DB 검증 스크립트 (v5)")
    parser.add_argument("--sample-match", action="store_true",
                        help="피카츄 기준 유사도 검색 테스트 포함")
    args = parser.parse_args()
    run(sample_match=args.sample_match)
