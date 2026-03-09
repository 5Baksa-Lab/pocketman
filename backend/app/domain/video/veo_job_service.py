"""Veo Job Service — 영상 생성 비동기 작업 로직."""

from __future__ import annotations

from app.core.errors import InvalidRequestError, NotFoundError
from app.core.schemas import VeoJobCreateRequest, VeoJobResponse, VeoJobUpdateRequest
from app.repository.veo_job_repository import (
    VALID_STATUSES,
    create_veo_job,
    creature_exists_for_job,
    get_veo_job,
    update_veo_job,
)


def _normalize_job_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    out["creature_id"] = str(out["creature_id"])
    return out


def create_job(req: VeoJobCreateRequest) -> VeoJobResponse:
    if not creature_exists_for_job(req.creature_id):
        raise NotFoundError("영상 생성 대상 크리처가 없습니다.", "CREATURE_NOT_FOUND")

    row = create_veo_job(req.creature_id)
    return VeoJobResponse.model_validate(_normalize_job_row(row))


def get_job(job_id: str) -> VeoJobResponse:
    row = get_veo_job(job_id)
    if row is None:
        raise NotFoundError("Veo 작업을 찾을 수 없습니다.", "VEO_JOB_NOT_FOUND")
    return VeoJobResponse.model_validate(_normalize_job_row(row))


def update_job(job_id: str, req: VeoJobUpdateRequest) -> VeoJobResponse:
    if req.status not in VALID_STATUSES:
        raise InvalidRequestError(
            message=f"허용되지 않은 status입니다: {req.status}",
            error_code="INVALID_VEO_STATUS",
        )

    row = update_veo_job(
        job_id=job_id,
        status=req.status,
        video_url=req.video_url,
        error_message=req.error_message,
    )
    if row is None:
        raise NotFoundError("Veo 작업을 찾을 수 없습니다.", "VEO_JOB_NOT_FOUND")

    return VeoJobResponse.model_validate(_normalize_job_row(row))
