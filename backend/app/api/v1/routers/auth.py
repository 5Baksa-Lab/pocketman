"""Auth API Router — 회원가입 / 로그인 / 내 정보."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.core.errors import PocketmanError
from app.core.schemas import AuthLoginRequest, AuthRegisterRequest
from app.domain.auth.auth_service import get_current_user, login_user, register_user

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/auth/register", status_code=201)
def register(req: AuthRegisterRequest):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = register_user(
            email=req.email,
            nickname=req.nickname,
            password=req.password,
        )
        duration_ms = int((time.time() - start) * 1000)
        log.info(f"[{request_id}] 회원가입 성공 | email={req.email} | duration={duration_ms}ms")
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": result.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] 회원가입 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] 회원가입 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.post("/auth/login")
def login(req: AuthLoginRequest):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = login_user(email=req.email, password=req.password)
        duration_ms = int((time.time() - start) * 1000)
        log.info(f"[{request_id}] 로그인 성공 | email={req.email} | duration={duration_ms}ms")
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": result.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] 로그인 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] 로그인 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })


@router.get("/auth/me")
def me(authorization: str | None = Header(default=None)):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        user = get_current_user(authorization)
        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": user.model_dump(),
        }
    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] me 조회 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"success": False, **e.detail})
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] me 조회 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })
