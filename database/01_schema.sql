-- =============================================================================
-- Pokéman Project: DB Schema v2 (기획안 v5 최종확정 기준)
-- 대상: 1~3세대 포켓몬 #001 ~ #386
-- 작성일: 2026-03-08
--
-- 테이블 구성:
--   pokemon_master        기본 정보 (PokeAPI)
--   pokemon_stats         능력치 (PokeAPI)
--   pokemon_visual        시각 특징 10차원 (Gemini Vision 스코어)
--   pokemon_impression    인상 점수 9차원 (규칙 기반 자동 계산)
--   pokemon_type_affinity 타입 친화도 8차원 (룰 기반 자동 계산)
--   pokemon_vectors       28차원 통합 벡터 (pgvector 유사도 검색)
--   user_face_features    사용자 얼굴 특징 (MediaPipe PoC)
--   creatures             사용자 생성 크리처
--   veo_jobs              Veo 영상 생성 작업 상태
--   reactions             크리처 이모지 리액션
--
-- 28차원 벡터 구성:
--   [0-9]   visual 10차원: eye_size, eye_distance, eye_roundness, eye_tail,
--                          face_roundness, face_proportion, feature_size,
--                          feature_emphasis, mouth_curve, overall_symmetry
--   [10-18] impression 9차원: cute, calm, smart, fierce, gentle,
--                             lively, innocent, confident, unique
--   [19-26] type_affinity 8차원: water, fire, grass, electric,
--                                psychic, normal, fighting, ghost
--   [27]    glasses 1차원: 0.0 or 1.0
-- =============================================================================

-- -----------------------------------------------------------------------------
-- EXTENSION
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- 1. pokemon_master — 포켓몬 기본 정보 (PokeAPI 수집)
-- =============================================================================
CREATE TABLE IF NOT EXISTS pokemon_master (
    pokemon_id          SMALLINT        PRIMARY KEY
                            CHECK (pokemon_id BETWEEN 1 AND 386),
    name_kr             VARCHAR(20)     NOT NULL,
    name_en             VARCHAR(30)     NOT NULL,
    name_jp             VARCHAR(20),
    generation          SMALLINT        NOT NULL DEFAULT 1
                            CHECK (generation BETWEEN 1 AND 3),
    pokedex_category    VARCHAR(30),
    primary_type        VARCHAR(10)     NOT NULL,
    secondary_type      VARCHAR(10),
    height_dm           SMALLINT,
    weight_hg           SMALLINT,
    color               VARCHAR(10),
    shape               VARCHAR(20),
    habitat             VARCHAR(20),
    is_legendary        BOOLEAN         NOT NULL DEFAULT FALSE,
    is_mythical         BOOLEAN         NOT NULL DEFAULT FALSE,
    pokedex_text_kr     TEXT,
    sprite_url          TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT now()
);
COMMENT ON TABLE pokemon_master IS '포켓몬 기본 정보 (PokeAPI 배치 수집)';
COMMENT ON COLUMN pokemon_master.generation IS '세대: 1=이상해씨, 2=치코리타, 3=나무지기';

-- =============================================================================
-- 2. pokemon_stats — 포켓몬 능력치 (PokeAPI 수집)
-- =============================================================================
CREATE TABLE IF NOT EXISTS pokemon_stats (
    pokemon_id      SMALLINT    PRIMARY KEY,
    hp              SMALLINT    NOT NULL CHECK (hp BETWEEN 1 AND 255),
    attack          SMALLINT    NOT NULL CHECK (attack BETWEEN 1 AND 255),
    defense         SMALLINT    NOT NULL CHECK (defense BETWEEN 1 AND 255),
    special_attack  SMALLINT    NOT NULL CHECK (special_attack BETWEEN 1 AND 255),
    special_defense SMALLINT    NOT NULL CHECK (special_defense BETWEEN 1 AND 255),
    speed           SMALLINT    NOT NULL CHECK (speed BETWEEN 1 AND 255),
    total_base_stat SMALLINT    GENERATED ALWAYS AS
                        (hp + attack + defense + special_attack + special_defense + speed) STORED,
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);
COMMENT ON TABLE pokemon_stats IS '포켓몬 6개 기본 능력치';

