"""Generation pipeline service (Imagen + Gemini Flash + Veo)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.adapter.generation_adapter import (
    ImageResult,
    StepMeta,
    StoryNameResult,
    VideoResult,
    generate_image,
    generate_name_story,
    generate_sprite,
    request_veo_video,
)
from app.core.errors import NotFoundError
from app.core.schemas import (
    CreatureResponse,
    GenerationPipelineResponse,
    GenerationStartRequest,
    GenerationStepMeta,
    VeoJobResponse,
)
from app.repository.creature_repository import (
    get_creature_generation_context,
    update_creature_generated_fields,
    update_creature_sprite_url,
    update_creature_video_url,
)
from app.repository.veo_job_repository import create_veo_job, update_veo_job


def _normalize_creature_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    out["match_reasons"] = out.get("match_reasons") or []
    return out


def _to_step_meta(meta: StepMeta) -> GenerationStepMeta:
    return GenerationStepMeta(
        source=meta.source,
        used_fallback=meta.used_fallback,
        retries=meta.retries,
        message=meta.message,
    )


def _existing_story_name(context: dict) -> StoryNameResult:
    name = str(context.get("name") or "포켓크리처")
    story = str(context.get("story") or "아직 스토리가 생성되지 않았습니다.")
    return StoryNameResult(
        name=name,
        story=story,
        meta=StepMeta(source="reuse_existing", used_fallback=False, retries=0),
    )


def _existing_image(context: dict) -> ImageResult:
    image_url = str(context.get("image_url") or "")
    if not image_url:
        image_url = "https://placehold.co/1024x1024/png?text=Creature"
        return ImageResult(
            image_url=image_url,
            meta=StepMeta(
                source="reuse_missing_placeholder",
                used_fallback=True,
                retries=0,
                message="기존 이미지가 없어 placeholder 사용",
            ),
        )
    return ImageResult(
        image_url=image_url,
        meta=StepMeta(source="reuse_existing", used_fallback=False, retries=0),
    )


def start_generation_pipeline(creature_id: str, req: GenerationStartRequest) -> GenerationPipelineResponse:
    context = get_creature_generation_context(creature_id)
    if context is None:
        raise NotFoundError("생성 대상 크리처가 없습니다.", "CREATURE_NOT_FOUND")

    # 1) 이름/스토리 + 이미지 (가능 시 병렬)
    if req.regenerate_name_story and req.regenerate_image:
        provisional_story = _existing_story_name(context)
        with ThreadPoolExecutor(max_workers=2) as ex:
            story_future = ex.submit(generate_name_story, context)
            image_future = ex.submit(
                generate_image,
                context,
                provisional_story.name,
                provisional_story.story,
            )
            story_result = story_future.result()
            image_result = image_future.result()
    else:
        if req.regenerate_name_story:
            story_result = generate_name_story(context)
        else:
            story_result = _existing_story_name(context)

        if req.regenerate_image:
            image_result = generate_image(
                context=context,
                generated_name=story_result.name,
                generated_story=story_result.story,
            )
        else:
            image_result = _existing_image(context)

    # 3) creature 업데이트
    updated = update_creature_generated_fields(
        creature_id=creature_id,
        name=story_result.name,
        story=story_result.story,
        image_url=image_result.image_url,
    )
    if updated is None:
        raise NotFoundError("생성 결과를 저장할 크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    creature = CreatureResponse.model_validate(_normalize_creature_row(updated))

    # 4) 영상 생성
    veo_job_resp: VeoJobResponse | None = None
    if req.trigger_video:
        job = create_veo_job(creature_id)

        video_context = {
            **context,
            "id": creature_id,
            "image_url": image_result.image_url,
        }
        video_result: VideoResult = request_veo_video(
            context=video_context,
            generated_name=story_result.name,
            generated_story=story_result.story,
        )

        updated_job = update_veo_job(
            job_id=str(job["id"]),
            status=video_result.status,
            video_url=video_result.video_url,
            error_message=video_result.error_message,
        )
        if updated_job is None:
            raise NotFoundError("생성된 Veo 작업을 찾을 수 없습니다.", "VEO_JOB_NOT_FOUND")

        if video_result.status == "succeeded" and video_result.video_url:
            maybe_updated_creature = update_creature_video_url(creature_id, video_result.video_url)
            if maybe_updated_creature:
                creature = CreatureResponse.model_validate(_normalize_creature_row(maybe_updated_creature))

        veo_job_resp = VeoJobResponse.model_validate({
            **updated_job,
            "id": str(updated_job["id"]),
            "creature_id": str(updated_job["creature_id"]),
        })
    else:
        video_result = VideoResult(
            status="skipped",
            video_url=None,
            error_message=None,
            meta=StepMeta(source="skipped", used_fallback=False, retries=0, message="영상 생성 비활성화"),
        )

    return GenerationPipelineResponse(
        creature=creature,
        veo_job=veo_job_resp,
        image=_to_step_meta(image_result.meta),
        story=_to_step_meta(story_result.meta),
        video=_to_step_meta(video_result.meta),
    )


def generate_sprite_for_creature(creature_id: str) -> dict:
    """4방향 도트 스프라이트를 생성해 DB에 저장하고 업데이트된 크리처 row를 반환한다."""
    context = get_creature_generation_context(creature_id)
    if context is None:
        raise NotFoundError("스프라이트를 생성할 크리처가 없습니다.", "CREATURE_NOT_FOUND")

    sprite_result = generate_sprite(context)

    updated = update_creature_sprite_url(creature_id, sprite_result.sprite_url)
    if updated is None:
        raise NotFoundError("스프라이트 URL 저장 실패 — 크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    return {
        **_normalize_creature_row(updated),
        "sprite_meta": {
            "source": sprite_result.meta.source,
            "used_fallback": sprite_result.meta.used_fallback,
            "retries": sprite_result.meta.retries,
            "message": sprite_result.meta.message,
        },
    }
