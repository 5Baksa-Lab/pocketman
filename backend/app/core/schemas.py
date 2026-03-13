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

class CreaturePatchRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    is_public: Optional[bool] = None


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


# ── Creature Detail / Like / Comment 스키마 ─────────────────────────────────

class CreatureOwnerInfo(BaseModel):
    id: str
    nickname: str


class CreatureDetailResponse(BaseModel):
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
    primary_type: Optional[str] = None
    secondary_type: Optional[str] = None
    owner: Optional[CreatureOwnerInfo] = None
    like_count: int = 0
    is_liked: bool = False


class LikeResponse(BaseModel):
    like_count: int


class CommentAuthorInfo(BaseModel):
    id: str
    nickname: str


class CommentResponse(BaseModel):
    id: str
    content: str
    author: CommentAuthorInfo
    created_at: datetime
    is_mine: bool


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100)


class MyCreatureItem(BaseModel):
    id: str
    name: str
    is_public: bool
    image_url: Optional[str]
    created_at: datetime
    matched_pokemon_name_kr: Optional[str] = None


class MyCreatureListResponse(BaseModel):
    items: list[MyCreatureItem]
    total: int


# ── User Profile 스키마 ──────────────────────────────────────────────────────

class UserProfileResponse(BaseModel):
    id: str
    email: str
    nickname: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    dark_mode: bool = False
    font_size: int = 16
    creature_count: int = 0
    like_received_count: int = 0


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=50)
    bio: Optional[str] = Field(default=None, max_length=100)
    avatar_creature_id: Optional[str] = None
    dark_mode: Optional[bool] = None
    font_size: Optional[int] = Field(default=None, ge=12, le=24)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=8, max_length=100)


class DeleteAccountRequest(BaseModel):
    password: Optional[str] = None


class NicknameAvailabilityResponse(BaseModel):
    available: bool


# ── Auth 스키마 ──────────────────────────────────────────────────────────────

class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    nickname: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=100)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=100)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    nickname: str
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
