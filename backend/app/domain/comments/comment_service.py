"""Comment Service — 비즈니스 로직 계층."""

from __future__ import annotations

from app.core.errors import ForbiddenError, NotFoundError
from app.core.schemas import (
    CommentAuthorInfo,
    CommentCreateRequest,
    CommentListResponse,
    CommentResponse,
)
from app.repository.comment_repository import (
    create_comment,
    delete_comment,
    get_comment_owner,
    list_comments,
)
from app.repository.creature_repository import creature_exists


def list_comments_for_creature(
    creature_id: str,
    page: int,
    limit: int,
    current_user_id: str | None = None,
) -> CommentListResponse:
    if not creature_exists(creature_id):
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    rows, total = list_comments(creature_id, page=page, limit=limit)
    items = [
        CommentResponse(
            id=str(r["id"]),
            content=r["content"],
            author=CommentAuthorInfo(
                id=str(r["author_id"]),
                nickname=r["author_nickname"],
            ),
            created_at=r["created_at"],
            is_mine=(str(r["author_id"]) == current_user_id) if current_user_id else False,
        )
        for r in rows
    ]
    return CommentListResponse(items=items, total=total, page=page)


def create_comment_for_creature(
    creature_id: str,
    user_id: str,
    req: CommentCreateRequest,
) -> CommentResponse:
    if not creature_exists(creature_id):
        raise NotFoundError("크리처를 찾을 수 없습니다.", "CREATURE_NOT_FOUND")

    row = create_comment(creature_id=creature_id, user_id=user_id, content=req.content)
    return CommentResponse(
        id=str(row["id"]),
        content=row["content"],
        author=CommentAuthorInfo(id=row["author_id"], nickname=row["author_nickname"]),
        created_at=row["created_at"],
        is_mine=True,
    )


def delete_comment_by_id(comment_id: str, current_user_id: str) -> None:
    owner = get_comment_owner(comment_id)
    if owner is None:
        raise NotFoundError("댓글을 찾을 수 없습니다.", "COMMENT_NOT_FOUND")
    if owner != current_user_id:
        raise ForbiddenError("본인의 댓글만 삭제할 수 있습니다.", "FORBIDDEN")
    delete_comment(comment_id)
