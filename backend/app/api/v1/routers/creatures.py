"""Creature/Reaction API Router."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.core.errors import PocketmanError
from app.core.schemas import (
    CreatureCreateRequest,
    ReactionCreateRequest,
)
from app.domain.creatures.creature_service import (
    add_reaction,
    create_creature_item,
    get_creature_item,
    get_reaction_summary_for_creature,
    list_public_creature_items,
)


log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/creatures")
def create_creature(req: CreatureCreateRequest):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        created = create_creature_item(req)
        duration_ms = int((time.time() - start) * 1000)
        log.info(f"[{request_id}] creature 생성 성공 | id={created.id} | duration={duration_ms}ms")
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": created.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] creature 생성 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] creature 생성 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.get("/creatures/public")
def list_public_creatures(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = list_public_creature_items(limit=limit, offset=offset)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": result.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] public creature 조회 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] public creature 조회 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.get("/creatures/{creature_id}")
def get_creature(creature_id: str):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        item = get_creature_item(creature_id)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": item.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] creature 조회 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] creature 조회 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.post("/creatures/{creature_id}/reactions")
def create_reaction(creature_id: str, req: ReactionCreateRequest):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        created = add_reaction(creature_id, req)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": created.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] reaction 등록 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] reaction 등록 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.get("/creatures/{creature_id}/reactions/summary")
def reaction_summary(creature_id: str):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        summary = get_reaction_summary_for_creature(creature_id)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": summary.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] reaction summary 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] reaction summary 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })
