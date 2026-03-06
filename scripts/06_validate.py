"""
Step 6. 검증 스크립트
- 151마리 전체 커버리지 확인
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
# Check 1. 전체 커버리지 (151마리 완성도)
# ---------------------------------------------------------------------------
def check_coverage(cursor) -> bool:
    section("Check 1. 전체 커버리지")

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE is_complete = TRUE)  AS complete,
            COUNT(*) FILTER (WHERE is_complete = FALSE) AS incomplete,
            COUNT(*)                                     AS total
        FROM v_pokemon_coverage;
    """)
    row = cursor.fetchone()
    complete   = row["complete"]
    incomplete = row["incomplete"]
    total      = row["total"]

    log.info(f"  전체: {total} | 완성: {complete} | 미완성: {incomplete}")

    if incomplete > 0:
        cursor.execute("""
            SELECT pokemon_id, name_kr,
                   has_face_shape, has_eye, has_nose_mouth,
                   has_style, has_emotion, has_impression,
                   has_type_affinity, has_vector
            FROM v_pokemon_coverage
            WHERE is_complete = FALSE
            ORDER BY pokemon_id;
        """)
        for r in cursor.fetchall():
            missing = [k for k, v in dict(r).items() if k.startswith("has_") and not v]
            log.warning(f"  [{FAIL}] #{r['pokemon_id']:03d} {r['name_kr']} | 누락: {missing}")
        return False

    log.info(f"  [{PASS}] 151마리 전체 완성")
    return True


