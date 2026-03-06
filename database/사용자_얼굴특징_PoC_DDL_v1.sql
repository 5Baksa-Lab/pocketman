-- =============================================================================
-- Pokeman Project: User_Face_Features DDL (PoC Runtime)
-- 목적: User_Face_Features 실스키마 1:1 컬럼으로 저장/검증
-- 작성일: 2026-03-06
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_face_features (
    -- Meta
    session_id          VARCHAR(50)     PRIMARY KEY,
    image_url           VARCHAR(255)    NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL,

    -- Face shape
    face_aspect_ratio   NUMERIC(5,4)    NOT NULL CHECK (face_aspect_ratio BETWEEN 0.0 AND 1.0),
    jawline_angle       NUMERIC(5,4)    NOT NULL CHECK (jawline_angle BETWEEN 0.0 AND 1.0),
    cheek_width_ratio   NUMERIC(5,4)    NOT NULL CHECK (cheek_width_ratio BETWEEN 0.0 AND 1.0),

    -- Eye / eyebrow
    eye_size_ratio      NUMERIC(5,4)    NOT NULL CHECK (eye_size_ratio BETWEEN 0.0 AND 1.0),
    eye_distance_ratio  NUMERIC(5,4)    NOT NULL CHECK (eye_distance_ratio BETWEEN 0.0 AND 1.0),
    eye_slant_angle     NUMERIC(5,4)    NOT NULL CHECK (eye_slant_angle BETWEEN 0.0 AND 1.0),
    eyebrow_thickness   NUMERIC(5,4)    NOT NULL CHECK (eyebrow_thickness BETWEEN 0.0 AND 1.0),

    -- Nose / mouth
    nose_length_ratio   NUMERIC(5,4)    NOT NULL CHECK (nose_length_ratio BETWEEN 0.0 AND 1.0),
    nose_width_ratio    NUMERIC(5,4)    NOT NULL CHECK (nose_width_ratio BETWEEN 0.0 AND 1.0),
    mouth_width_ratio   NUMERIC(5,4)    NOT NULL CHECK (mouth_width_ratio BETWEEN 0.0 AND 1.0),
    lip_thickness_ratio NUMERIC(5,4)    NOT NULL CHECK (lip_thickness_ratio BETWEEN 0.0 AND 1.0),

    -- Style
    has_glasses         BOOLEAN         NOT NULL DEFAULT FALSE,
    has_facial_hair     BOOLEAN         NOT NULL DEFAULT FALSE,
    has_bangs           BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Color / emotion
    dominant_color      VARCHAR(7)      NOT NULL,
    smile_score         NUMERIC(5,4)    NOT NULL CHECK (smile_score BETWEEN 0.0 AND 1.0),
    emotion_class       VARCHAR(20)     NOT NULL
                        CHECK (emotion_class IN ('기쁨', '무표정', '분노', '신비', '온화', '슬픔', '공포'))
);

CREATE INDEX IF NOT EXISTS idx_user_face_features_created_at
    ON user_face_features (created_at DESC);

COMMENT ON TABLE user_face_features IS '사용자 이미지 특징 추출 결과(User_Face_Features 실스키마)';
