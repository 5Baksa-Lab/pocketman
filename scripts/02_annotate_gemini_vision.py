"""
Step 2. Gemini Vision 시각 특징 주석 배치 스크립트
기획안 v5 §6-3 "Category 1: 시각적 특징 (Visual Features)" 기준

입력: pokemon_master.sprite_url
출력: pokemon_visual (10차원 스코어 + has_glasses)

벡터 차원 [0-9]:
  eye_size_score, eye_distance_score, eye_roundness_score, eye_tail_score,
  face_roundness_score, face_proportion_score, feature_size_score,
  feature_emphasis_score, mouth_curve_score, overall_symmetry

실행 방법:
    USE_MOCK_AI=true python scripts/02_annotate_gemini_vision.py
    python scripts/02_annotate_gemini_vision.py --start 1 --end 386
    python scripts/02_annotate_gemini_vision.py --retry-failed
"""

import os
import json
import time
import random
import logging
import argparse
from typing import Optional

import httpx
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

USE_MOCK_AI     = os.environ.get("USE_MOCK_AI", "false").lower() == "true"
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL    = "gemini-2.0-flash"
REQUEST_DELAY   = 1.5
BATCH_SIZE      = 10
COMMIT_BATCH_SIZE = 20


# ---------------------------------------------------------------------------
# Gemini Vision 프롬프트 (10차원 스코어 직접 출력)
# ---------------------------------------------------------------------------
VISION_PROMPT = """
당신은 포켓몬 스프라이트 이미지를 분석하는 전문가입니다.
아래 이미지의 포켓몬 얼굴 특징을 0.0~1.0 스코어로 분석하여 반드시 JSON만 출력하세요.
설명, 마크다운 코드블록, 추가 텍스트 없이 JSON 객체만 출력합니다.

[스코어 기준 - 기획안 v5 §6-3]
- eye_size_score:         0=작은눈, 1=매우큰눈 (눈세로/얼굴세로)
- eye_distance_score:     0=좁은미간, 1=넓은미간 (미간/얼굴가로)
- eye_roundness_score:    0=날카로운눈, 1=둥근눈 (눈가로:세로비율)
- eye_tail_score:         0=처진눈꼬리(온화), 1=올라간눈꼬리(공격적)
- face_roundness_score:   0=각진얼굴(V형), 1=둥근얼굴(U형)
- face_proportion_score:  0=가로형얼굴, 1=세로형얼굴
- feature_size_score:     0=이목구비작음, 1=이목구비큼 (코+입너비/얼굴가로)
- feature_emphasis_score: 0=이목구비약함, 1=이목구비강함 (눈썹+코볼 강조)
- mouth_curve_score:      0=처진입꼬리(찌푸림), 1=올라간입꼬리(미소)
- overall_symmetry:       0=비대칭, 1=좌우대칭
- has_glasses:            안경/안경형 디자인 true/false

[예외 처리]
- 눈 없는 포켓몬: eye_size_score=0.0, eye_roundness_score=0.5
- 전신이 눈인 포켓몬(꼬마돌 등): eye_size_score=1.0
- 비인간형: 가능한 근사치로 추정

출력 형식 (이것만 출력):
{
  "eye_size_score": 0.50,
  "eye_distance_score": 0.50,
  "eye_roundness_score": 0.50,
  "eye_tail_score": 0.50,
  "face_roundness_score": 0.50,
  "face_proportion_score": 0.50,
  "feature_size_score": 0.50,
  "feature_emphasis_score": 0.50,
  "mouth_curve_score": 0.50,
  "overall_symmetry": 0.80,
  "has_glasses": false
}
"""

SCORE_FIELDS = [
    "eye_size_score", "eye_distance_score", "eye_roundness_score", "eye_tail_score",
    "face_roundness_score", "face_proportion_score", "feature_size_score",
    "feature_emphasis_score", "mouth_curve_score", "overall_symmetry",
]