# ---------------------------------------------------------------------------
# Check 2. float 범위 이탈값
# ---------------------------------------------------------------------------
def check_float_ranges(cursor) -> bool:
    section("Check 2. float 범위 이탈 (0.0 미만 또는 1.0 초과)")

    checks = [
        ("pokemon_face_shape",          ["face_aspect_ratio", "jawline_angle"]),
        ("pokemon_eye_features",        ["eye_size_ratio", "eye_distance_ratio", "eye_slant_angle"]),
        ("pokemon_nose_mouth_features", ["nose_length_ratio", "nose_width_ratio",
                                         "mouth_width_ratio", "lip_thickness_ratio", "philtrum_ratio"]),
        ("pokemon_emotion_features",    ["smile_score"]),
        ("pokemon_impression_scores",   ["cute_score", "calm_score", "smart_score", "fierce_score",
                                         "gentle_score", "lively_score", "innocent_score",
                                         "confident_score", "unique_score"]),
        ("pokemon_type_affinity",       ["water_affinity", "fire_affinity", "grass_affinity",
                                         "electric_affinity", "psychic_affinity", "ghost_affinity"]),
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
# Check 3. emotion_class 허용값 검증
# ---------------------------------------------------------------------------
def check_emotion_classes(cursor) -> bool:
    section("Check 3. emotion_class 허용값 검증")

    ALLOWED = ("기쁨", "무표정", "분노", "신비", "온화", "슬픔", "공포")
    cursor.execute("""
        SELECT e.pokemon_id, m.name_kr, e.emotion_class
        FROM pokemon_emotion_features e
        JOIN pokemon_master m ON e.pokemon_id = m.pokemon_id
        WHERE e.emotion_class NOT IN %s;
    """, (ALLOWED,))

    rows = cursor.fetchall()
    if rows:
        for r in rows:
            log.warning(f"  [{FAIL}] #{r['pokemon_id']:03d} {r['name_kr']} | emotion_class={r['emotion_class']}")
        return False

    log.info(f"  [{PASS}] 모든 emotion_class 허용값 내")
    return True


# ---------------------------------------------------------------------------
# Check 4. personality_class 최대 4개 / 허용 키워드 검증
# ---------------------------------------------------------------------------
def check_personality(cursor) -> bool:
    section("Check 4. personality_class 검증 (최대 4개, 허용 키워드)")

    ALLOWED_SET = {
        "용감한", "온화한", "조심스러운", "명랑한", "냉정한", "건방진",
        "고집스러운", "느긋한", "개구쟁이", "뻔뻔한", "호기심많은",
        "외로움을타는", "수줍은", "사나운", "신중한", "충성스러운",
    }

    cursor.execute("""
        SELECT e.pokemon_id, m.name_kr, e.personality_class
        FROM pokemon_emotion_features e
        JOIN pokemon_master m ON e.pokemon_id = m.pokemon_id;
    """)

    all_ok = True
    for r in cursor.fetchall():
        personalities = [p.strip() for p in r["personality_class"].split(",") if p.strip()]
        invalid = [p for p in personalities if p not in ALLOWED_SET]
        if len(personalities) > 4:
            log.warning(f"  [{FAIL}] #{r['pokemon_id']:03d} {r['name_kr']} | 4개 초과: {personalities}")
            all_ok = False
        if invalid:
            log.warning(f"  [{FAIL}] #{r['pokemon_id']:03d} {r['name_kr']} | 허용 외 키워드: {invalid}")
            all_ok = False

    if all_ok:
        log.info(f"  [{PASS}] personality_class 모두 유효")
    return all_ok


# ---------------------------------------------------------------------------
# Check 5. 진화 라인 일관성 (차이 > 0.4 경고)
# ---------------------------------------------------------------------------
def check_evolution_consistency(cursor) -> bool:
    section("Check 5. 진화 라인 일관성 체크 (eye_slant_angle 기준)")

    # 1세대 주요 진화 라인
    EVOLUTION_CHAINS = [
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
        [90, 91], [92, 93, 94], [95],
        [96, 97], [98, 99], [100, 101],
        [102, 103], [104, 105], [106], [107], [108],
        [109, 110], [111, 112], [113],
        [114], [115], [116, 117], [118, 119],
        [120, 121], [122], [123], [124], [125], [126],
        [127], [128], [129, 130], [131], [132], [133, 134, 135, 136],
        [137, 138, 139], [140, 141], [142], [143], [144], [145], [146],
        [147, 148, 149], [150], [151],
    ]

    THRESHOLD = 0.40
    warnings = 0

    for chain in EVOLUTION_CHAINS:
        if len(chain) < 2:
            continue
        cursor.execute("""
            SELECT e.pokemon_id, m.name_kr, e.eye_slant_angle, i.fierce_score
            FROM pokemon_eye_features e
            JOIN pokemon_master m ON e.pokemon_id = m.pokemon_id
            JOIN pokemon_impression_scores i ON e.pokemon_id = i.pokemon_id
            WHERE e.pokemon_id = ANY(%s)
            ORDER BY e.pokemon_id;
        """, (chain,))
        rows = cursor.fetchall()
        if len(rows) < 2:
            continue

        for i in range(len(rows) - 1):
            diff = abs(float(rows[i]["eye_slant_angle"]) - float(rows[i+1]["eye_slant_angle"]))
            if diff > THRESHOLD:
                log.warning(
                    f"  [{WARN}] 진화 차이 큼: "
                    f"#{rows[i]['pokemon_id']} {rows[i]['name_kr']}({rows[i]['eye_slant_angle']}) → "
                    f"#{rows[i+1]['pokemon_id']} {rows[i+1]['name_kr']}({rows[i+1]['eye_slant_angle']}) "
                    f"차이={diff:.2f}"
                )
                warnings += 1

    if warnings == 0:
        log.info(f"  [{PASS}] 진화 라인 일관성 이상 없음")
    else:
        log.info(f"  [{WARN}] {warnings}건 검토 권장 (수동 보정 불필요, 참고용)")
    return True


# ---------------------------------------------------------------------------
# Check 6. confidence 낮은 항목 (수동 검수 필요)
# ---------------------------------------------------------------------------
def check_low_confidence(cursor):
    section("Check 6. 수동 검수 필요 목록 (confidence < 0.70)")

    cursor.execute("""
        SELECT pokemon_id, name_kr,
               face_confidence, eye_confidence, nose_mouth_confidence
        FROM v_pokemon_review_needed
        ORDER BY pokemon_id
        LIMIT 20;
    """)
    rows = cursor.fetchall()

    if not rows:
        log.info(f"  [{PASS}] 수동 검수 대상 없음")
    else:
        log.info(f"  [{WARN}] 검수 대상 {len(rows)}마리:")
        for r in rows:
            log.info(
                f"    #{r['pokemon_id']:03d} {r['name_kr']} | "
                f"face={r['face_confidence']} eye={r['eye_confidence']} "
                f"nose_mouth={r['nose_mouth_confidence']}"
            )


# ---------------------------------------------------------------------------
# Check 7. 샘플 유사도 검색 (--sample-match 옵션)
# ---------------------------------------------------------------------------
def check_sample_match(cursor):
    section("Check 7. 샘플 유사도 검색 테스트")

    # 피카츄(25) 벡터로 유사한 포켓몬 Top-5 검색
    cursor.execute("""
        SELECT feature_vector::text FROM pokemon_feature_vectors WHERE pokemon_id = 25;
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
            ROUND((1 - (fv.feature_vector <=> %s::vector))::numeric, 4) AS similarity
        FROM pokemon_feature_vectors fv
        JOIN pokemon_master m ON fv.pokemon_id = m.pokemon_id
        ORDER BY fv.feature_vector <=> %s::vector
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
    log.info("===== 포켓몬 DB 검증 시작 =====")

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    results = {
        "커버리지":       check_coverage(cursor),
        "float 범위":    check_float_ranges(cursor),
        "emotion_class": check_emotion_classes(cursor),
        "personality":   check_personality(cursor),
        "진화 일관성":   check_evolution_consistency(cursor),
    }
    check_low_confidence(cursor)

    if sample_match:
        check_sample_match(cursor)

    cursor.close()
    conn.close()

    # 최종 결과 요약
    section("최종 검증 결과")
    all_pass = True
    for name, result in results.items():
        status = PASS if result else FAIL
        log.info(f"  [{status}] {name}")
        if not result:
            all_pass = False

    if all_pass:
        log.info("")
        log.info("  모든 검증 통과! Step 5 이후 서비스 연동 가능합니다.")
    else:
        log.info("")
        log.info("  일부 항목 실패. 위 FAIL 항목을 수정 후 재검증하세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="포켓몬 DB 검증 스크립트")
    parser.add_argument("--sample-match", action="store_true",
                        help="피카츄 기준 유사도 검색 테스트 포함")
    args = parser.parse_args()
    run(sample_match=args.sample_match)
