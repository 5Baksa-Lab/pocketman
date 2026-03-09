"""Veo Job API Router."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import PocketmanError
from app.core.schemas import VeoJobCreateRequest, VeoJobUpdateRequest
from app.domain.video.veo_job_service import create_job, get_job, update_job


log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/veo-jobs")
def create_veo_job(req: VeoJobCreateRequest):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        created = create_job(req)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": created.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] veo job 생성 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] veo job 생성 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.get("/veo-jobs/{job_id}")
def get_veo_job(job_id: str):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        job = get_job(job_id)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": job.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] veo job 조회 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] veo job 조회 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.patch("/veo-jobs/{job_id}")
def patch_veo_job(job_id: str, req: VeoJobUpdateRequest):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        updated = update_job(job_id, req)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": updated.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] veo job 수정 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] veo job 수정 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })
