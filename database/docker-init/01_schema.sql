-- =============================================================================
-- Pokéman Docker 초기화: 기본 스키마 (database/01_schema.sql 동일)
-- docker-entrypoint-initdb.d 자동 실행
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. pokemon_master
CREATE TABLE IF NOT EXISTS pokemon_master (
    pokemon_id          SMALLINT        PRIMARY KEY CHECK (pokemon_id BETWEEN 1 AND 386),
    name_kr             VARCHAR(20)     NOT NULL,
    name_en             VARCHAR(30)     NOT NULL,
    name_jp             VARCHAR(20),
    generation          SMALLINT        NOT NULL DEFAULT 1 CHECK (generation BETWEEN 1 AND 3),
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

-- 2. pokemon_stats
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

-- 3. pokemon_visual
CREATE TABLE IF NOT EXISTS pokemon_visual (
    pokemon_id              SMALLINT        PRIMARY KEY,
    eye_size_score          NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (eye_size_score BETWEEN 0.0 AND 1.0),
    eye_distance_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (eye_distance_score BETWEEN 0.0 AND 1.0),
    eye_roundness_score     NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (eye_roundness_score BETWEEN 0.0 AND 1.0),
    eye_tail_score          NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (eye_tail_score BETWEEN 0.0 AND 1.0),
    face_roundness_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (face_roundness_score BETWEEN 0.0 AND 1.0),
    face_proportion_score   NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (face_proportion_score BETWEEN 0.0 AND 1.0),
    feature_size_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (feature_size_score BETWEEN 0.0 AND 1.0),
    feature_emphasis_score  NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (feature_emphasis_score BETWEEN 0.0 AND 1.0),
    mouth_curve_score       NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (mouth_curve_score BETWEEN 0.0 AND 1.0),
    overall_symmetry        NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (overall_symmetry BETWEEN 0.0 AND 1.0),
    has_glasses             BOOLEAN         NOT NULL DEFAULT FALSE,
    extraction_source       VARCHAR(20)     NOT NULL DEFAULT 'gemini_vision',
    confidence              NUMERIC(3,2),
    reviewed                BOOLEAN         NOT NULL DEFAULT FALSE,
    annotated_at            TIMESTAMPTZ     NOT NULL DEFAULT now(),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);

-- 4. pokemon_impression
CREATE TABLE IF NOT EXISTS pokemon_impression (
    pokemon_id      SMALLINT        PRIMARY KEY,
    cute_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (cute_score BETWEEN 0.0 AND 1.0),
    calm_score      NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (calm_score BETWEEN 0.0 AND 1.0),
    smart_score     NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (smart_score BETWEEN 0.0 AND 1.0),
    fierce_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (fierce_score BETWEEN 0.0 AND 1.0),
    gentle_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (gentle_score BETWEEN 0.0 AND 1.0),
    lively_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (lively_score BETWEEN 0.0 AND 1.0),
    innocent_score  NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (innocent_score BETWEEN 0.0 AND 1.0),
    confident_score NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (confident_score BETWEEN 0.0 AND 1.0),
    unique_score    NUMERIC(4,3)    NOT NULL DEFAULT 0.5 CHECK (unique_score BETWEEN 0.0 AND 1.0),
    derivation_note VARCHAR(100),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);

-- 5. pokemon_type_affinity
CREATE TABLE IF NOT EXISTS pokemon_type_affinity (
    pokemon_id          SMALLINT        PRIMARY KEY,
    water_affinity      NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (water_affinity BETWEEN 0.0 AND 1.0),
    fire_affinity       NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (fire_affinity BETWEEN 0.0 AND 1.0),
    grass_affinity      NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (grass_affinity BETWEEN 0.0 AND 1.0),
    electric_affinity   NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (electric_affinity BETWEEN 0.0 AND 1.0),
    psychic_affinity    NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (psychic_affinity BETWEEN 0.0 AND 1.0),
    normal_affinity     NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (normal_affinity BETWEEN 0.0 AND 1.0),
    fighting_affinity   NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (fighting_affinity BETWEEN 0.0 AND 1.0),
    ghost_affinity      NUMERIC(4,3)    NOT NULL DEFAULT 0.0 CHECK (ghost_affinity BETWEEN 0.0 AND 1.0),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);

-- 6. pokemon_vectors
CREATE TABLE IF NOT EXISTS pokemon_vectors (
    pokemon_id      SMALLINT        PRIMARY KEY,
    feature_vector  vector(28)      NOT NULL,
    vector_version  SMALLINT        NOT NULL DEFAULT 1,
    generated_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pokemon_vectors_cosine
    ON pokemon_vectors USING ivfflat (feature_vector vector_cosine_ops) WITH (lists = 20);

-- 7. user_face_features
CREATE TABLE IF NOT EXISTS user_face_features (
    session_id              VARCHAR(50)     PRIMARY KEY,
    image_url               TEXT            NOT NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    face_aspect_ratio       NUMERIC(5,4)    NOT NULL CHECK (face_aspect_ratio BETWEEN 0.0 AND 1.0),
    jawline_angle           NUMERIC(5,4)    NOT NULL CHECK (jawline_angle BETWEEN 0.0 AND 1.0),
    cheek_width_ratio       NUMERIC(5,4)    NOT NULL CHECK (cheek_width_ratio BETWEEN 0.0 AND 1.0),
    eye_size_ratio          NUMERIC(5,4)    NOT NULL CHECK (eye_size_ratio BETWEEN 0.0 AND 1.0),
    eye_distance_ratio      NUMERIC(5,4)    NOT NULL CHECK (eye_distance_ratio BETWEEN 0.0 AND 1.0),
    eye_slant_angle         NUMERIC(5,4)    NOT NULL CHECK (eye_slant_angle BETWEEN 0.0 AND 1.0),
    eyebrow_thickness       NUMERIC(5,4)    NOT NULL CHECK (eyebrow_thickness BETWEEN 0.0 AND 1.0),
    nose_length_ratio       NUMERIC(5,4)    NOT NULL CHECK (nose_length_ratio BETWEEN 0.0 AND 1.0),
    nose_width_ratio        NUMERIC(5,4)    NOT NULL CHECK (nose_width_ratio BETWEEN 0.0 AND 1.0),
    mouth_width_ratio       NUMERIC(5,4)    NOT NULL CHECK (mouth_width_ratio BETWEEN 0.0 AND 1.0),
    lip_thickness_ratio     NUMERIC(5,4)    NOT NULL CHECK (lip_thickness_ratio BETWEEN 0.0 AND 1.0),
    has_glasses             BOOLEAN         NOT NULL DEFAULT FALSE,
    has_facial_hair         BOOLEAN         NOT NULL DEFAULT FALSE,
    has_bangs               BOOLEAN         NOT NULL DEFAULT FALSE,
    dominant_color          VARCHAR(7)      NOT NULL,
    smile_score             NUMERIC(5,4)    NOT NULL CHECK (smile_score BETWEEN 0.0 AND 1.0),
    emotion_class           VARCHAR(20)     NOT NULL CHECK (emotion_class IN ('기쁨', '무표정', '분노', '신비', '온화', '슬픔', '공포')),
    poc_status              VARCHAR(20)     DEFAULT 'success' CHECK (poc_status IN ('success', 'failed')),
    poc_error_code          VARCHAR(30),
    poc_quality_score       NUMERIC(5,4)    CHECK (poc_quality_score BETWEEN 0.0 AND 1.0)
);
CREATE INDEX IF NOT EXISTS idx_user_face_features_created_at ON user_face_features (created_at DESC);

-- 8. creatures
CREATE TABLE IF NOT EXISTS creatures (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    matched_pokemon_id  SMALLINT        NOT NULL REFERENCES pokemon_master(pokemon_id) ON DELETE RESTRICT,
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
CREATE INDEX IF NOT EXISTS idx_creatures_matched_pokemon ON creatures (matched_pokemon_id);
CREATE INDEX IF NOT EXISTS idx_creatures_created_at ON creatures (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_creatures_public_created ON creatures (is_public, created_at DESC);

-- 9. veo_jobs
CREATE TABLE IF NOT EXISTS veo_jobs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id     UUID            NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    status          VARCHAR(20)     NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'canceled')),
    video_url       TEXT,
    error_message   TEXT,
    requested_at    TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_veo_jobs_creature_id ON veo_jobs (creature_id);
CREATE INDEX IF NOT EXISTS idx_veo_jobs_status ON veo_jobs (status);

-- 10. reactions
CREATE TABLE IF NOT EXISTS reactions (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id     UUID            NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    emoji_type      VARCHAR(20)     NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reactions_creature_id ON reactions (creature_id);
CREATE INDEX IF NOT EXISTS idx_reactions_created_at ON reactions (created_at DESC);