-- =============================================================================
-- 3. pokemon_visual — 시각 특징 10차원 스코어 (Gemini Vision 주석)
--    기획안 v5 §6-3 "Category 1: 시각적 특징 (Visual Features)" 기준
-- =============================================================================
CREATE TABLE IF NOT EXISTS pokemon_visual (
    pokemon_id              SMALLINT        PRIMARY KEY,

    -- 눈 관련 (4차원)
    eye_size_score          NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (eye_size_score BETWEEN 0.0 AND 1.0),
    eye_distance_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (eye_distance_score BETWEEN 0.0 AND 1.0),
    eye_roundness_score     NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (eye_roundness_score BETWEEN 0.0 AND 1.0),
    eye_tail_score          NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (eye_tail_score BETWEEN 0.0 AND 1.0),

    -- 얼굴형 관련 (2차원)
    face_roundness_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (face_roundness_score BETWEEN 0.0 AND 1.0),
    face_proportion_score   NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (face_proportion_score BETWEEN 0.0 AND 1.0),

    -- 이목구비 관련 (2차원)
    feature_size_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (feature_size_score BETWEEN 0.0 AND 1.0),
    feature_emphasis_score  NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (feature_emphasis_score BETWEEN 0.0 AND 1.0),

    -- 입/대칭 (2차원)
    mouth_curve_score       NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (mouth_curve_score BETWEEN 0.0 AND 1.0),
    overall_symmetry        NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                                CHECK (overall_symmetry BETWEEN 0.0 AND 1.0),

    -- 안경 (벡터 27번 차원용)
    has_glasses             BOOLEAN         NOT NULL DEFAULT FALSE,

    -- 메타
    extraction_source       VARCHAR(20)     NOT NULL DEFAULT 'gemini_vision',
    confidence              NUMERIC(3,2),
    reviewed                BOOLEAN         NOT NULL DEFAULT FALSE,
    annotated_at            TIMESTAMPTZ     NOT NULL DEFAULT now(),

    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);
COMMENT ON TABLE pokemon_visual IS '시각 특징 10차원 스코어 (Gemini Vision 주석, 0.0~1.0)';
COMMENT ON COLUMN pokemon_visual.eye_size_score IS '0=작은눈, 1=큰눈';
COMMENT ON COLUMN pokemon_visual.eye_distance_score IS '0=좁은미간, 1=넓은미간';
COMMENT ON COLUMN pokemon_visual.eye_roundness_score IS '0=날카로운눈, 1=둥근눈';
COMMENT ON COLUMN pokemon_visual.eye_tail_score IS '0=처진눈꼬리, 1=올라간눈꼬리';
COMMENT ON COLUMN pokemon_visual.face_roundness_score IS '0=각진얼굴, 1=둥근얼굴';
COMMENT ON COLUMN pokemon_visual.face_proportion_score IS '0=가로형얼굴, 1=세로형얼굴';
COMMENT ON COLUMN pokemon_visual.feature_size_score IS '0=이목구비작음, 1=이목구비큼';
COMMENT ON COLUMN pokemon_visual.feature_emphasis_score IS '0=이목구비약함, 1=이목구비강함';
COMMENT ON COLUMN pokemon_visual.mouth_curve_score IS '0=처진입꼬리, 1=올라간입꼬리(smile)';
COMMENT ON COLUMN pokemon_visual.overall_symmetry IS '0=비대칭, 1=대칭';

-- =============================================================================
-- 4. pokemon_impression — 인상/성격 점수 9차원
--    기획안 v5 §6-4 "Category 2: 인상/성격 점수" 기준
--    입력: pokemon_visual 값 → 규칙 기반 자동 계산 (03_calc_impression.py)
-- =============================================================================
CREATE TABLE IF NOT EXISTS pokemon_impression (
    pokemon_id      SMALLINT        PRIMARY KEY,
    cute_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (cute_score BETWEEN 0.0 AND 1.0),
    calm_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (calm_score BETWEEN 0.0 AND 1.0),
    smart_score     NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (smart_score BETWEEN 0.0 AND 1.0),
    fierce_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (fierce_score BETWEEN 0.0 AND 1.0),
    gentle_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (gentle_score BETWEEN 0.0 AND 1.0),
    lively_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (lively_score BETWEEN 0.0 AND 1.0),
    innocent_score  NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (innocent_score BETWEEN 0.0 AND 1.0),
    confident_score NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (confident_score BETWEEN 0.0 AND 1.0),
    unique_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5
                        CHECK (unique_score BETWEEN 0.0 AND 1.0),
    derivation_note VARCHAR(100),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);
