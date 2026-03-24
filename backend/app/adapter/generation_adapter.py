"""Generation adapters — google-genai SDK 통합 (Gemini Flash / Imagen 3 / Veo).

USE_MOCK_AI=true  → deterministic mock 결과 반환
USE_MOCK_AI=false → 실제 Google AI API 호출 + 재시도 + fallback
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from app.core.config import (
    AI_MAX_RETRIES,
    AI_REQUEST_TIMEOUT_SEC,
    AI_RETRY_BASE_DELAY_SEC,
    API_BASE_URL,
    GEMINI_API_KEY,
    GEMINI_FLASH_MODEL,
    GENERATED_FILES_DIR,
    IMAGEN_MODEL,
    USE_MOCK_AI,
    VEO_MODEL,
)

_log = logging.getLogger(__name__)

# ── google-genai SDK lazy init ──────────────────────────────────────
_genai_client = None


def _get_genai_client():
    """google-genai Client 싱글턴. API 키 미설정 시 None 반환."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    if not GEMINI_API_KEY:
        _log.warning("GEMINI_API_KEY 미설정 — AI 기능이 fallback 모드로 동작합니다.")
        return None

    try:
        from google import genai

        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
        _log.info("google-genai Client 초기화 완료")
        return _genai_client
    except Exception as e:
        _log.error("google-genai Client 초기화 실패: %s", e)
        return None


# ── Data classes ────────────────────────────────────────────────────


@dataclass
class StepMeta:
    source: str
    used_fallback: bool
    retries: int
    message: str | None = None


@dataclass
class StoryNameResult:
    name: str
    story: str
    meta: StepMeta


@dataclass
class ImageResult:
    image_url: str
    meta: StepMeta


@dataclass
class VideoResult:
    status: str
    video_url: str | None
    error_message: str | None
    meta: StepMeta


# ── Retry helper ────────────────────────────────────────────────────


def _retry_call(fn, op_name: str):
    attempts = max(1, AI_MAX_RETRIES + 1)
    last_error: Exception | None = None

    for idx in range(attempts):
        try:
            value = fn()
            return value, idx
        except Exception as e:
            last_error = e
            _log.warning("%s 시도 %d 실패: %s", op_name, idx + 1, e)
            if idx < attempts - 1:
                delay = AI_RETRY_BASE_DELAY_SEC * (2**idx)
                time.sleep(delay)

    if last_error is None:
        raise RuntimeError(f"{op_name} 실패 (원인 미상)")
    raise RuntimeError(f"{op_name} 실패: {last_error}")


# ── JSON parser ─────────────────────────────────────────────────────


