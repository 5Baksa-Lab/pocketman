"""
Step 3. 인상/성격 점수 계산 스크립트
기획안 v5 §6-4 "Category 2: 인상/성격 점수 (Impression Scores)" 기준

입력:
  - pokemon_master.pokedex_text_kr + 타입 정보 (Gemini Flash 분석)
  - pokemon_visual (fallback 규칙식)
출력: pokemon_impression (9차원 스코어)

동작 우선순위:
  1) Gemini Flash로 9개 인상 점수 추출
  2) 실패 시 visual 기반 규칙식으로 fallback

실행 방법:
    python scripts/03_calc_impression.py
    python scripts/03_calc_impression.py --start 1 --end 386
"""

import os
import json
import time
import random
import logging
import argparse
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from shared.feature_mapping import calc_impression_from_visual, impression_to_db_scores

try:
    import google.generativeai as genai
except ModuleNotFoundError:  # pragma: no cover - optional during local setup
    genai = None  # type: ignore

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

USE_MOCK_AI = os.environ.get("USE_MOCK_AI", "false").lower() == "true"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
REQUEST_DELAY = 0.8
COMMIT_BATCH_SIZE = 50

IMPRESSION_FIELDS = [
    "cute", "calm", "smart", "fierce", "gentle",
    "lively", "innocent", "confident", "unique",
]


# ---------------------------------------------------------------------------
# Gemini Flash helpers
# ---------------------------------------------------------------------------
def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return round(max(lo, min(hi, float(v))), 3)