COMMENT ON TABLE pokemon_impression IS '인상/성격 점수 9차원 (visual → 규칙 기반 자동 계산)';

-- =============================================================================
-- 5. pokemon_type_affinity — 타입 친화도 8차원
--    기획안 v5 §6-5 "Category 3: 타입 친화도" 기준
--    입력: pokemon_master.primary_type/secondary_type → 룰 기반 자동 계산
-- =============================================================================
CREATE TABLE IF NOT EXISTS pokemon_type_affinity (
    pokemon_id          SMALLINT        PRIMARY KEY,
    water_affinity      NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (water_affinity BETWEEN 0.0 AND 1.0),
    fire_affinity       NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (fire_affinity BETWEEN 0.0 AND 1.0),
    grass_affinity      NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (grass_affinity BETWEEN 0.0 AND 1.0),
    electric_affinity   NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (electric_affinity BETWEEN 0.0 AND 1.0),
    psychic_affinity    NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (psychic_affinity BETWEEN 0.0 AND 1.0),
    normal_affinity     NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (normal_affinity BETWEEN 0.0 AND 1.0),
    fighting_affinity   NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (fighting_affinity BETWEEN 0.0 AND 1.0),
    ghost_affinity      NUMERIC(4,3)    NOT NULL DEFAULT 0.0
                            CHECK (ghost_affinity BETWEEN 0.0 AND 1.0),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);
COMMENT ON TABLE pokemon_type_affinity IS '타입 친화도 8차원 (룰 기반 자동 계산, 기획안 v5 §6-5)';

-- =============================================================================
-- 6. pokemon_vectors — 28차원 통합 벡터 (pgvector 유사도 검색)
--    입력: pokemon_visual(10) + pokemon_impression(9) + pokemon_type_affinity(8) + glasses(1)
-- =============================================================================
CREATE TABLE IF NOT EXISTS pokemon_vectors (
    pokemon_id      SMALLINT        PRIMARY KEY,
    feature_vector  vector(28)      NOT NULL,
    vector_version  SMALLINT        NOT NULL DEFAULT 1,
    generated_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);

-- IVFFlat 코사인 인덱스 (lists = √386 ≈ 20)
CREATE INDEX IF NOT EXISTS idx_pokemon_vectors_cosine
    ON pokemon_vectors
    USING ivfflat (feature_vector vector_cosine_ops)
    WITH (lists = 20);

COMMENT ON TABLE pokemon_vectors IS '28차원 통합 특징 벡터 (pgvector IVFFlat 코사인 인덱스)';
COMMENT ON COLUMN pokemon_vectors.feature_vector IS
    '[0-9]=visual(10) [10-18]=impression(9) [19-26]=type_affinity(8) [27]=glasses(1)';

