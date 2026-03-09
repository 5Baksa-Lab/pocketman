"""
공통 응답/요청 스키마 (기획안 v5 기준)
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str


# ── 매칭 관련 스키마 ────────────────────────────────────────────────────────

class MatchReason(BaseModel):
    dimension: str      # 유사한 차원 이름 (예: "eye_size_score")
    label: str          # 사람이 읽을 수 있는 설명 (예: "큰 눈")
    user_value: float
    pokemon_value: float


class PokemonMatchResult(BaseModel):
    rank: int                       # 1, 2, 3
    pokemon_id: int
    name_kr: str
    name_en: str
    primary_type: str
    secondary_type: Optional[str]
    sprite_url: Optional[str]
    similarity: float               # 코사인 유사도 0.0~1.0
    reasons: list[MatchReason]      # 근거 문장 (최대 3개)


class MatchResponse(BaseModel):
    top3: list[PokemonMatchResult]
    user_vector: list[float]        # 28차원 (디버그용)


# ── 헬스체크 스키마 ──────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    db: str
    pokemon_count: int
    vector_count: int


# ── Creature / Feed / Reaction / Veo 스키마 ─────────────────────────────────

class CreatureCreateRequest(BaseModel):
    matched_pokemon_id: int = Field(ge=1, le=386)
    match_rank: int = Field(ge=1, le=3)
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_reasons: list[dict[str, Any]] = Field(default_factory=list)
    name: str = Field(min_length=1, max_length=40)
    story: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    is_public: bool = False


class CreatureResponse(BaseModel):
    id: str
    matched_pokemon_id: int
    match_rank: int
    similarity_score: float
    match_reasons: list[dict[str, Any]]
    name: str
    story: Optional[str]
    image_url: Optional[str]
    video_url: Optional[str]
    is_public: bool
    created_at: datetime
    matched_pokemon_name_kr: Optional[str] = None


class CreatureListResponse(BaseModel):
    items: list[CreatureResponse]
    limit: int
    offset: int


class ReactionCreateRequest(BaseModel):
    emoji_type: str = Field(min_length=1, max_length=20)


class ReactionResponse(BaseModel):
    id: str
    creature_id: str
    emoji_type: str
    created_at: datetime


class ReactionCountItem(BaseModel):
    emoji_type: str
    count: int


class ReactionSummaryResponse(BaseModel):
    creature_id: str
    counts: list[ReactionCountItem]
    total: int


class VeoJobCreateRequest(BaseModel):
    creature_id: str


class VeoJobUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)
    video_url: Optional[str] = None
    error_message: Optional[str] = None


class VeoJobResponse(BaseModel):
    id: str
    creature_id: str
    status: str
    video_url: Optional[str]
    error_message: Optional[str]
    requested_at: datetime
    updated_at: datetime


# ── 생성 파이프라인 스키마 ───────────────────────────────────────────────────

class GenerationStartRequest(BaseModel):
    regenerate_name_story: bool = True
    regenerate_image: bool = True
    trigger_video: bool = True


class GenerationStepMeta(BaseModel):
    source: str
    used_fallback: bool
    retries: int = 0
    message: Optional[str] = None


class GenerationPipelineResponse(BaseModel):
    creature: CreatureResponse
    veo_job: Optional[VeoJobResponse] = None
    image: GenerationStepMeta
    story: GenerationStepMeta
    video: GenerationStepMeta