# ---------------------------------------------------------------------------
# Mock 데이터 생성
# ---------------------------------------------------------------------------
def generate_mock_annotation(pokemon_id: int) -> dict:
    """포켓몬 ID 기반 시드로 재현 가능한 Mock 스코어 생성"""
    rng = random.Random(pokemon_id * 42)

    def r(lo=0.2, hi=0.8) -> float:
        return round(rng.uniform(lo, hi), 3)

    return {
        "eye_size_score":          r(0.2, 0.9),
        "eye_distance_score":      r(0.3, 0.8),
        "eye_roundness_score":     r(0.2, 0.9),
        "eye_tail_score":          r(0.1, 0.9),
        "face_roundness_score":    r(0.2, 0.9),
        "face_proportion_score":   r(0.3, 0.8),
        "feature_size_score":      r(0.2, 0.8),
        "feature_emphasis_score":  r(0.1, 0.8),
        "mouth_curve_score":       r(0.1, 0.9),
        "overall_symmetry":        r(0.5, 1.0),
        "has_glasses":             rng.random() < 0.05,
    }


# ---------------------------------------------------------------------------
# Gemini Vision 호출
# ---------------------------------------------------------------------------
def call_gemini_vision(image_url: str, pokemon_id: int) -> tuple[Optional[dict], Optional[str]]:
    if USE_MOCK_AI:
        time.sleep(0.05)
        return generate_mock_annotation(pokemon_id), None

    try:
        with httpx.Client() as client:
            img_resp = client.get(image_url, timeout=10.0)
            img_resp.raise_for_status()
            image_bytes = img_resp.content
            content_type = img_resp.headers.get("content-type", "image/png")

        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content([
            {"mime_type": content_type, "data": image_bytes},
            VISION_PROMPT,
        ])

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(l for l in lines if not l.startswith("```"))

        parsed = json.loads(raw_text)
        return parsed, None

    except json.JSONDecodeError as e:
        return None, f"JSON 파싱 오류: {e}"
    except Exception as e:
        return None, f"API 오류: {e}"


# ---------------------------------------------------------------------------
# 값 검증 및 정규화
# ---------------------------------------------------------------------------
def clamp(value, lo=0.0, hi=1.0) -> float:
    return round(max(lo, min(hi, float(value))), 3)


def validate(raw: dict) -> dict:
    for f in SCORE_FIELDS:
        raw[f] = clamp(raw.get(f, 0.5))
    raw["has_glasses"] = bool(raw.get("has_glasses", False))
    return raw


# ---------------------------------------------------------------------------
# DB 저장
# ---------------------------------------------------------------------------
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def save_visual(cursor, pokemon_id: int, data: dict):
    source = "mock" if USE_MOCK_AI else "gemini_vision"
    confidence = 0.60 if USE_MOCK_AI else 0.85

    cursor.execute("""
        INSERT INTO pokemon_visual (
            pokemon_id,
            eye_size_score, eye_distance_score, eye_roundness_score, eye_tail_score,
            face_roundness_score, face_proportion_score,
            feature_size_score, feature_emphasis_score,
            mouth_curve_score, overall_symmetry,
            has_glasses,
            extraction_source, confidence, reviewed
        ) VALUES (
            %(pokemon_id)s,
            %(eye_size_score)s, %(eye_distance_score)s,
            %(eye_roundness_score)s, %(eye_tail_score)s,
            %(face_roundness_score)s, %(face_proportion_score)s,
            %(feature_size_score)s, %(feature_emphasis_score)s,
            %(mouth_curve_score)s, %(overall_symmetry)s,
            %(has_glasses)s,
            %(source)s, %(confidence)s, FALSE
        )
        ON CONFLICT (pokemon_id) DO UPDATE SET
            eye_size_score         = EXCLUDED.eye_size_score,
            eye_distance_score     = EXCLUDED.eye_distance_score,
            eye_roundness_score    = EXCLUDED.eye_roundness_score,
            eye_tail_score         = EXCLUDED.eye_tail_score,
            face_roundness_score   = EXCLUDED.face_roundness_score,
            face_proportion_score  = EXCLUDED.face_proportion_score,
            feature_size_score     = EXCLUDED.feature_size_score,
            feature_emphasis_score = EXCLUDED.feature_emphasis_score,
            mouth_curve_score      = EXCLUDED.mouth_curve_score,
            overall_symmetry       = EXCLUDED.overall_symmetry,
            has_glasses            = EXCLUDED.has_glasses,
            extraction_source      = EXCLUDED.extraction_source,
            reviewed               = FALSE,
            annotated_at           = now();
    """, {**data, "pokemon_id": pokemon_id, "source": source, "confidence": confidence})