def parse_json_object(raw: str) -> Optional[dict]:
    text = (raw or "").strip()
    if not text:
        return None

    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(line for line in lines if not line.strip().startswith("```"))
        text = text.strip()

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def normalize_impression_scores(raw: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in IMPRESSION_FIELDS:
        out[key] = clamp(raw.get(key, 0.5))
    return out


def build_prompt(row: dict) -> str:
    name_kr = row.get("name_kr", "")
    name_en = row.get("name_en", "")
    primary_type = row.get("primary_type", "")
    secondary_type = row.get("secondary_type") or "없음"
    pokedex_text = row.get("pokedex_text_kr") or "도감 설명 없음"

    return f"""
당신은 포켓몬 도감 텍스트와 타입을 기반으로 인상/성격 점수를 수치화하는 분석가입니다.
설명 없이 JSON 객체만 출력하세요.

포켓몬:
- name_kr: {name_kr}
- name_en: {name_en}
- primary_type: {primary_type}
- secondary_type: {secondary_type}
- pokedex_text: {pokedex_text}

다음 9개 키를 0.0~1.0 점수로 반환:
- cute
- calm
- smart
- fierce
- gentle
- lively
- innocent
- confident
- unique

출력 형식:
{{
  "cute": 0.50,
  "calm": 0.50,
  "smart": 0.50,
  "fierce": 0.50,
  "gentle": 0.50,
  "lively": 0.50,
  "innocent": 0.50,
  "confident": 0.50,
  "unique": 0.50
}}
""".strip()


def generate_mock_impression(pokemon_id: int) -> dict[str, float]:
    rng = random.Random(pokemon_id * 173)
    return {key: clamp(rng.uniform(0.15, 0.9)) for key in IMPRESSION_FIELDS}


def init_gemini_model():
    if USE_MOCK_AI:
        log.info("Gemini Flash Mock 모드 사용 (USE_MOCK_AI=true)")
        return None

    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY 미설정: 규칙 기반 fallback만 사용합니다.")
        return None

    if genai is None:
        log.warning("google-generativeai 모듈 없음: 규칙 기반 fallback만 사용합니다.")
        return None

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel(GEMINI_MODEL)
    except Exception as e:
        log.warning(f"Gemini 모델 초기화 실패: {e} | fallback만 사용합니다.")
        return None


def call_gemini_impression(model, row: dict) -> tuple[Optional[dict[str, float]], Optional[str]]:
    if USE_MOCK_AI:
        return generate_mock_impression(int(row["pokemon_id"])), None

    if model is None:
        return None, "gemini_model_unavailable"

    try:
        response = model.generate_content(build_prompt(row))
        parsed = parse_json_object(getattr(response, "text", ""))
        if parsed is None:
            return None, "gemini_json_parse_failed"
        return normalize_impression_scores(parsed), None
    except Exception as e:
        return None, f"gemini_error: {e}"


# ---------------------------------------------------------------------------
# DB 처리
# ---------------------------------------------------------------------------
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def run(start: int, end: int):
    log.info(f"===== Step 3: 인상 점수 계산 시작: #{start}~#{end} =====")
    model = init_gemini_model()

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute(
        """
        SELECT
            m.pokemon_id, m.name_kr, m.name_en,
            m.primary_type, m.secondary_type, m.pokedex_text_kr,
            v.eye_size_score, v.eye_distance_score, v.eye_roundness_score,
            v.eye_tail_score, v.face_roundness_score, v.face_proportion_score,
            v.feature_size_score, v.feature_emphasis_score,
            v.mouth_curve_score, v.overall_symmetry, v.has_glasses
        FROM pokemon_master m
        JOIN pokemon_visual v ON m.pokemon_id = v.pokemon_id
        WHERE m.pokemon_id BETWEEN %s AND %s
        ORDER BY m.pokemon_id;
    """,
        (start, end),
    )

    rows = cursor.fetchall()
    log.info(f"처리 대상: {len(rows)}마리")

    if len(rows) == 0:
        log.warning("처리할 데이터가 없습니다. Step 2를 먼저 실행하세요.")

    success = 0
    pending_commits = 0
    failed = 0
    gemini_count = 0
    mock_count = 0
    fallback_count = 0

    for row in rows:
        pokemon_id = row["pokemon_id"]
        cursor.execute("SAVEPOINT sp_impression_row")

        try:
            fallback_impression = calc_impression_from_visual(row)
            gemini_impression, gemini_error = call_gemini_impression(model, row)

            source_label = "fallback"
            derivation_note = "fallback_auto_from_visual_v5"
            if gemini_impression is not None:
                impression = gemini_impression
                if USE_MOCK_AI:
                    source_label = "mock_gemini"
                    derivation_note = "mock_gemini_flash_v5"
                    mock_count += 1
                else:
                    source_label = "gemini_flash"
                    derivation_note = "gemini_flash_from_text_v5"
                    gemini_count += 1
            else:
                impression = fallback_impression
                fallback_count += 1
                if gemini_error:
                    log.warning(f"  #{pokemon_id:03d} Gemini 실패 → fallback: {gemini_error}")

            scores = impression_to_db_scores(impression)
            cursor.execute(
                """
                INSERT INTO pokemon_impression (
                    pokemon_id,
                    cute_score, calm_score, smart_score, fierce_score, gentle_score,
                    lively_score, innocent_score, confident_score, unique_score,
                    derivation_note
                ) VALUES (
                    %(pokemon_id)s,
                    %(cute_score)s, %(calm_score)s, %(smart_score)s,
                    %(fierce_score)s, %(gentle_score)s,
                    %(lively_score)s, %(innocent_score)s,
                    %(confident_score)s, %(unique_score)s,
                    %(derivation_note)s
                )
                ON CONFLICT (pokemon_id) DO UPDATE SET
                    cute_score = EXCLUDED.cute_score,
                    calm_score = EXCLUDED.calm_score,
                    smart_score = EXCLUDED.smart_score,
                    fierce_score = EXCLUDED.fierce_score,
                    gentle_score = EXCLUDED.gentle_score,
                    lively_score = EXCLUDED.lively_score,
                    innocent_score = EXCLUDED.innocent_score,
                    confident_score = EXCLUDED.confident_score,
                    unique_score = EXCLUDED.unique_score,
                    derivation_note = EXCLUDED.derivation_note;
            """,
                {
                    "pokemon_id": pokemon_id,
                    "derivation_note": derivation_note,
                    **scores,
                },
            )
            cursor.execute("RELEASE SAVEPOINT sp_impression_row")
            pending_commits += 1
            if pending_commits >= COMMIT_BATCH_SIZE:
                conn.commit()
                pending_commits = 0
        except Exception as e:
            cursor.execute("ROLLBACK TO SAVEPOINT sp_impression_row")
            cursor.execute("RELEASE SAVEPOINT sp_impression_row")
            log.error(f"  DB 저장 오류 #{pokemon_id}: {e}")
            failed += 1
            continue

        log.info(
            f"  #{pokemon_id:03d} {row['name_kr']} | "
            f"cute={scores['cute_score']} calm={scores['calm_score']} "
            f"fierce={scores['fierce_score']} unique={scores['unique_score']} "
            f"source={source_label}"
        )
        success += 1

        if not USE_MOCK_AI and model is not None:
            time.sleep(REQUEST_DELAY)

    if pending_commits > 0:
        conn.commit()

    cursor.close()
    conn.close()
    log.info(
        "===== Step 3: 인상 점수 계산 완료: "
        f"성공 {success}마리 | 실패 {failed}마리 | "
        f"gemini={gemini_count} mock={mock_count} fallback={fallback_count} ====="
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="인상 점수 계산 스크립트 (Gemini Flash + fallback, v5)")
    parser.add_argument("--start", type=int, default=1, help="시작 번호")
    parser.add_argument("--end", type=int, default=386, help="끝 번호")
    args = parser.parse_args()
    run(start=args.start, end=args.end)
