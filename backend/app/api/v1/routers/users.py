"""User Profile API Router."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.core.errors import PocketmanError
from app.core.schemas import (
    DeleteAccountRequest,
    PasswordChangeRequest,
    UserUpdateRequest,
)
from app.domain.auth.auth_service import get_current_user
from app.domain.users.user_service import (
    change_password,
    check_nickname,
    delete_account,
    get_profile,
    update_profile,
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


@router.get("/users/check-nickname")
def check_nickname_endpoint(
    q: str = Query(min_length=2, max_length=50),
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
        result = check_nickname(q, current_user_id=current_user_id)
        return _ok(rid, t, result)
    except Exception as e:
        return _err(e, rid, t, "닉네임 중복 검사")


@router.get("/users/me")
def get_my_profile(authorization: str | None = Header(default=None)):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        profile = get_profile(user.id)
        return _ok(rid, t, profile)
    except Exception as e:
        return _err(e, rid, t, "프로필 조회")


@router.patch("/users/me")
def update_my_profile(
    req: UserUpdateRequest,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        profile = update_profile(user.id, req)
        return _ok(rid, t, profile)
    except Exception as e:
        return _err(e, rid, t, "프로필 수정")


@router.patch("/users/me/password")
def change_my_password(
    req: PasswordChangeRequest,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        change_password(user.id, req)
        return _ok(rid, t, {"message": "비밀번호가 변경됐습니다."})
    except Exception as e:
        return _err(e, rid, t, "비밀번호 변경")


@router.delete("/users/me")
def delete_my_account(
    req: DeleteAccountRequest,
    authorization: str | None = Header(default=None),
):
    rid, t = str(uuid.uuid4())[:8], time.time()
    try:
        user = get_current_user(authorization)
        delete_account(user.id, req)
        return JSONResponse(status_code=204, content=None)
    except Exception as e:
        return _err(e, rid, t, "회원 탈퇴")
