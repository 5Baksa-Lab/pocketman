"""Creature/Reaction/Comment/Like API Router."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.core.errors import PocketmanError
from app.core.schemas import (
    CommentCreateRequest,
    CreatureCreateRequest,
    CreaturePatchRequest,
    ReactionCreateRequest,
)
from app.domain.auth.auth_service import get_current_user
from app.domain.comments.comment_service import (
    create_comment_for_creature,
    delete_comment_by_id,
    list_comments_for_creature,
)
from app.domain.creatures.creature_service import (
    add_reaction,
    create_creature_item,
    delete_creature_item,
    get_creature_detail_item,
    get_creature_item,
    get_reaction_summary_for_creature,
    list_liked_creature_items,
    list_my_creature_items,
    list_public_creature_items,
    patch_creature_item,
    toggle_like_item,
)


log = logging.getLogger(__name__)
router = APIRouter()


def _ok(request_id: str, start: float, data: object) -> dict:
    return {
        "success": True,
        "request_id": request_id,
        "duration_ms": int((time.time() - start) * 1000),
        "data": data.model_dump() if hasattr(data, "model_dump") else data,
    }


def _err(e: Exception, request_id: str, start: float, label: str):
    duration_ms = int((time.time() - start) * 1000)
    if isinstance(e, PocketmanError):
        log.warning(f"[{request_id}] {label} 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    log.error(f"[{request_id}] {label} 오류 | duration={duration_ms}ms | {e}")
    return JSONResponse(status_code=500, content={
        "success": False,
        "error_code": "INTERNAL_ERROR",
        "message": "서버 내부 오류가 발생했습니다.",
    })


# ── 정적 경로 (동적 {creature_id} 앞에 등록) ────────────────────────────────

@router.get("/creatures/public")
def list_public_creatures(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        result = list_public_creature_items(limit=limit, offset=offset)
        return _ok(rid, t, result)
    except Exception as e:
        return _err(e, rid, t, "public creature 조회")


@router.get("/creatures/my")
def get_my_creatures(authorization: str | None = Header(default=None)):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        result = list_my_creature_items(user.id)
        return _ok(rid, t, result)
    except Exception as e:
        return _err(e, rid, t, "내 creature 조회")


@router.get("/creatures/liked")
def get_liked_creatures(authorization: str | None = Header(default=None)):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        result = list_liked_creature_items(user.id)
        return _ok(rid, t, result)
    except Exception as e:
        return _err(e, rid, t, "좋아요 creature 조회")


# ── POST /creatures ──────────────────────────────────────────────────────────

@router.post("/creatures")
def create_creature(
    req: CreatureCreateRequest,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user_id = None
        if authorization:
            try:
                user = get_current_user(authorization)
                user_id = user.id
            except PocketmanError:
                pass  # 미인증이면 anonymous 크리처로 생성

        created = create_creature_item(req, user_id=user_id)
        log.info(f"[{rid}] creature 생성 성공 | id={created.id}")
        return _ok(rid, t, created)
    except Exception as e:
        return _err(e, rid, t, "creature 생성")


# ── 동적 경로 ────────────────────────────────────────────────────────────────

@router.get("/creatures/{creature_id}")
def get_creature(
    creature_id: str,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        current_user_id = None
        if authorization:
            try:
                user = get_current_user(authorization)
                current_user_id = user.id
            except PocketmanError:
                pass
        item = get_creature_detail_item(creature_id, current_user_id=current_user_id)
        return _ok(rid, t, item)
    except Exception as e:
        return _err(e, rid, t, "creature 조회")


@router.patch("/creatures/{creature_id}")
def patch_creature(
    creature_id: str,
    req: CreaturePatchRequest,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        current_user_id = None
        if authorization:
            try:
                user = get_current_user(authorization)
                current_user_id = user.id
            except PocketmanError:
                pass
        updated = patch_creature_item(creature_id, req, current_user_id=current_user_id)
        return _ok(rid, t, updated)
    except Exception as e:
        return _err(e, rid, t, "creature patch")


@router.delete("/creatures/{creature_id}")
def delete_creature(
    creature_id: str,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        delete_creature_item(creature_id, current_user_id=user.id)
        return JSONResponse(status_code=204, content=None)
    except Exception as e:
        return _err(e, rid, t, "creature 삭제")


# ── Like ─────────────────────────────────────────────────────────────────────

@router.post("/creatures/{creature_id}/like")
def add_like(creature_id: str, authorization: str | None = Header(default=None)):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        result = toggle_like_item(creature_id, user_id=user.id, add=True)
        return _ok(rid, t, result)
    except Exception as e:
        return _err(e, rid, t, "like 추가")


@router.delete("/creatures/{creature_id}/like")
def remove_like(creature_id: str, authorization: str | None = Header(default=None)):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        result = toggle_like_item(creature_id, user_id=user.id, add=False)
        return _ok(rid, t, result)
    except Exception as e:
        return _err(e, rid, t, "like 취소")


# ── Comments ─────────────────────────────────────────────────────────────────

@router.get("/creatures/{creature_id}/comments")
def list_comments(
    creature_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        current_user_id = None
        if authorization:
            try:
                user = get_current_user(authorization)
                current_user_id = user.id
            except PocketmanError:
                pass
        result = list_comments_for_creature(creature_id, page, limit, current_user_id)
        return _ok(rid, t, result)
    except Exception as e:
        return _err(e, rid, t, "댓글 목록 조회")


@router.post("/creatures/{creature_id}/comments")
def create_comment(
    creature_id: str,
    req: CommentCreateRequest,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        result = create_comment_for_creature(creature_id, user_id=user.id, req=req)
        return JSONResponse(status_code=201, content={
            "success": True,
            "request_id": rid,
            "duration_ms": int((time.time() - t) * 1000),
            "data": result.model_dump(),
        })
    except Exception as e:
        return _err(e, rid, t, "댓글 작성")


@router.delete("/creatures/{creature_id}/comments/{comment_id}")
def delete_comment(
    creature_id: str,
    comment_id: str,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        delete_comment_by_id(comment_id, current_user_id=user.id)
        return JSONResponse(status_code=204, content=None)
    except Exception as e:
        return _err(e, rid, t, "댓글 삭제")


# ── Reactions (기존 유지) ────────────────────────────────────────────────────

@router.post("/creatures/{creature_id}/reactions")
def create_reaction(creature_id: str, req: ReactionCreateRequest):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        created = add_reaction(creature_id, req)
        return _ok(rid, t, created)
    except Exception as e:
        return _err(e, rid, t, "reaction 등록")


@router.get("/creatures/{creature_id}/reactions/summary")
def reaction_summary(creature_id: str):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        summary = get_reaction_summary_for_creature(creature_id)
        return _ok(rid, t, summary)
    except Exception as e:
        return _err(e, rid, t, "reaction summary")