def _parse_json_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None

    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(line for line in lines if not line.strip().startswith("```"))
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidate = raw[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# ── Fallback helpers ────────────────────────────────────────────────


def _fallback_name(context: dict[str, Any]) -> str:
    pokemon_name = context.get("matched_pokemon_name_kr") or "포켓몬"
    return f"{pokemon_name} 타입 크리처"


def _fallback_story(context: dict[str, Any]) -> str:
    pokemon_name = context.get("matched_pokemon_name_kr") or "포켓몬"
    p_type = context.get("primary_type") or "노말"
    return (
        f"이 크리처는 {pokemon_name}의 분위기와 {p_type} 타입의 성향을 이어받아 탄생했습니다. "
        "차분한 외형 속에서도 자신만의 강점을 드러내며, 사용자와 함께 성장하는 동반자입니다."
    )


def _fallback_image_url(context: dict[str, Any]) -> str:
    label = context.get("matched_pokemon_name_kr") or "Creature"
    return f"https://placehold.co/1024x1024/png?text={quote(str(label))}"


def _mock_video_url(context: dict[str, Any]) -> str:
    creature_id = context.get("id") or "mock"
    return f"https://cdn.pocketman.mock/videos/{creature_id}.mp4"


# ── 이미지 파일 저장 ───────────────────────────────────────────────


def _ensure_generated_dir() -> str:
    os.makedirs(GENERATED_FILES_DIR, exist_ok=True)
    return GENERATED_FILES_DIR


def _save_image_bytes(image_bytes: bytes, ext: str = "png") -> str:
    """이미지 바이트를 로컬 파일로 저장하고 접근 가능한 URL을 반환한다."""
    dir_path = _ensure_generated_dir()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(dir_path, filename)

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    _log.info("생성 이미지 저장: %s (%d bytes)", filepath, len(image_bytes))
    return f"{API_BASE_URL.rstrip('/')}/static/generated/{filename}"


# ── Prompts ─────────────────────────────────────────────────────────


def _build_story_prompt(context: dict[str, Any]) -> str:
    reasons = context.get("match_reasons") or []
    reasons_text = ", ".join(str(r.get("label", "")) for r in reasons[:3]) or "없음"
    return f"""
당신은 게임 캐릭터 디자이너입니다.
아래 정보를 기반으로 한국어 크리처 이름(name)과 짧은 소개 스토리(story)를 생성하세요.
설명 없이 JSON 객체만 출력하세요.

입력:
- matched_pokemon_name_kr: {context.get('matched_pokemon_name_kr')}
- matched_pokemon_name_en: {context.get('matched_pokemon_name_en')}
- primary_type: {context.get('primary_type')}
- secondary_type: {context.get('secondary_type') or '없음'}
- similarity_score: {context.get('similarity_score')}
- match_reasons: {reasons_text}

조건:
- name: 2~12자
- story: 2~4문장, 포켓몬 세계관 톤
- 선정적/폭력적 표현 금지

출력 형식:
{{
  "name": "샘플이름",
  "story": "샘플 스토리"
}}
""".strip()


def _build_imagen_prompt(context: dict[str, Any], name: str, story: str) -> str:
    pokemon_name = context.get("matched_pokemon_name_en") or "Pokemon"
    p_type = context.get("primary_type") or "normal"
    s_type = context.get("secondary_type") or ""
    type_desc = f"{p_type}/{s_type}" if s_type else p_type

    return (
        f"A cute, unique creature character inspired by {pokemon_name}. "
        f"Name: {name}. Type: {type_desc}. "
        f"Description: {story[:200]} "
        "Style: Pokemon-inspired creature design, digital art, vibrant colors, "
        "white background, full body portrait, high quality, detailed."
    )


def _build_veo_prompt(context: dict[str, Any], name: str, story: str) -> str:
    return (
        f"A short introduction animation of a cute creature named {name}. "
        f"{story[:200]} "
        "Style: animated, Pokemon-inspired, cute, dynamic movement, "
        "colorful background, looping animation."
    )


# ═══════════════════════════════════════════════════════════════════
#  1. Gemini Flash — 이름 / 스토리 생성
# ═══════════════════════════════════════════════════════════════════


def generate_name_story(context: dict[str, Any]) -> StoryNameResult:
    # ── Mock 모드 ──
    if USE_MOCK_AI:
        seed = int(str(context.get("matched_pokemon_id", 0))) * 97
        rng = random.Random(seed)
        pokemon_name = context.get("matched_pokemon_name_kr") or "크리처"
        suffix = ["링", "온", "라", "모", "트"]
        name = f"{pokemon_name[:2]}{rng.choice(suffix)}"
        story = (
            f"{name}는 {pokemon_name}의 인상을 닮아 탄생한 크리처입니다. "
            "밝은 눈빛과 안정적인 기운으로 주변을 지켜주며, 위기에서 빠르게 반응합니다."
        )
        return StoryNameResult(
            name=name,
            story=story,
            meta=StepMeta(source="mock_gemini_flash", used_fallback=False, retries=0),
        )

    # ── 실제 API ──
    client = _get_genai_client()
    if client is None:
        return StoryNameResult(
            name=_fallback_name(context),
            story=_fallback_story(context),
            meta=StepMeta(
                source="fallback_rule",
                used_fallback=True,
                retries=0,
                message="Gemini 설정 미완료로 fallback 사용",
            ),
        )

    def _call_real():
        resp = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=_build_story_prompt(context),
        )
        parsed = _parse_json_object(resp.text or "")
        if parsed is None:
            raise RuntimeError("Gemini 응답 JSON 파싱 실패")

        name = str(parsed.get("name", "")).strip()
        story = str(parsed.get("story", "")).strip()
        if not name or not story:
            raise RuntimeError("name/story 필드 누락")
        return name, story

    try:
        (name, story), retries = _retry_call(_call_real, "Gemini Flash 스토리 생성")
        return StoryNameResult(
            name=name,
            story=story,
            meta=StepMeta(source="gemini_flash", used_fallback=False, retries=retries),
        )
    except Exception as e:
        _log.error("Gemini Flash 최종 실패, fallback 사용: %s", e)
        return StoryNameResult(
            name=_fallback_name(context),
            story=_fallback_story(context),
            meta=StepMeta(
                source="fallback_rule",
                used_fallback=True,
                retries=AI_MAX_RETRIES,
                message=str(e),
            ),
        )


# ═══════════════════════════════════════════════════════════════════
#  2. Imagen 3 — 크리처 이미지 생성
# ═══════════════════════════════════════════════════════════════════


