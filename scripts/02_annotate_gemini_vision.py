"""
Step 2. Gemini Vision 시각 특징 주석 배치 스크립트
대상: pokemon_master 에 저장된 1세대 포켓몬 스프라이트
저장: pokemon_face_shape / pokemon_eye_features /
       pokemon_nose_mouth_features / pokemon_style_features /
       pokemon_emotion_features / pokemon_annotation_log

실행 방법:
    python scripts/02_annotate_gemini_vision.py
    python scripts/02_annotate_gemini_vision.py --start 1 --end 30
    python scripts/02_annotate_gemini_vision.py --retry-failed   # 실패 건만 재실행
    USE_MOCK_AI=true python scripts/02_annotate_gemini_vision.py # Mock 모드 (비용 없음)
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

# ---------------------------------------------------------------------------
# 환경 설정
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

USE_MOCK_AI     = os.environ.get("USE_MOCK_AI", "false").lower() == "true"
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL    = "gemini-1.5-flash-002"
REQUEST_DELAY   = 1.5           # Gemini API 호출 간 딜레이 (초)
BATCH_SIZE      = 10            # 오류 격리 배치 단위

EMOTION_CLASSES     = ["기쁨", "무표정", "분노", "신비", "온화", "슬픔", "공포"]
PERSONALITY_POOL    = [
    "용감한", "온화한", "조심스러운", "명랑한", "냉정한", "건방진",
    "고집스러운", "느긋한", "개구쟁이", "뻔뻔한", "호기심많은",
    "외로움을타는", "수줍은", "사나운", "신중한", "충성스러운",
]


# ---------------------------------------------------------------------------
# Gemini Vision 프롬프트
# ---------------------------------------------------------------------------
VISION_PROMPT = """
당신은 포켓몬 스프라이트 이미지를 분석하는 전문가입니다.
아래 이미지의 포켓몬 얼굴/두부 특징을 분석하여 반드시 JSON만 출력하세요.
설명, 마크다운 코드블록, 추가 텍스트 없이 JSON 객체만 출력합니다.

[분석 기준]
- face_aspect_ratio: 두부 가로÷세로 (0.0=매우세로형, 1.0=매우가로형/둥글)
- jawline_angle: 하턱/주둥이 끝 형태 (0.0=뾰족V, 1.0=둥근U)
- eye_size_ratio: 눈 크기÷얼굴 크기 (0.0=없음, 1.0=매우큰눈)
- eye_distance_ratio: 양눈 간격÷얼굴가로 (0.0=붙음, 1.0=매우넓음)
- eye_slant_angle: 눈꼬리 방향 (0.0=처짐/온화, 0.5=수평, 1.0=올라감/공격적)
- eye_note: 특수케이스 - "no_eyes"/"compound_eyes"/"full_body_eye"/null
- nose_length_ratio: 코/주둥이 돌출 길이 (0.0=없음, 1.0=매우긺)
- nose_width_ratio: 코볼 너비 (0.0=없음, 1.0=매우넓음)
- mouth_width_ratio: 입/부리 너비÷얼굴가로 (0.0=작음, 1.0=매우큼)
- lip_thickness_ratio: 입술 두께감 (0.0=선형/얇음, 1.0=매우두꺼움)
- smile_score: 웃음 표정 (0.0=찌푸림, 0.5=무표정, 1.0=환한미소)
- has_glasses: 안경/안경형 디자인 (true/false)
- has_facial_hair: 수염/갈기/콧수염 유사 요소 (true/false)
- has_bangs: 두부 전면 덮는 털/잎/갈기 (true/false)
- glasses_note: has_glasses=true일 때 근거 (null 가능)
- facial_hair_note: has_facial_hair=true일 때 근거 (null 가능)
- bangs_note: has_bangs=true일 때 근거 (null 가능)
- emotion_class: 기쁨/무표정/분노/신비/온화/슬픔/공포 중 1개
- personality_class: [용감한/온화한/조심스러운/명랑한/냉정한/건방진/고집스러운/느긋한/개구쟁이/뻔뻔한/호기심많은/외로움을타는/수줍은/사나운/신중한/충성스러운] 에서 최대 4개 쉼표구분

[예외 처리 규칙]
- 눈 없는 포켓몬: eye_size_ratio=0.0, eye_note="no_eyes"
- 코 없는 포켓몬: nose_length_ratio=0.10, nose_width_ratio=0.10
- 비인간형 포켓몬: philtrum 구조 없으므로 해당 항목 없음 (스키마에서 별도 처리)

출력 형식 (이것만 출력):
{
  "face_aspect_ratio": 0.00,
  "jawline_angle": 0.00,
  "eye_size_ratio": 0.00,
  "eye_distance_ratio": 0.00,
  "eye_slant_angle": 0.50,
  "eye_note": null,
  "nose_length_ratio": 0.00,
  "nose_width_ratio": 0.00,
  "mouth_width_ratio": 0.00,
  "lip_thickness_ratio": 0.00,
  "smile_score": 0.50,
  "has_glasses": false,
  "has_facial_hair": false,
  "has_bangs": false,
  "glasses_note": null,
  "facial_hair_note": null,
  "bangs_note": null,
  "emotion_class": "무표정",
  "personality_class": "온화한,조심스러운"
}
"""


# ---------------------------------------------------------------------------
# Mock 데이터 생성 (USE_MOCK_AI=true 시 사용)
# ---------------------------------------------------------------------------
def generate_mock_annotation(pokemon_id: int) -> dict:
    """
    개발 중 API 비용 절약을 위한 Mock 값 생성
    포켓몬 ID 기반 시드로 재현 가능한 랜덤값 반환
    """
    rng = random.Random(pokemon_id * 42)

    def r(lo=0.1, hi=0.9) -> float:
        return round(rng.uniform(lo, hi), 2)

    return {
        "face_aspect_ratio":  r(0.3, 1.0),
        "jawline_angle":      r(0.2, 1.0),
        "eye_size_ratio":     r(0.2, 0.9),
        "eye_distance_ratio": r(0.3, 0.8),
        "eye_slant_angle":    r(0.1, 0.9),
        "eye_note":           None,
        "nose_length_ratio":  r(0.1, 0.5),
        "nose_width_ratio":   r(0.1, 0.4),
        "mouth_width_ratio":  r(0.2, 0.8),
        "lip_thickness_ratio": r(0.1, 0.5),
        "smile_score":        r(0.1, 0.9),
        "has_glasses":        rng.random() < 0.05,
        "has_facial_hair":    rng.random() < 0.15,
        "has_bangs":          rng.random() < 0.20,
        "glasses_note":       None,
        "facial_hair_note":   None,
        "bangs_note":         None,
        "emotion_class":      rng.choice(EMOTION_CLASSES),
        "personality_class":  ",".join(rng.sample(PERSONALITY_POOL, k=rng.randint(2, 4))),
    }


# ---------------------------------------------------------------------------
# Gemini Vision 호출
# ---------------------------------------------------------------------------
def call_gemini_vision(image_url: str, pokemon_id: int) -> tuple[Optional[dict], Optional[str]]:
    """
    Returns: (parsed_dict, error_message)
    """
    if USE_MOCK_AI:
        time.sleep(0.05)  # 실제 API처럼 약간의 딜레이
        return generate_mock_annotation(pokemon_id), None

    try:
        # 스프라이트 이미지 다운로드
        with httpx.Client() as client:
            img_resp = client.get(image_url, timeout=10.0)
            img_resp.raise_for_status()
            image_bytes = img_resp.content
            content_type = img_resp.headers.get("content-type", "image/png")

        # Gemini Vision 호출
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content([
            {"mime_type": content_type, "data": image_bytes},
            VISION_PROMPT,
        ])

        raw_text = response.text.strip()

        # JSON 파싱
        # 코드블록이 포함된 경우 제거
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            )

        parsed = json.loads(raw_text)
        return parsed, None

    except json.JSONDecodeError as e:
        return None, f"JSON 파싱 오류: {e} | 원본: {raw_text[:200]}"
    except Exception as e:
        return None, f"API 오류: {e}"


# ---------------------------------------------------------------------------
# 값 검증 및 정규화
# ---------------------------------------------------------------------------
def clamp(value, lo=0.0, hi=1.0) -> float:
    return round(max(lo, min(hi, float(value))), 2)


def validate_and_normalize(raw: dict) -> dict:
    """
    float 범위 보정, emotion_class 허용값 검증, personality_class 4개 제한
    """
    float_fields = [
        "face_aspect_ratio", "jawline_angle", "eye_size_ratio",
        "eye_distance_ratio", "eye_slant_angle", "nose_length_ratio",
        "nose_width_ratio", "mouth_width_ratio", "lip_thickness_ratio",
        "smile_score",
    ]
    for f in float_fields:
        if f in raw:
            raw[f] = clamp(raw.get(f, 0.5))

    # emotion_class 허용값 검증
    if raw.get("emotion_class") not in EMOTION_CLASSES:
        log.warning(f"  잘못된 emotion_class: {raw.get('emotion_class')} → '무표정' 으로 대체")
        raw["emotion_class"] = "무표정"

    # personality_class 4개 제한
    personalities = [p.strip() for p in raw.get("personality_class", "").split(",") if p.strip()]
    valid = [p for p in personalities if p in PERSONALITY_POOL]
    if len(valid) > 4:
        valid = valid[:4]
    raw["personality_class"] = ",".join(valid) if valid else "온화한"

    return raw


# ---------------------------------------------------------------------------
# DB 저장
# ---------------------------------------------------------------------------
def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    return psycopg2.connect(url)


def save_annotation(cursor, pokemon_id: int, data: dict):
    # pokemon_face_shape
    cursor.execute("""
        INSERT INTO pokemon_face_shape
            (pokemon_id, face_aspect_ratio, jawline_angle, extraction_source, confidence, reviewed)
        VALUES (%s, %s, %s, %s, %s, FALSE)
        ON CONFLICT (pokemon_id) DO UPDATE SET
            face_aspect_ratio = EXCLUDED.face_aspect_ratio,
            jawline_angle     = EXCLUDED.jawline_angle,
            reviewed          = FALSE;
    """, (pokemon_id, data["face_aspect_ratio"], data["jawline_angle"],
          "mock" if USE_MOCK_AI else "gemini_vision", 0.85 if not USE_MOCK_AI else 0.60))

    # pokemon_eye_features
    cursor.execute("""
        INSERT INTO pokemon_eye_features
            (pokemon_id, eye_size_ratio, eye_distance_ratio, eye_slant_angle,
             eye_note, extraction_source, confidence, reviewed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE)
        ON CONFLICT (pokemon_id) DO UPDATE SET
            eye_size_ratio     = EXCLUDED.eye_size_ratio,
            eye_distance_ratio = EXCLUDED.eye_distance_ratio,
            eye_slant_angle    = EXCLUDED.eye_slant_angle,
            eye_note           = EXCLUDED.eye_note,
            reviewed           = FALSE;
    """, (pokemon_id, data["eye_size_ratio"], data["eye_distance_ratio"],
          data["eye_slant_angle"], data.get("eye_note"),
          "mock" if USE_MOCK_AI else "gemini_vision", 0.85 if not USE_MOCK_AI else 0.60))

    # pokemon_nose_mouth_features
    cursor.execute("""
        INSERT INTO pokemon_nose_mouth_features
            (pokemon_id, nose_length_ratio, nose_width_ratio, mouth_width_ratio,
             lip_thickness_ratio, philtrum_ratio, is_humanoid, mouth_note,
             extraction_source, confidence, reviewed)
        VALUES (%s, %s, %s, %s, %s, 0.10, FALSE, %s, %s, %s, FALSE)
        ON CONFLICT (pokemon_id) DO UPDATE SET
            nose_length_ratio  = EXCLUDED.nose_length_ratio,
            nose_width_ratio   = EXCLUDED.nose_width_ratio,
            mouth_width_ratio  = EXCLUDED.mouth_width_ratio,
            lip_thickness_ratio= EXCLUDED.lip_thickness_ratio,
            reviewed           = FALSE;
    """, (pokemon_id, data["nose_length_ratio"], data["nose_width_ratio"],
          data["mouth_width_ratio"], data["lip_thickness_ratio"],
          data.get("mouth_note"),
          "mock" if USE_MOCK_AI else "gemini_vision", 0.80 if not USE_MOCK_AI else 0.60))

    # pokemon_style_features
    cursor.execute("""
        INSERT INTO pokemon_style_features
            (pokemon_id, has_glasses, has_facial_hair, has_bangs,
             glasses_note, facial_hair_note, bangs_note, extraction_source, reviewed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)
        ON CONFLICT (pokemon_id) DO UPDATE SET
            has_glasses     = EXCLUDED.has_glasses,
            has_facial_hair = EXCLUDED.has_facial_hair,
            has_bangs       = EXCLUDED.has_bangs,
            reviewed        = FALSE;
    """, (pokemon_id, data["has_glasses"], data["has_facial_hair"], data["has_bangs"],
          data.get("glasses_note"), data.get("facial_hair_note"), data.get("bangs_note"),
          "mock" if USE_MOCK_AI else "gemini_vision"))

    # pokemon_emotion_features
    cursor.execute("""
        INSERT INTO pokemon_emotion_features
            (pokemon_id, smile_score, emotion_class, personality_class,
             extraction_source, reviewed)
        VALUES (%s, %s, %s, %s, %s, FALSE)
        ON CONFLICT (pokemon_id) DO UPDATE SET
            smile_score       = EXCLUDED.smile_score,
            emotion_class     = EXCLUDED.emotion_class,
            personality_class = EXCLUDED.personality_class,
            reviewed          = FALSE;
    """, (pokemon_id, data["smile_score"], data["emotion_class"], data["personality_class"],
          "mock" if USE_MOCK_AI else "gemini_flash_text"))


def log_annotation(cursor, pokemon_id: int, status: str,
                   raw_response: Optional[dict], error_msg: Optional[str]):
    cursor.execute("""
        INSERT INTO pokemon_annotation_log
            (pokemon_id, batch_type, status, raw_response, error_message, model_version)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (
        pokemon_id,
        "gemini_vision",
        status,
        json.dumps(raw_response, ensure_ascii=False) if raw_response else None,
        error_msg,
        "mock" if USE_MOCK_AI else GEMINI_MODEL,
    ))


