"""User Service — 비즈니스 로직 계층."""

from __future__ import annotations

from passlib.context import CryptContext

from app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from app.core.schemas import (
    DeleteAccountRequest,
    NicknameAvailabilityResponse,
    PasswordChangeRequest,
    UserProfileResponse,
    UserUpdateRequest,
)
from app.repository.user_repository import (
    check_nickname_available,
    delete_user,
    get_user_password_hash,
    get_user_profile,
    update_password_hash,
    update_user_profile,
)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _normalize_profile_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    if out.get("avatar_creature_id"):
        out["avatar_creature_id"] = str(out["avatar_creature_id"])
    return out


def get_profile(user_id: str) -> UserProfileResponse:
    row = get_user_profile(user_id)
    if row is None:
        raise NotFoundError("사용자를 찾을 수 없습니다.", "USER_NOT_FOUND")
    return UserProfileResponse.model_validate(_normalize_profile_row(row))


def check_nickname(nickname: str, current_user_id: str | None = None) -> NicknameAvailabilityResponse:
    available = check_nickname_available(nickname, exclude_user_id=current_user_id)
    return NicknameAvailabilityResponse(available=available)


def update_profile(user_id: str, req: UserUpdateRequest) -> UserProfileResponse:
    fields: dict = {}
    if req.name is not None:
        # 닉네임 중복 검사 (본인 제외)
        if not check_nickname_available(req.name, exclude_user_id=user_id):
            raise ConflictError("이미 사용 중인 닉네임입니다.", "NICKNAME_ALREADY_EXISTS")
        fields["nickname"] = req.name
    if req.bio is not None:
        fields["bio"] = req.bio
    if req.avatar_creature_id is not None:
        fields["avatar_creature_id"] = req.avatar_creature_id
    if req.dark_mode is not None:
        fields["dark_mode"] = req.dark_mode
    if req.font_size is not None:
        fields["font_size"] = req.font_size

    row = update_user_profile(user_id, fields)
    if row is None:
        raise NotFoundError("사용자를 찾을 수 없습니다.", "USER_NOT_FOUND")
    return UserProfileResponse.model_validate(_normalize_profile_row(row))


def change_password(user_id: str, req: PasswordChangeRequest) -> None:
    current_hash = get_user_password_hash(user_id)
    if current_hash is None:
        raise NotFoundError("사용자를 찾을 수 없습니다.", "USER_NOT_FOUND")
    if not current_hash:
        raise InvalidRequestError("소셜 로그인 계정은 비밀번호를 변경할 수 없습니다.", "NO_PASSWORD")
    if not _pwd_context.verify(req.current_password, current_hash):
        raise InvalidRequestError("현재 비밀번호가 올바르지 않습니다.", "INVALID_CURRENT_PASSWORD")
    new_hash = _pwd_context.hash(req.new_password)
    update_password_hash(user_id, new_hash)


def delete_account(user_id: str, req: DeleteAccountRequest) -> None:
    current_hash = get_user_password_hash(user_id)
    if current_hash is None:
        raise NotFoundError("사용자를 찾을 수 없습니다.", "USER_NOT_FOUND")
    # 이메일 계정: 비밀번호 확인
    if current_hash and req.password:
        if not _pwd_context.verify(req.password, current_hash):
            raise InvalidRequestError("비밀번호가 올바르지 않습니다.", "INVALID_PASSWORD")
    delete_user(user_id)
