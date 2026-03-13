"""Creature/Reaction Service — 비즈니스 로직 계층."""

from __future__ import annotations

from app.core.errors import ForbiddenError, NotFoundError
from app.core.schemas import (
    CreatureCreateRequest,
    CreatureDetailResponse,
    CreatureListResponse,
    CreatureOwnerInfo,
    CreaturePatchRequest,
    CreatureResponse,
    LikeResponse,
    MyCreatureItem,
    MyCreatureListResponse,
    ReactionCountItem,
    ReactionCreateRequest,
    ReactionResponse,
    ReactionSummaryResponse,
)
from app.repository.creature_repository import (
    add_like,
    create_creature,
    create_reaction,
    creature_exists,
    delete_creature,
    get_creature_by_id,
    get_creature_detail_by_id,
    get_reaction_summary,
    list_liked_creatures,
    list_my_creatures,
    list_public_creatures,
    patch_creature,
    remove_like,
)


def _normalize_creature_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    if out.get("user_id"):
        out["user_id"] = str(out["user_id"])
    out["match_reasons"] = out.get("match_reasons") or []
    return out


def _normalize_reaction_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    out["creature_id"] = str(out["creature_id"])
    return out


def create_creature_item(req: CreatureCreateRequest, user_id: str | None = None) -> CreatureResponse:
    payload = req.model_dump()
    payload["user_id"] = user_id
    row = create_creature(payload)
    return CreatureResponse.model_validate(_normalize_creature_row(row))


def get_creature_item(creature_id: str) -> CreatureResponse:
    row = get_creature_by_id(creature_id)
    if row is None:
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")
    return CreatureResponse.model_validate(_normalize_creature_row(row))


def get_creature_detail_item(
    creature_id: str,
    current_user_id: str | None = None,
) -> CreatureDetailResponse:
    row = get_creature_detail_by_id(creature_id, current_user_id)
    if row is None:
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    # 비공개 크리처 — 소유자가 아닌 경우 404
    if not row["is_public"] and str(row.get("user_id") or "") != (current_user_id or ""):
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    owner = None
    if row.get("owner_id"):
        owner = CreatureOwnerInfo(id=str(row["owner_id"]), nickname=row["owner_nickname"])

    return CreatureDetailResponse(
        id=str(row["id"]),
        matched_pokemon_id=row["matched_pokemon_id"],
        match_rank=row["match_rank"],
        similarity_score=row["similarity_score"],
        match_reasons=row.get("match_reasons") or [],
        name=row["name"],
        story=row.get("story"),
        image_url=row.get("image_url"),
        video_url=row.get("video_url"),
        is_public=row["is_public"],
        created_at=row["created_at"],
        matched_pokemon_name_kr=row.get("matched_pokemon_name_kr"),
        primary_type=row.get("primary_type"),
        secondary_type=row.get("secondary_type"),
        owner=owner,
        like_count=row.get("like_count", 0),
        is_liked=row.get("is_liked", False),
    )


def list_public_creature_items(limit: int, offset: int) -> CreatureListResponse:
    rows = list_public_creatures(limit=limit, offset=offset)
    items = [CreatureResponse.model_validate(_normalize_creature_row(r)) for r in rows]
    return CreatureListResponse(items=items, limit=limit, offset=offset)


def list_my_creature_items(user_id: str) -> MyCreatureListResponse:
    rows = list_my_creatures(user_id)
    items = [
        MyCreatureItem(
            id=str(r["id"]),
            name=r["name"],
            is_public=r["is_public"],
            image_url=r.get("image_url"),
            created_at=r["created_at"],
            matched_pokemon_name_kr=r.get("matched_pokemon_name_kr"),
        )
        for r in rows
    ]
    return MyCreatureListResponse(items=items, total=len(items))


def list_liked_creature_items(user_id: str) -> MyCreatureListResponse:
    rows = list_liked_creatures(user_id)
    items = [
        MyCreatureItem(
            id=str(r["id"]),
            name=r["name"],
            is_public=r["is_public"],
            image_url=r.get("image_url"),
            created_at=r["created_at"],
            matched_pokemon_name_kr=r.get("matched_pokemon_name_kr"),
        )
        for r in rows
    ]
    return MyCreatureListResponse(items=items, total=len(items))


def patch_creature_item(
    creature_id: str,
    req: CreaturePatchRequest,
    current_user_id: str | None = None,
) -> CreatureResponse:
    row = get_creature_by_id(creature_id)
    if row is None:
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    # 소유자 확인: user_id가 있는 creature는 소유자만 수정 가능
    creature_owner = str(row["user_id"]) if row.get("user_id") else None
    if creature_owner and creature_owner != current_user_id:
        raise ForbiddenError("본인의 크리처만 수정할 수 있습니다.", "FORBIDDEN")

    fields: dict = {}
    if req.name is not None:
        fields["name"] = req.name
    if req.is_public is not None:
        fields["is_public"] = req.is_public

    updated = patch_creature(creature_id, fields)
    if updated is None:
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")
    return CreatureResponse.model_validate(_normalize_creature_row(updated))


def delete_creature_item(creature_id: str, current_user_id: str) -> None:
    row = get_creature_by_id(creature_id)
    if row is None:
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    creature_owner = str(row["user_id"]) if row.get("user_id") else None
    if creature_owner != current_user_id:
        raise ForbiddenError("본인의 크리처만 삭제할 수 있습니다.", "FORBIDDEN")

    delete_creature(creature_id)


def toggle_like_item(creature_id: str, user_id: str, add: bool) -> LikeResponse:
    if not creature_exists(creature_id):
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    if add:
        count = add_like(user_id=user_id, creature_id=creature_id)
    else:
        count = remove_like(user_id=user_id, creature_id=creature_id)
    return LikeResponse(like_count=count)


def add_reaction(creature_id: str, req: ReactionCreateRequest) -> ReactionResponse:
    if not creature_exists(creature_id):
        raise NotFoundError("리액션 대상 크리처가 없습니다.", "CREATURE_NOT_FOUND")

    row = create_reaction(creature_id=creature_id, emoji_type=req.emoji_type)
    return ReactionResponse.model_validate(_normalize_reaction_row(row))


def get_reaction_summary_for_creature(creature_id: str) -> ReactionSummaryResponse:
    if not creature_exists(creature_id):
        raise NotFoundError("리액션 대상 크리처가 없습니다.", "CREATURE_NOT_FOUND")

    rows = get_reaction_summary(creature_id)
    counts = [ReactionCountItem.model_validate(r) for r in rows]
    total = sum(item.count for item in counts)
    return ReactionSummaryResponse(creature_id=creature_id, counts=counts, total=total)
