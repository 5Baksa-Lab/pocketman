"""Generation adapters for Imagen / Gemini Flash / Veo with mock-real switch.

실제 API 연동 지점은 환경변수 기반 endpoint 및 key를 사용한다.
- USE_MOCK_AI=true: deterministic mock 결과 반환
- USE_MOCK_AI=false: 실 API 시도 + 재시도 + fallback
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
import time
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import (
    AI_MAX_RETRIES,
    AI_REQUEST_TIMEOUT_SEC,
    AI_RETRY_BASE_DELAY_SEC,
    GEMINI_API_KEY,
    GEMINI_FLASH_MODEL,
    IMAGEN_API_URL,
    USE_MOCK_AI,
    VEO_API_URL,
)

try:
    import google.generativeai as genai
except ModuleNotFoundError:  # pragma: no cover
    genai = None  # type: ignore


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


def _retry_call(fn, op_name: str):
    attempts = max(1, AI_MAX_RETRIES + 1)
    last_error: Exception | None = None

    for idx in range(attempts):
        try:
            value = fn()
            return value, idx
        except Exception as e:  # pragma: no cover - external dependency path
            last_error = e
            if idx < attempts - 1:
                delay = AI_RETRY_BASE_DELAY_SEC * (2 ** idx)
                time.sleep(delay)

    if last_error is None:
        raise RuntimeError(f"{op_name} 실패 (원인 미상)")
    raise RuntimeError(f"{op_name} 실패: {last_error}")


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


def generate_name_story(context: dict[str, Any]) -> StoryNameResult:
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

    if not GEMINI_API_KEY or genai is None:
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
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        resp = model.generate_content(_build_story_prompt(context))
        parsed = _parse_json_object(getattr(resp, "text", ""))
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


def generate_image(context: dict[str, Any], generated_name: str, generated_story: str) -> ImageResult:
    if USE_MOCK_AI:
        return ImageResult(
            image_url=_fallback_image_url(context),
            meta=StepMeta(source="mock_imagen", used_fallback=False, retries=0),
        )

    def _call_real():
        if not IMAGEN_API_URL:
            raise RuntimeError("IMAGEN_API_URL 미설정")

        payload = {
            "name": generated_name,
            "story": generated_story,
            "matched_pokemon": context.get("matched_pokemon_name_en"),
            "primary_type": context.get("primary_type"),
            "secondary_type": context.get("secondary_type"),
        }
        with httpx.Client(timeout=AI_REQUEST_TIMEOUT_SEC) as client:
            resp = client.post(IMAGEN_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        image_url = str(data.get("image_url", "")).strip()
        if not image_url:
            raise RuntimeError("Imagen 응답에 image_url 누락")
        return image_url

    try:
        image_url, retries = _retry_call(_call_real, "Imagen 이미지 생성")
        return ImageResult(
            image_url=image_url,
            meta=StepMeta(source="imagen_api", used_fallback=False, retries=retries),
        )
    except Exception as e:
        return ImageResult(
            image_url=_fallback_image_url(context),
            meta=StepMeta(
                source="fallback_placeholder",
                used_fallback=True,
                retries=AI_MAX_RETRIES,
                message=str(e),
            ),
        )


def request_veo_video(context: dict[str, Any], generated_name: str, generated_story: str) -> VideoResult:
    if USE_MOCK_AI:
        return VideoResult(
            status="succeeded",
            video_url=_mock_video_url(context),
            error_message=None,
            meta=StepMeta(source="mock_veo", used_fallback=False, retries=0),
        )

    def _call_real():
        if not VEO_API_URL:
            raise RuntimeError("VEO_API_URL 미설정")

        payload = {
            "creature_id": context.get("id"),
            "name": generated_name,
            "story": generated_story,
            "image_url": context.get("image_url"),
            "matched_pokemon": context.get("matched_pokemon_name_en"),
        }
        with httpx.Client(timeout=AI_REQUEST_TIMEOUT_SEC) as client:
            resp = client.post(VEO_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        status = str(data.get("status", "queued")).strip().lower() or "queued"
        video_url = data.get("video_url")
        error_message = data.get("error_message")
        if status not in {"queued", "running", "succeeded", "failed", "canceled"}:
            status = "queued"
        return status, video_url, error_message

    try:
        (status, video_url, error_message), retries = _retry_call(_call_real, "Veo 영상 생성 요청")
        return VideoResult(
            status=status,
            video_url=video_url,
            error_message=error_message,
            meta=StepMeta(source="veo_api", used_fallback=False, retries=retries),
        )
    except Exception as e:
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