# ---------------------------------------------------------------------------
# 메인 실행
# ---------------------------------------------------------------------------
def run(start: int, end: int, retry_failed: bool = False):
    mode = "[MOCK 모드]" if USE_MOCK_AI else "[실제 API 모드]"
    log.info(f"===== Step 2: Gemini Vision 시각 특징 주석 {mode}: #{start}~#{end} =====")

    if not USE_MOCK_AI:
        if not GEMINI_API_KEY:
            raise EnvironmentError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=GEMINI_API_KEY)

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if retry_failed:
        cursor.execute("""
            SELECT pokemon_id, name_kr, sprite_url
            FROM pokemon_master
            WHERE pokemon_id BETWEEN %s AND %s
              AND pokemon_id NOT IN (SELECT pokemon_id FROM pokemon_visual)
            ORDER BY pokemon_id;
        """, (start, end))
    else:
        cursor.execute("""
            SELECT pokemon_id, name_kr, sprite_url
            FROM pokemon_master
            WHERE pokemon_id BETWEEN %s AND %s
            ORDER BY pokemon_id;
        """, (start, end))

    targets = cursor.fetchall()
    log.info(f"처리 대상: {len(targets)}마리")

    success_count, fail_count, fail_ids = 0, 0, []
    pending_commits = 0

    for idx, row in enumerate(targets, 1):
        pokemon_id = row["pokemon_id"]
        name_kr    = row["name_kr"]
        sprite_url = row["sprite_url"]

        log.info(f"[{idx}/{len(targets)}] #{pokemon_id:03d} {name_kr}")

        if not sprite_url:
            log.warning(f"  sprite_url 없음 - 건너뜀")
            fail_count += 1
            fail_ids.append(pokemon_id)
            continue

        annotation, error_msg = call_gemini_vision(sprite_url, pokemon_id)

        if annotation is None:
            log.error(f"  분석 실패: {error_msg}")
            fail_count += 1
            fail_ids.append(pokemon_id)
        else:
            annotation = validate(annotation)
            cursor.execute("SAVEPOINT sp_visual_row")
            try:
                save_visual(cursor, pokemon_id, annotation)
                cursor.execute("RELEASE SAVEPOINT sp_visual_row")
                pending_commits += 1
                if pending_commits >= COMMIT_BATCH_SIZE:
                    conn.commit()
                    pending_commits = 0
                log.info(
                    f"  저장 완료: eye_size={annotation['eye_size_score']} "
                    f"face_round={annotation['face_roundness_score']} "
                    f"mouth={annotation['mouth_curve_score']}"
                )
                success_count += 1
            except Exception as e:
                cursor.execute("ROLLBACK TO SAVEPOINT sp_visual_row")
                cursor.execute("RELEASE SAVEPOINT sp_visual_row")
                log.error(f"  DB 저장 오류: {e}")
                fail_count += 1
                fail_ids.append(pokemon_id)

        if idx % BATCH_SIZE == 0:
            log.info(f"  --- 배치 체크포인트: {idx}/{len(targets)} ---")

        if not USE_MOCK_AI:
            time.sleep(REQUEST_DELAY)

    if pending_commits > 0:
        conn.commit()

    cursor.close()
    conn.close()

    log.info("=" * 50)
    log.info(f"완료 | 성공: {success_count} | 실패: {fail_count}")
    if fail_ids:
        log.warning(f"실패 목록: {fail_ids}")
        log.warning("재실행: python 02_annotate_gemini_vision.py --retry-failed")
    log.info("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini Vision 시각 특징 주석 스크립트 (v5)")
    parser.add_argument("--start",        type=int, default=1,   help="시작 번호 (기본: 1)")
    parser.add_argument("--end",          type=int, default=386, help="끝 번호   (기본: 386)")
    parser.add_argument("--retry-failed", action="store_true",   help="누락된 항목만 재실행")
    args = parser.parse_args()
    run(start=args.start, end=args.end, retry_failed=args.retry_failed)
