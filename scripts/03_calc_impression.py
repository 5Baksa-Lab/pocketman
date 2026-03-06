"""
Step 3. 인상 점수 자동 계산 스크립트
입력: pokemon_face_shape + pokemon_eye_features + pokemon_style_features + pokemon_emotion_features
출력: pokemon_impression_scores (9개 차원)

실행 방법:
    python scripts/03_calc_impression.py
    python scripts/03_calc_impression.py --start 1 --end 30
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


# ---------------------------------------------------------------------------
# 인상 점수 계산 공식
# ---------------------------------------------------------------------------
def clamp(v: float, lo=0.0, hi=1.0) -> float:
    return round(max(lo, min(hi, float(v))), 2)


def calc_impression(row: dict) -> dict:
    """
    face_shape + eye + style + emotion 값을 받아 9개 인상 점수를 반환

    row 예상 키:
        face_aspect_ratio, jawline_angle,
        eye_size_ratio, eye_distance_ratio, eye_slant_angle,
        has_glasses, has_facial_hair, has_bangs,
        smile_score, emotion_class
    """
    f_asp  = float(row.get("face_aspect_ratio",  0.5))
    jaw    = float(row.get("jawline_angle",       0.5))
    e_sz   = float(row.get("eye_size_ratio",      0.5))
    e_dist = float(row.get("eye_distance_ratio",  0.5))
    e_sl   = float(row.get("eye_slant_angle",     0.5))
    glasses = 1.0 if row.get("has_glasses")      else 0.0
    f_hair  = 1.0 if row.get("has_facial_hair")  else 0.0
    bangs   = 1.0 if row.get("has_bangs")        else 0.0
    smile  = float(row.get("smile_score",         0.5))
    emo    = row.get("emotion_class", "무표정")

    # emotion_class 보너스 매핑
    emo_bonus = {
        "기쁨":  {"cute": 0.15, "lively": 0.15, "gentle": 0.10},
        "온화":  {"calm": 0.15, "gentle": 0.15, "innocent": 0.10},
        "신비":  {"unique": 0.20, "calm": 0.10},
        "분노":  {"fierce": 0.20, "confident": 0.10},
        "슬픔":  {"calm": 0.10, "innocent": 0.10},
        "공포":  {"unique": 0.15, "fierce": 0.10},
        "무표정": {},
    }
    bonus = emo_bonus.get(emo, {})

    # --- 9개 인상 점수 계산 ---

    # cute: 큰 눈 + 둥근 얼굴 + 올라간 입꼬리
    cute = (e_sz * 0.40) + (f_asp * 0.30) + (smile * 0.30)
    cute = clamp(cute + bonus.get("cute", 0))

    # calm: 처진(중립) 눈꼬리 + 둥근 턱선 + 중립 smile
    calm_eye  = 1.0 - abs(e_sl - 0.5) * 2        # 0.5에 가까울수록 높음
    calm_smile = 1.0 - abs(smile - 0.5) * 2
    calm = (calm_eye * 0.40) + (jaw * 0.30) + (calm_smile * 0.30)
    calm = clamp(calm + bonus.get("calm", 0))

    # smart: 안경 + 좁은 미간 + 좁은 눈
    smart = (glasses * 0.50) + ((1.0 - e_dist) * 0.30) + ((1.0 - e_sz) * 0.20)
    smart = clamp(smart + bonus.get("smart", 0))

    # fierce: 올라간 눈꼬리 + 각진 턱선 + 찌푸린 표정
    fierce = (e_sl * 0.50) + ((1.0 - jaw) * 0.30) + ((1.0 - smile) * 0.20)
    fierce = clamp(fierce + bonus.get("fierce", 0))

    # gentle: 미소 + 둥근 턱선 + 처진 눈꼬리
    gentle = (smile * 0.40) + (jaw * 0.30) + ((1.0 - e_sl) * 0.30)
    gentle = clamp(gentle + bonus.get("gentle", 0))

    # lively: 미소 + 큰 눈 + 강조된 이목구비(f_hair/bangs)
    feature_emphasis = max(f_hair * 0.3, bangs * 0.3)
    lively = (smile * 0.40) + (e_sz * 0.30) + (feature_emphasis * 0.30)
    lively = clamp(lively + bonus.get("lively", 0))

    # innocent: 큰 눈 + 둥근 턱선 + 낮은 fierce
    innocent = (e_sz * 0.40) + (jaw * 0.30) + ((1.0 - fierce) * 0.30)
    innocent = clamp(innocent + bonus.get("innocent", 0))

    # confident: 올라간 눈꼬리 + 각진 턱선 + 수염(위협감)
    confident = (e_sl * 0.35) + ((1.0 - jaw) * 0.35) + (f_hair * 0.30)
    confident = clamp(confident + bonus.get("confident", 0))

    # unique: 안경 or 극단적 눈 크기 + 앞머리
    eye_extremity = abs(e_sz - 0.5) * 2   # 0 또는 1에 가까울수록 높음
    unique = (glasses * 0.30) + (eye_extremity * 0.40) + (bangs * 0.30)
    unique = clamp(unique + bonus.get("unique", 0))

    return {
        "cute_score":      cute,
        "calm_score":      calm,
        "smart_score":     smart,
        "fierce_score":    fierce,
        "gentle_score":    gentle,
        "lively_score":    lively,
        "innocent_score":  innocent,
        "confident_score": confident,
        "unique_score":    unique,
    }


# ---------------------------------------------------------------------------
# DB 처리
# ---------------------------------------------------------------------------
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def run(start: int, end: int):
    log.info(f"===== 인상 점수 계산 시작: #{start} ~ #{end} =====")

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 필요한 값 JOIN 조회
    cursor.execute("""
        SELECT
            m.pokemon_id, m.name_kr,
            fs.face_aspect_ratio, fs.jawline_angle,
            ey.eye_size_ratio, ey.eye_distance_ratio, ey.eye_slant_angle,
            st.has_glasses, st.has_facial_hair, st.has_bangs,
            em.smile_score, em.emotion_class
        FROM pokemon_master m
        JOIN pokemon_face_shape          fs ON m.pokemon_id = fs.pokemon_id
        JOIN pokemon_eye_features        ey ON m.pokemon_id = ey.pokemon_id
        JOIN pokemon_style_features      st ON m.pokemon_id = st.pokemon_id
        JOIN pokemon_emotion_features    em ON m.pokemon_id = em.pokemon_id
        WHERE m.pokemon_id BETWEEN %s AND %s
        ORDER BY m.pokemon_id;
    """, (start, end))

    rows = cursor.fetchall()
    log.info(f"처리 대상: {len(rows)}마리")

    success = 0
    for row in rows:
        pokemon_id = row["pokemon_id"]
        scores = calc_impression(row)

        cursor.execute("""
            INSERT INTO pokemon_impression_scores (
                pokemon_id,
                cute_score, calm_score, smart_score, fierce_score, gentle_score,
                lively_score, innocent_score, confident_score, unique_score,
                derivation_note
            ) VALUES (
                %(pokemon_id)s,
                %(cute_score)s, %(calm_score)s, %(smart_score)s, %(fierce_score)s, %(gentle_score)s,
                %(lively_score)s, %(innocent_score)s, %(confident_score)s, %(unique_score)s,
                'auto_from_face_eye_style_emotion_v1'
            )
            ON CONFLICT (pokemon_id) DO UPDATE SET
                cute_score      = EXCLUDED.cute_score,
                calm_score      = EXCLUDED.calm_score,
                smart_score     = EXCLUDED.smart_score,
                fierce_score    = EXCLUDED.fierce_score,
                gentle_score    = EXCLUDED.gentle_score,
                lively_score    = EXCLUDED.lively_score,
                innocent_score  = EXCLUDED.innocent_score,
                confident_score = EXCLUDED.confident_score,
                unique_score    = EXCLUDED.unique_score,
                derivation_note = EXCLUDED.derivation_note;
        """, {"pokemon_id": pokemon_id, **scores})

        conn.commit()
        log.info(
            f"  #{pokemon_id:03d} {row['name_kr']} | "
            f"cute={scores['cute_score']} calm={scores['calm_score']} "
            f"smart={scores['smart_score']} fierce={scores['fierce_score']}"
        )
        success += 1

    cursor.close()
    conn.close()

    log.info(f"===== 인상 점수 계산 완료: {success}마리 =====")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="인상 점수 자동 계산 스크립트")
    parser.add_argument("--start", type=int, default=1,   help="시작 번호")
    parser.add_argument("--end",   type=int, default=151, help="끝 번호")
    args = parser.parse_args()
    run(start=args.start, end=args.end)