def generate_image(
    context: dict[str, Any], generated_name: str, generated_story: str
) -> ImageResult:
    # ── Mock 모드 ──
    if USE_MOCK_AI:
        return ImageResult(
            image_url=_fallback_image_url(context),
            meta=StepMeta(source="mock_imagen", used_fallback=False, retries=0),
        )

    # ── 실제 API ──
    client = _get_genai_client()
    if client is None:
        return ImageResult(
            image_url=_fallback_image_url(context),
            meta=StepMeta(
                source="fallback_placeholder",
                used_fallback=True,
                retries=0,
                message="Gemini API 키 미설정으로 이미지 생성 불가",
            ),
        )

    def _call_real():
        from google.genai import types

        prompt = _build_imagen_prompt(context, generated_name, generated_story)
        _log.info("Imagen 프롬프트: %s", prompt[:100])

        response = client.models.generate_images(
            model=IMAGEN_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
            ),
        )

        if not response.generated_images:
            raise RuntimeError("Imagen 응답에 생성된 이미지가 없습니다")

        generated_image = response.generated_images[0]

        # image.image_bytes 에서 바이트 추출
        if hasattr(generated_image, "image") and hasattr(
            generated_image.image, "image_bytes"
        ):
            image_bytes = generated_image.image.image_bytes
        else:
            raise RuntimeError("Imagen 응답에서 이미지 바이트를 추출할 수 없습니다")

        if not image_bytes:
            raise RuntimeError("Imagen 이미지 바이트가 비어 있습니다")

        image_url = _save_image_bytes(image_bytes, ext="png")
        return image_url

    try:
        image_url, retries = _retry_call(_call_real, "Imagen 이미지 생성")
        return ImageResult(
            image_url=image_url,
            meta=StepMeta(source="imagen_api", used_fallback=False, retries=retries),
        )
    except Exception as e:
        _log.error("Imagen 최종 실패, fallback 사용: %s", e)
        return ImageResult(
            image_url=_fallback_image_url(context),
            meta=StepMeta(
                source="fallback_placeholder",
                used_fallback=True,
                retries=AI_MAX_RETRIES,
                message=str(e),
            ),
        )


# ═══════════════════════════════════════════════════════════════════
#  3. Veo — 크리처 소개 영상 생성 (비동기)
# ═══════════════════════════════════════════════════════════════════


def request_veo_video(
    context: dict[str, Any], generated_name: str, generated_story: str
) -> VideoResult:
    # ── Mock 모드 ──
    if USE_MOCK_AI:
        return VideoResult(
            status="succeeded",
            video_url=_mock_video_url(context),
            error_message=None,
            meta=StepMeta(source="mock_veo", used_fallback=False, retries=0),
        )

    # ── 실제 API ──
    client = _get_genai_client()
    if client is None:
        return VideoResult(
            status="failed",
            video_url=None,
            error_message="Gemini API 키 미설정으로 영상 생성 불가",
            meta=StepMeta(
                source="fallback_no_video",
                used_fallback=True,
                retries=0,
                message="API 키 미설정",
            ),
        )

    def _call_real():
        prompt = _build_veo_prompt(context, generated_name, generated_story)
        _log.info("Veo 프롬프트: %s", prompt[:100])

        # Veo API는 비동기 operation을 반환 — 완료까지 폴링
        operation = client.models.generate_videos(
            model=VEO_MODEL,
            prompt=prompt,
        )

        # 타임아웃 내에서 완료 대기
        import time as _time

        deadline = _time.time() + AI_REQUEST_TIMEOUT_SEC
        while not operation.done:
            if _time.time() > deadline:
                return "running", None, "Veo 생성 진행 중 (타임아웃 초과, 폴링 필요)"
            _time.sleep(5)
            operation = client.operations.get(operation)

        # 완료된 경우 결과 추출
        result = operation.result
        if not result or not result.generated_videos:
            return "failed", None, "Veo 생성 완료되었으나 영상이 없습니다"

        video = result.generated_videos[0]

        # 영상 바이트 저장
        if hasattr(video, "video") and hasattr(video.video, "video_bytes"):
            video_bytes = video.video.video_bytes
            if video_bytes:
                dir_path = _ensure_generated_dir()
                filename = f"{uuid.uuid4().hex}.mp4"
                filepath = os.path.join(dir_path, filename)
                with open(filepath, "wb") as f:
                    f.write(video_bytes)
                video_url = f"{API_BASE_URL.rstrip('/')}/static/generated/{filename}"
                return "succeeded", video_url, None

        # URI 방식으로 제공되는 경우
        if hasattr(video, "uri") and video.uri:
            return "succeeded", video.uri, None

        return "failed", None, "Veo 영상 데이터 추출 실패"

    try:
        (status, video_url, error_message), retries = _retry_call(
            _call_real, "Veo 영상 생성"
        )
        return VideoResult(
            status=status,
            video_url=video_url,
            error_message=error_message,
            meta=StepMeta(source="veo_api", used_fallback=False, retries=retries),
        )
    except Exception as e:
        _log.error("Veo 최종 실패: %s", e)
        return VideoResult(
            status="failed",
            video_url=None,
            error_message="Veo 생성 실패. 프론트엔드 CSS fallback 연출을 사용하세요.",
            meta=StepMeta(
                source="fallback_no_video",
                used_fallback=True,
                retries=AI_MAX_RETRIES,
                message=str(e),
            ),
        )