# ---------------------------------------------------------------------------
# 메인 실행
# ---------------------------------------------------------------------------
def run(start: int, end: int, retry_failed: bool = False):
    mode = "[MOCK 모드]" if USE_MOCK_AI else "[실제 API 모드]"
    log.info(f"===== Gemini Vision 배치 주석 시작 {mode}: #{start} ~ #{end} =====")

    if not USE_MOCK_AI:
        if not GEMINI_API_KEY:
            raise EnvironmentError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        genai.configure(api_key=GEMINI_API_KEY)

    conn   = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 처리 대상 포켓몬 목록 조회
    if retry_failed:
        cursor.execute("""
            SELECT m.pokemon_id, m.name_kr, m.sprite_url
            FROM pokemon_master m
            JOIN pokemon_annotation_log l ON m.pokemon_id = l.pokemon_id
            WHERE l.status = 'failed'
              AND m.pokemon_id BETWEEN %s AND %s
            GROUP BY m.pokemon_id, m.name_kr, m.sprite_url
            ORDER BY m.pokemon_id;
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

    success_count = 0
    fail_count    = 0
    fail_ids      = []

    for idx, row in enumerate(targets, 1):
        pokemon_id  = row["pokemon_id"]
        name_kr     = row["name_kr"]
        sprite_url  = row["sprite_url"]

        log.info(f"[{idx}/{len(targets)}] #{pokemon_id:03d} {name_kr} 분석 중...")

        if not sprite_url:
            log.warning(f"  sprite_url 없음 - 건너뜀")
            log_annotation(cursor, pokemon_id, "failed", None, "sprite_url 없음")
            conn.commit()
            fail_count += 1
            fail_ids.append(pokemon_id)
            continue

        # Gemini Vision 호출
        annotation, error_msg = call_gemini_vision(sprite_url, pokemon_id)

        if annotation is None:
            log.error(f"  분석 실패: {error_msg}")
            log_annotation(cursor, pokemon_id, "failed", None, error_msg)
            conn.commit()
            fail_count += 1
            fail_ids.append(pokemon_id)
        else:
            # 검증 및 정규화
            annotation = validate_and_normalize(annotation)

            try:
                save_annotation(cursor, pokemon_id, annotation)
                log_annotation(cursor, pokemon_id, "success", annotation, None)
                conn.commit()
                log.info(
                    f"  저장 완료: emotion={annotation['emotion_class']} "
                    f"| smile={annotation['smile_score']} "
                    f"| eye_slant={annotation['eye_slant_angle']}"
                )
                success_count += 1
            except Exception as e:
                conn.rollback()
                log.error(f"  DB 저장 오류: {e}")
                log_annotation(cursor, pokemon_id, "failed", annotation, str(e))
                conn.commit()
                fail_count += 1
                fail_ids.append(pokemon_id)

        # 배치 단위 로그
        if idx % BATCH_SIZE == 0:
            log.info(f"  --- 배치 체크포인트: {idx}/{len(targets)} 완료 ---")

        time.sleep(REQUEST_DELAY)

    cursor.close()
    conn.close()

    log.info("=" * 50)
    log.info(f"주석 완료 | 성공: {success_count} | 실패: {fail_count}")
    if fail_ids:
        log.warning(f"실패 목록: {fail_ids}")
        log.warning("재실행: python 02_annotate_gemini_vision.py --retry-failed")
    log.info("=" * 50)


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini Vision 배치 주석 스크립트")
    parser.add_argument("--start",        type=int, default=1,     help="시작 번호 (기본: 1)")
    parser.add_argument("--end",          type=int, default=151,   help="끝 번호   (기본: 151)")
    parser.add_argument("--retry-failed", action="store_true",     help="실패한 항목만 재실행")
    args = parser.parse_args()

    run(start=args.start, end=args.end, retry_failed=args.retry_failed)
