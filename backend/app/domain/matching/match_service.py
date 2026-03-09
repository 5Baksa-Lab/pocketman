"""
Match Service — 이미지 입력 → Top-3 포켓몬 반환 비즈니스 로직
"""

from app.adapter.cv_adapter import build_user_vector
from app.repository.pokemon_repository import search_top_k
from app.domain.matching.reasoning_service import generate_reasons
from app.core.schemas import MatchResponse, PokemonMatchResult
from app.core.config import TOP_K


def match_pokemon(image_bytes: bytes) -> MatchResponse:
    """
    1. CV Adapter: 이미지 → 28차원 사용자 벡터
    2. Repository: pgvector Top-K 검색
    3. Reasoning:  유사도 근거 생성
    4. 응답 조립
    """
    # Step 1: 얼굴 특징 추출 → 사용자 벡터
    user_vector, raw_features = build_user_vector(image_bytes)
    user_visual = raw_features.get("visual", {})
    user_impression = raw_features.get("impression", {})

    # Step 2: pgvector Top-K 검색
    pokemon_rows = search_top_k(user_vector, k=TOP_K)

    # Step 3: 결과 조립
    top3 = []
    for rank, row in enumerate(pokemon_rows, 1):
        reasons = generate_reasons(user_visual, user_impression, row)
        top3.append(PokemonMatchResult(
            rank=rank,
            pokemon_id=row["pokemon_id"],
            name_kr=row["name_kr"],
            name_en=row["name_en"],
            primary_type=row["primary_type"],
            secondary_type=row.get("secondary_type"),
            sprite_url=row.get("sprite_url"),
            similarity=float(row["similarity"]),
            reasons=reasons,
        ))

    return MatchResponse(
        top3=top3,
        user_vector=user_vector.tolist(),
    )