-- =============================================================================
-- 7. user_face_features — 사용자 얼굴 특징 (MediaPipe PoC)
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_face_features (
    session_id              VARCHAR(50)     PRIMARY KEY,
    image_url               TEXT            NOT NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),

    -- 얼굴형
    face_aspect_ratio       NUMERIC(5,4)    NOT NULL CHECK (face_aspect_ratio BETWEEN 0.0 AND 1.0),
    jawline_angle           NUMERIC(5,4)    NOT NULL CHECK (jawline_angle BETWEEN 0.0 AND 1.0),
    cheek_width_ratio       NUMERIC(5,4)    NOT NULL CHECK (cheek_width_ratio BETWEEN 0.0 AND 1.0),

    -- 눈
    eye_size_ratio          NUMERIC(5,4)    NOT NULL CHECK (eye_size_ratio BETWEEN 0.0 AND 1.0),
    eye_distance_ratio      NUMERIC(5,4)    NOT NULL CHECK (eye_distance_ratio BETWEEN 0.0 AND 1.0),
    eye_slant_angle         NUMERIC(5,4)    NOT NULL CHECK (eye_slant_angle BETWEEN 0.0 AND 1.0),
    eyebrow_thickness       NUMERIC(5,4)    NOT NULL CHECK (eyebrow_thickness BETWEEN 0.0 AND 1.0),

    -- 코/입
    nose_length_ratio       NUMERIC(5,4)    NOT NULL CHECK (nose_length_ratio BETWEEN 0.0 AND 1.0),
    nose_width_ratio        NUMERIC(5,4)    NOT NULL CHECK (nose_width_ratio BETWEEN 0.0 AND 1.0),
    mouth_width_ratio       NUMERIC(5,4)    NOT NULL CHECK (mouth_width_ratio BETWEEN 0.0 AND 1.0),
    lip_thickness_ratio     NUMERIC(5,4)    NOT NULL CHECK (lip_thickness_ratio BETWEEN 0.0 AND 1.0),

    -- 스타일
    has_glasses             BOOLEAN         NOT NULL DEFAULT FALSE,
    has_facial_hair         BOOLEAN         NOT NULL DEFAULT FALSE,
    has_bangs               BOOLEAN         NOT NULL DEFAULT FALSE,
    dominant_color          VARCHAR(7)      NOT NULL,

    -- 표정/감정
    smile_score             NUMERIC(5,4)    NOT NULL CHECK (smile_score BETWEEN 0.0 AND 1.0),
    emotion_class           VARCHAR(20)     NOT NULL
                            CHECK (emotion_class IN ('기쁨', '무표정', '분노', '신비', '온화', '슬픔', '공포')),

    -- PoC 메타
    poc_status              VARCHAR(20)     DEFAULT 'success'
                            CHECK (poc_status IN ('success', 'failed')),
    poc_error_code          VARCHAR(30),
    poc_quality_score       NUMERIC(5,4)    CHECK (poc_quality_score BETWEEN 0.0 AND 1.0)
);

CREATE INDEX IF NOT EXISTS idx_user_face_features_created_at
    ON user_face_features (created_at DESC);

COMMENT ON TABLE user_face_features IS '사용자 이미지 특징 추출 결과(User_Face_Features 실스키마 + PoC 메타)';

-- =============================================================================
-- 8. creatures — 사용자 생성 크리처
--    기획안 v5 §10-1 ER 기준
-- =============================================================================
CREATE TABLE IF NOT EXISTS creatures (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    matched_pokemon_id  SMALLINT        NOT NULL
                            REFERENCES pokemon_master(pokemon_id) ON DELETE RESTRICT,
    match_rank          SMALLINT        NOT NULL CHECK (match_rank BETWEEN 1 AND 3),
    similarity_score    NUMERIC(5,4)    NOT NULL CHECK (similarity_score BETWEEN 0.0 AND 1.0),
    match_reasons       JSONB           NOT NULL DEFAULT '[]'::jsonb,
    name                VARCHAR(40)     NOT NULL,
    story               TEXT,
    image_url           TEXT,
    video_url           TEXT,
    is_public           BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_creatures_matched_pokemon
    ON creatures (matched_pokemon_id);
CREATE INDEX IF NOT EXISTS idx_creatures_created_at
    ON creatures (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_creatures_public_created
    ON creatures (is_public, created_at DESC);

COMMENT ON TABLE creatures IS '사용자가 선택/생성한 크리처 결과 저장';
COMMENT ON COLUMN creatures.match_reasons IS 'Top-K 매칭 근거 배열(JSON)';

-- =============================================================================
-- 9. veo_jobs — Veo 영상 생성 Job 상태
-- =============================================================================
CREATE TABLE IF NOT EXISTS veo_jobs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id     UUID            NOT NULL
                        REFERENCES creatures(id) ON DELETE CASCADE,
    status          VARCHAR(20)     NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'canceled')),
    video_url       TEXT,
    error_message   TEXT,
    requested_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_veo_jobs_creature_id
    ON veo_jobs (creature_id);
CREATE INDEX IF NOT EXISTS idx_veo_jobs_status
    ON veo_jobs (status);

COMMENT ON TABLE veo_jobs IS 'Veo 영상 생성 비동기 작업 상태 추적';

-- =============================================================================
-- 10. reactions — 이모지 리액션
-- =============================================================================
CREATE TABLE IF NOT EXISTS reactions (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id     UUID            NOT NULL
                        REFERENCES creatures(id) ON DELETE CASCADE,
    emoji_type      VARCHAR(20)     NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reactions_creature_id
    ON reactions (creature_id);
CREATE INDEX IF NOT EXISTS idx_reactions_created_at
    ON reactions (created_at DESC);

COMMENT ON TABLE reactions IS '크리처 피드 이모지 반응 로그';
