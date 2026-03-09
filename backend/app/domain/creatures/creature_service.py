"""Creature/Reaction Service — 비즈니스 로직 계층."""

from __future__ import annotations

from app.core.errors import NotFoundError
from app.core.schemas import (
    CreatureCreateRequest,
    CreatureListResponse,
    CreatureResponse,
    ReactionCountItem,
    ReactionCreateRequest,
    ReactionResponse,
    ReactionSummaryResponse,
)
from app.repository.creature_repository import (
    create_creature,
    create_reaction,
    creature_exists,
    get_creature_by_id,
    get_reaction_summary,
    list_public_creatures,
)


def _normalize_creature_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    out["match_reasons"] = out.get("match_reasons") or []
    return out


def _normalize_reaction_row(row: dict) -> dict:
    out = dict(row)
    out["id"] = str(out["id"])
    out["creature_id"] = str(out["creature_id"])
    return out


def create_creature_item(req: CreatureCreateRequest) -> CreatureResponse:
    row = create_creature(req.model_dump())
    return CreatureResponse.model_validate(_normalize_creature_row(row))


def get_creature_item(creature_id: str) -> CreatureResponse:
    row = get_creature_by_id(creature_id)
    if row is None:
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")
    return CreatureResponse.model_validate(_normalize_creature_row(row))


def list_public_creature_items(limit: int, offset: int) -> CreatureListResponse:
    rows = list_public_creatures(limit=limit, offset=offset)
    items = [CreatureResponse.model_validate(_normalize_creature_row(r)) for r in rows]
    return CreatureListResponse(items=items, limit=limit, offset=offset)


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
