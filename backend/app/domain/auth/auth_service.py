"""Auth Service — 인증 비즈니스 로직 계층."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import psycopg2
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import JWT_ACCESS_TOKEN_EXPIRE_HOURS, JWT_ALGORITHM, JWT_SECRET_KEY
from app.core.errors import ConflictError, UnauthorizedError
from app.core.schemas import AuthTokenResponse, AuthUserResponse
from app.repository.user_repository import create_user, get_user_by_email, get_user_by_id

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def _create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _normalize_user_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    return out


def _normalize_email(email: str) -> str:
    """이메일 정규화: 공백 제거 + 소문자 통일."""
    return email.strip().lower()


def register_user(email: str, nickname: str, password: str) -> AuthTokenResponse:
    email = _normalize_email(email)

    # 사전 중복 체크 (race condition 방지를 위해 DB unique 제약도 병행)
    existing = get_user_by_email(email)
    if existing:
        raise ConflictError("이미 사용 중인 이메일입니다.", "EMAIL_ALREADY_EXISTS")

    password_hash = _hash_password(password)
    try:
        row = create_user(email=email, nickname=nickname.strip(), password_hash=password_hash)
    except psycopg2.errors.UniqueViolation:
        # 동시 요청 race condition — DB unique 충돌을 409로 변환
        raise ConflictError("이미 사용 중인 이메일입니다.", "EMAIL_ALREADY_EXISTS")

    row = _normalize_user_row(row)
    token = _create_access_token(row["id"])
    user = AuthUserResponse.model_validate(row)
    return AuthTokenResponse(access_token=token, user=user)


def login_user(email: str, password: str) -> AuthTokenResponse:
    email = _normalize_email(email)
    row = get_user_by_email(email)
    if not row or not _verify_password(password, row["password_hash"]):
        raise UnauthorizedError("이메일 또는 비밀번호가 올바르지 않습니다.", "INVALID_CREDENTIALS")

    row = _normalize_user_row(row)
    token = _create_access_token(row["id"])
    user_data = {k: v for k, v in row.items() if k != "password_hash"}
    user = AuthUserResponse.model_validate(user_data)
    return AuthTokenResponse(access_token=token, user=user)


def get_current_user(authorization: str | None) -> AuthUserResponse:
    """Bearer 토큰 검증 → 현재 유저 반환."""
    if not authorization:
        raise UnauthorizedError("인증 토큰이 없습니다.", "MISSING_TOKEN")

    # RFC 7235: Authorization 헤더 스킴은 case-insensitive
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("인증 토큰이 없습니다.", "MISSING_TOKEN")

    token = parts[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise UnauthorizedError("유효하지 않은 토큰입니다.", "INVALID_TOKEN")
    except JWTError:
        raise UnauthorizedError("유효하지 않은 토큰입니다.", "INVALID_TOKEN")

    row = get_user_by_id(user_id)
    if not row:
        raise UnauthorizedError("사용자를 찾을 수 없습니다.", "USER_NOT_FOUND")

    return AuthUserResponse.model_validate(_normalize_user_row(row))
