"""Generation pipeline API Router."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import PocketmanError
from app.core.schemas import GenerationStartRequest
from app.domain.generation.pipeline_service import (
    generate_sprite_for_creature,
    start_generation_pipeline,
)


log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/creatures/{creature_id}/generate")
def generate_creature_assets(creature_id: str, req: GenerationStartRequest):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        result = start_generation_pipeline(creature_id, req)
        duration_ms = int((time.time() - start) * 1000)
        log.info(f"[{request_id}] generation 성공 | creature_id={creature_id} | duration={duration_ms}ms")
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": result.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] generation 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] generation 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "생성 파이프라인 실행 중 오류가 발생했습니다.",
        })


@router.post("/creatures/{creature_id}/sprite")
def generate_creature_sprite(creature_id: str):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        result = generate_sprite_for_creature(creature_id)
        duration_ms = int((time.time() - start) * 1000)
        log.info(f"[{request_id}] sprite 생성 성공 | creature_id={creature_id} | duration={duration_ms}ms")
        return {"success": True, "request_id": request_id, "duration_ms": duration_ms, "data": result}
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] sprite 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] sprite 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "스프라이트 생성 중 오류가 발생했습니다.",
        })
