-- =============================================================================
-- Pokéman Project: Gen 1 Pokemon Face Feature DB DDL
-- 대상: 1세대 포켓몬 #001 ~ #151
-- 기준: 사람_얼굴특징_DB_스키마_v1.md 와 동일한 필드 구조 적용
-- 작성일: 2026-03-06
-- =============================================================================


-- -----------------------------------------------------------------------------
-- EXTENSION
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";     -- pgvector (유사도 검색)


-- =============================================================================
-- 1. 포켓몬 기본 정보 (pokemon_master)
--    PokeAPI 에서 수집하는 구조적 메타데이터
-- =============================================================================
CREATE TABLE pokemon_master (
    -- PK / 식별
    pokemon_id          SMALLINT        PRIMARY KEY,            -- 전국도감 번호 (1~151)
    name_kr             VARCHAR(20)     NOT NULL,               -- 한국어 이름
    name_en             VARCHAR(30)     NOT NULL,               -- 영문 이름
    name_jp             VARCHAR(20),                            -- 일본어 이름

    -- 세대 / 분류
    generation          SMALLINT        NOT NULL DEFAULT 1,     -- 1세대 고정
    pokedex_category    VARCHAR(30),                            -- 도감 분류 (예: "씨앗 포켓몬")

    -- 타입
    primary_type        VARCHAR(10)     NOT NULL,               -- 1번 타입
    secondary_type      VARCHAR(10),                            -- 2번 타입 (없으면 NULL)

    -- 신체 정보 (PokeAPI)
    height_dm           SMALLINT,                               -- 키 (데시미터)
    weight_hg           SMALLINT,                               -- 무게 (헥토그램)

    -- 도감 분류 속성 (PokeAPI species)
    color               VARCHAR(10),    -- red/blue/yellow/green/black/brown/purple/gray/white/pink
    shape               VARCHAR(20),    -- quadruped/upright/wings/squiggle/fish/blob/...
    habitat             VARCHAR(20),    -- cave/forest/grassland/mountain/rare/rough-terrain/sea/urban/waters-edge

    -- 특수 분류
    is_legendary        BOOLEAN         NOT NULL DEFAULT FALSE,
    is_mythical         BOOLEAN         NOT NULL DEFAULT FALSE,

    -- 도감 설명
    pokedex_text_kr     TEXT,                                   -- 한국어 도감 설명
    sprite_url          TEXT,                                   -- PokeAPI front_default 스프라이트 URL

    -- 메타
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- 제약
    CONSTRAINT chk_generation       CHECK (generation = 1),
    CONSTRAINT chk_pokemon_id_range CHECK (pokemon_id BETWEEN 1 AND 151)
);

COMMENT ON TABLE  pokemon_master                IS '1세대 포켓몬 기본 정보 (PokeAPI 수집)';
COMMENT ON COLUMN pokemon_master.pokemon_id     IS '전국도감 번호 (1~151)';
COMMENT ON COLUMN pokemon_master.color          IS 'PokeAPI species.color: red/blue/yellow/green/black/brown/purple/gray/white/pink';
COMMENT ON COLUMN pokemon_master.shape          IS 'PokeAPI species.shape: quadruped/upright/wings/squiggle/fish/blob/humanoid/heads/tentacles/armor/legs/arms/oval/serpentine';


-- =============================================================================
-- 2. 포켓몬 종족치 (pokemon_stats)
--    매핑 시 사람의 얼굴 특징 → 포켓몬 스탯 친화도 계산에 활용
-- =============================================================================
CREATE TABLE pokemon_stats (
    pokemon_id          SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    hp                  SMALLINT        NOT NULL CHECK (hp          BETWEEN 1 AND 255),
    attack              SMALLINT        NOT NULL CHECK (attack       BETWEEN 1 AND 255),
    defense             SMALLINT        NOT NULL CHECK (defense      BETWEEN 1 AND 255),
    special_attack      SMALLINT        NOT NULL CHECK (special_attack  BETWEEN 1 AND 255),
    special_defense     SMALLINT        NOT NULL CHECK (special_defense BETWEEN 1 AND 255),
    speed               SMALLINT        NOT NULL CHECK (speed        BETWEEN 1 AND 255),

    -- 파생 집계
    total_base_stat     SMALLINT GENERATED ALWAYS AS
                            (hp + attack + defense + special_attack + special_defense + speed)
                        STORED
);

COMMENT ON TABLE  pokemon_stats              IS '1세대 포켓몬 종족치 (Base Stats)';
COMMENT ON COLUMN pokemon_stats.total_base_stat IS '6개 종족치 합계 (자동 계산)';


-- =============================================================================
-- 3. 얼굴형 특징 (pokemon_face_shape)
--    [추출: Gemini Vision API 배치]
--    ↔ User_Face_Features.face_aspect_ratio / jawline_angle
-- =============================================================================
CREATE TABLE pokemon_face_shape (
    pokemon_id          SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    -- ↔ face_aspect_ratio: 얼굴/두부 가로÷세로 비율
    --    0.0 = 매우 세로형(뱀,벌레류)  1.0 = 매우 가로형/둥글(잠만보,푸린류)
    face_aspect_ratio   NUMERIC(3,2)    NOT NULL CHECK (face_aspect_ratio BETWEEN 0.0 AND 1.0),

    -- ↔ jawline_angle: 하턱/주둥이 곡선
    --    0.0 = 뾰족한 V라인  1.0 = 둥근 U라인
    jawline_angle       NUMERIC(3,2)    NOT NULL CHECK (jawline_angle BETWEEN 0.0 AND 1.0),

    extraction_source   VARCHAR(30)     NOT NULL DEFAULT 'gemini_vision',
    confidence          NUMERIC(3,2)    CHECK (confidence BETWEEN 0.0 AND 1.0),
    reviewed            BOOLEAN         NOT NULL DEFAULT FALSE   -- 수동 검수 완료 여부
);

COMMENT ON TABLE  pokemon_face_shape                    IS '포켓몬 얼굴형 데이터 (Gemini Vision 추출)';
COMMENT ON COLUMN pokemon_face_shape.face_aspect_ratio  IS '두부 가로/세로 비율: 0=세로형, 1=가로형/둥글';
COMMENT ON COLUMN pokemon_face_shape.jawline_angle      IS '하턱 곡선: 0=뾰족(V), 1=둥글(U)';


-- =============================================================================
-- 4. 눈 특징 (pokemon_eye_features)
--    [추출: Gemini Vision API 배치]
--    ↔ User_Face_Features: eye_size_ratio / eye_distance_ratio / eye_slant_angle
-- =============================================================================
CREATE TABLE pokemon_eye_features (
    pokemon_id          SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    -- ↔ eye_size_ratio: 눈 크기 / 얼굴 크기 상대 비율
    --    0.0 = 눈 없음(주뱃 구버전)  1.0 = 매우 큰 눈(푸린,왕눈해)
    eye_size_ratio      NUMERIC(3,2)    NOT NULL CHECK (eye_size_ratio      BETWEEN 0.0 AND 1.0),

    -- ↔ eye_distance_ratio: 양눈 중심 간 거리 / 얼굴 가로
    --    0.0 = 매우 붙어있음  1.0 = 매우 넓음
    eye_distance_ratio  NUMERIC(3,2)    NOT NULL CHECK (eye_distance_ratio  BETWEEN 0.0 AND 1.0),

    -- ↔ eye_slant_angle: 눈꼬리 기울기
    --    0.0 = 매우 처짐(강아지상/온화)  0.5 = 수평  1.0 = 매우 올라감(고양이상/공격적)
    eye_slant_angle     NUMERIC(3,2)    NOT NULL CHECK (eye_slant_angle     BETWEEN 0.0 AND 1.0),

    -- 예외 처리 메모
    eye_note            VARCHAR(50),    -- 예: 'compound_eyes', 'no_eyes', 'full_body_eye'

    extraction_source   VARCHAR(30)     NOT NULL DEFAULT 'gemini_vision',
    confidence          NUMERIC(3,2)    CHECK (confidence BETWEEN 0.0 AND 1.0),
    reviewed            BOOLEAN         NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE  pokemon_eye_features                  IS '포켓몬 눈 특징 데이터 (Gemini Vision 추출)';
COMMENT ON COLUMN pokemon_eye_features.eye_slant_angle  IS '0=처짐(온화), 0.5=수평, 1=올라감(공격적)';
COMMENT ON COLUMN pokemon_eye_features.eye_note         IS '특수 눈 케이스 메모: no_eyes / compound_eyes / full_body_eye';


-- =============================================================================
-- 5. 코/입 특징 (pokemon_nose_mouth_features)
--    [추출: Gemini Vision API 배치]
--    ↔ User_Face_Features: nose_length_ratio ~ philtrum_ratio
--
--    주의: 비인간형 포켓몬의 경우 anatomical analog(해부학적 유사부위) 기준 측정
--          코/주둥이 없는 포켓몬: nose_* = 0.1 고정
--          인중 구조 없는 포켓몬: philtrum_ratio = 0.1 고정
-- =============================================================================
CREATE TABLE pokemon_nose_mouth_features (
    pokemon_id              SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    -- ↔ nose_length_ratio: 코/주둥이 돌출 길이 / 얼굴 세로
    --    0.0 = 없음  1.0 = 매우 긺(주둥이 긴 포켓몬)
    nose_length_ratio       NUMERIC(3,2)    NOT NULL CHECK (nose_length_ratio    BETWEEN 0.0 AND 1.0),

    -- ↔ nose_width_ratio: 코볼/콧구멍 너비 / 얼굴 가로
    --    0.0 = 없음  1.0 = 매우 넓음
    nose_width_ratio        NUMERIC(3,2)    NOT NULL CHECK (nose_width_ratio     BETWEEN 0.0 AND 1.0),

    -- ↔ mouth_width_ratio: 입(부리/주둥이) 너비 / 얼굴 가로
    --    0.0 = 매우 작음  1.0 = 매우 큼(입이 몸 전체인 포켓몬)
    mouth_width_ratio       NUMERIC(3,2)    NOT NULL CHECK (mouth_width_ratio    BETWEEN 0.0 AND 1.0),

    -- ↔ lip_thickness_ratio: 입술/입 두께감
    --    0.0 = 선 형태(얇음)  1.0 = 매우 두꺼운 입술
    lip_thickness_ratio     NUMERIC(3,2)    NOT NULL CHECK (lip_thickness_ratio  BETWEEN 0.0 AND 1.0),

    -- ↔ philtrum_ratio: 코 하단~입 상단 거리 비율
    --    비인간형 포켓몬 = 0.1 고정
    philtrum_ratio          NUMERIC(3,2)    NOT NULL DEFAULT 0.10
                                            CHECK (philtrum_ratio BETWEEN 0.0 AND 1.0),

    -- 예외 처리 플래그
    is_humanoid             BOOLEAN         NOT NULL DEFAULT FALSE,  -- 인간형 여부 (philtrum 측정 유효)
    mouth_note              VARCHAR(50),    -- 예: 'beak', 'no_mouth', 'full_body_mouth'

    extraction_source       VARCHAR(30)     NOT NULL DEFAULT 'gemini_vision',
    confidence              NUMERIC(3,2)    CHECK (confidence BETWEEN 0.0 AND 1.0),
    reviewed                BOOLEAN         NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE  pokemon_nose_mouth_features               IS '포켓몬 코/입 특징 데이터 (Gemini Vision 추출)';
COMMENT ON COLUMN pokemon_nose_mouth_features.philtrum_ratio    IS '비인간형=0.1 고정값. is_humanoid=TRUE일 때만 유효';
COMMENT ON COLUMN pokemon_nose_mouth_features.is_humanoid       IS '인간형 포켓몬 여부 (루주라, 괴력몬 등)';


-- =============================================================================
-- 6. 스타일/부가 특징 (pokemon_style_features)
--    [추출: Gemini Vision API - Boolean 판단]
--    ↔ User_Face_Features: has_glasses / has_facial_hair / has_bangs
-- =============================================================================
CREATE TABLE pokemon_style_features (
    pokemon_id          SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    -- ↔ has_glasses: 안경/눈테 유사 디자인 요소 보유 여부
    has_glasses         BOOLEAN         NOT NULL DEFAULT FALSE,

    -- ↔ has_facial_hair: 수염/콧수염/갈기/수염털 유사 요소 보유 여부
    --    예: 나옹(수염), 성원숭(얼굴 털), 시라소몬
    has_facial_hair     BOOLEAN         NOT NULL DEFAULT FALSE,

    -- ↔ has_bangs: 두부 전면을 덮는 털/잎/갈기/뿔 등 유무
    --    예: 가디(머리털), 식스테일(꽃무늬), 뚜벅쵸(잎)
    has_bangs           BOOLEAN         NOT NULL DEFAULT FALSE,

    -- 근거 메모 (검수/디버깅용)
    glasses_note        VARCHAR(60),    -- 예: 'ring_pattern_around_eyes'
    facial_hair_note    VARCHAR(60),    -- 예: 'whiskers', 'mane', 'beard_shape_marking'
    bangs_note          VARCHAR(60),    -- 예: 'leaf_on_head', 'long_forehead_fur'

    extraction_source   VARCHAR(30)     NOT NULL DEFAULT 'gemini_vision',
    reviewed            BOOLEAN         NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE  pokemon_style_features                IS '포켓몬 스타일/부가 특징 (Gemini Vision Boolean 추출)';
COMMENT ON COLUMN pokemon_style_features.has_glasses    IS '안경/눈테 형태 디자인 보유 여부 (패턴 포함)';
COMMENT ON COLUMN pokemon_style_features.has_facial_hair IS '수염/갈기/콧수염 유사 디자인 요소 보유 여부';
COMMENT ON COLUMN pokemon_style_features.has_bangs      IS '두부 전면 덮는 털/잎/갈기 보유 여부';


-- =============================================================================
-- 7. 감정/성격 특징 (pokemon_emotion_features)
--    [추출: Gemini Vision (smile_score) + Gemini Flash 텍스트 분류 (emotion/personality)]
--    ↔ User_Face_Features: smile_score / emotion_class / personality_class
-- =============================================================================
CREATE TABLE pokemon_emotion_features (
    pokemon_id          SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    -- ↔ smile_score: 스프라이트 표정의 웃음 정도
    --    0.0 = 찌푸림/화남  0.5 = 무표정  1.0 = 환한 미소
    smile_score         NUMERIC(3,2)    NOT NULL CHECK (smile_score BETWEEN 0.0 AND 1.0),

    -- ↔ emotion_class: 스프라이트 인상 기반 분류
    emotion_class       VARCHAR(20)     NOT NULL
                        CHECK (emotion_class IN (
                            '기쁨', '무표정', '분노', '신비', '온화', '슬픔', '공포'
                        )),

    -- ↔ personality_class: 도감 설명 + 타입 기반 성격 키워드 (최대 4개, 쉼표 구분)
    --    키워드 풀: 용감한/온화한/조심스러운/명랑한/냉정한/건방진/고집스러운/
    --               느긋한/개구쟁이/뻔뻔한/호기심많은/외로움을타는/수줍은/사나운/신중한/충성스러운
    personality_class   VARCHAR(80)     NOT NULL,

    extraction_source   VARCHAR(30)     NOT NULL DEFAULT 'gemini_flash_text',
    reviewed            BOOLEAN         NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE  pokemon_emotion_features                  IS '포켓몬 감정/성격 특징 (Gemini Vision + Flash 추출)';
COMMENT ON COLUMN pokemon_emotion_features.emotion_class    IS '기쁨/무표정/분노/신비/온화/슬픔/공포 중 1개';
COMMENT ON COLUMN pokemon_emotion_features.personality_class IS '성격 키워드 최대 4개 쉼표 구분 저장. 예: "용감한,명랑한,개구쟁이"';


-- =============================================================================
-- 8. 통합 벡터 (pokemon_feature_vectors)
--    [생성: 위 6개 테이블 값 조합 후 정규화]
--    pgvector 코사인 유사도 검색 대상
--
--    벡터 구성 (28차원):
--      [0]  face_aspect_ratio
--      [1]  jawline_angle
--      [2]  eye_size_ratio
--      [3]  eye_distance_ratio
--      [4]  eye_slant_angle
--      [5]  nose_length_ratio
--      [6]  nose_width_ratio
--      [7]  mouth_width_ratio
--      [8]  lip_thickness_ratio
--      [9]  philtrum_ratio
--      [10] has_glasses (0.0 or 1.0)
--      [11] has_facial_hair (0.0 or 1.0)
--      [12] has_bangs (0.0 or 1.0)
--      [13] smile_score
--      [14] cute_score      (인상 - impression 레이어)
--      [15] calm_score
--      [16] smart_score
--      [17] fierce_score
--      [18] gentle_score
--      [19] lively_score
--      [20] innocent_score
--      [21] confident_score
--      [22] unique_score
--      [23] water_affinity  (타입 친화도 레이어)
--      [24] fire_affinity
--      [25] grass_affinity
--      [26] electric_affinity
--      [27] psychic_affinity
-- =============================================================================
CREATE TABLE pokemon_feature_vectors (
    pokemon_id          SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,
    feature_vector      vector(28)      NOT NULL,
    vector_version      SMALLINT        NOT NULL DEFAULT 1,     -- 벡터 스키마 버전 관리
    generated_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 코사인 유사도 검색 인덱스 (IVFFlat)
-- lists 파라미터: sqrt(151) ≒ 12  (포켓몬 수의 제곱근)
CREATE INDEX idx_pokemon_vectors_cosine
    ON pokemon_feature_vectors
    USING ivfflat (feature_vector vector_cosine_ops)
    WITH (lists = 12);

COMMENT ON TABLE  pokemon_feature_vectors               IS '포켓몬 28차원 통합 특징 벡터 (pgvector 유사도 검색용)';
COMMENT ON COLUMN pokemon_feature_vectors.feature_vector IS '28차원 정규화 벡터. 차원 구성은 위 주석 참조';
COMMENT ON COLUMN pokemon_feature_vectors.vector_version IS '벡터 스키마가 변경될 경우 버전 증가 후 전체 재생성';


-- =============================================================================
-- 9. 인상 스코어 (pokemon_impression_scores)
--    [생성: pokemon_face_shape + eye + emotion 값 → 가중치 공식 자동 계산]
--    사람의 인상 점수와 동일한 차원으로 매핑하기 위한 중간 레이어
-- =============================================================================
CREATE TABLE pokemon_impression_scores (
    pokemon_id          SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    -- 9개 인상 차원 (0.0~1.0)
    cute_score          NUMERIC(3,2)    NOT NULL CHECK (cute_score      BETWEEN 0.0 AND 1.0),
    calm_score          NUMERIC(3,2)    NOT NULL CHECK (calm_score      BETWEEN 0.0 AND 1.0),
    smart_score         NUMERIC(3,2)    NOT NULL CHECK (smart_score     BETWEEN 0.0 AND 1.0),
    fierce_score        NUMERIC(3,2)    NOT NULL CHECK (fierce_score    BETWEEN 0.0 AND 1.0),
    gentle_score        NUMERIC(3,2)    NOT NULL CHECK (gentle_score    BETWEEN 0.0 AND 1.0),
    lively_score        NUMERIC(3,2)    NOT NULL CHECK (lively_score    BETWEEN 0.0 AND 1.0),
    innocent_score      NUMERIC(3,2)    NOT NULL CHECK (innocent_score  BETWEEN 0.0 AND 1.0),
    confident_score     NUMERIC(3,2)    NOT NULL CHECK (confident_score BETWEEN 0.0 AND 1.0),
    unique_score        NUMERIC(3,2)    NOT NULL CHECK (unique_score    BETWEEN 0.0 AND 1.0),

    -- 산출 방식 메모
    derivation_note     VARCHAR(100)    -- 예: 'auto_from_face+emotion+type' / 'manual_override'
);

COMMENT ON TABLE  pokemon_impression_scores IS '포켓몬 인상 점수 (얼굴특징 + 감정 + 타입 기반 자동 계산)';


-- =============================================================================
-- 10. 타입 친화도 (pokemon_type_affinity)
--     [생성: primary_type / secondary_type → TYPE_TO_AFFINITY 룰 테이블 자동 계산]
-- =============================================================================
CREATE TABLE pokemon_type_affinity (
    pokemon_id              SMALLINT        PRIMARY KEY REFERENCES pokemon_master(pokemon_id) ON DELETE CASCADE,

    water_affinity          NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (water_affinity      BETWEEN 0.0 AND 1.0),
    fire_affinity           NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (fire_affinity        BETWEEN 0.0 AND 1.0),
    grass_affinity          NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (grass_affinity       BETWEEN 0.0 AND 1.0),
    electric_affinity       NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (electric_affinity    BETWEEN 0.0 AND 1.0),
    psychic_affinity        NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (psychic_affinity     BETWEEN 0.0 AND 1.0),
    normal_affinity         NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (normal_affinity      BETWEEN 0.0 AND 1.0),
    fighting_affinity       NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (fighting_affinity    BETWEEN 0.0 AND 1.0),
    ghost_affinity          NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (ghost_affinity       BETWEEN 0.0 AND 1.0),
    ice_affinity            NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (ice_affinity         BETWEEN 0.0 AND 1.0),
    ground_affinity         NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (ground_affinity      BETWEEN 0.0 AND 1.0),
    rock_affinity           NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (rock_affinity        BETWEEN 0.0 AND 1.0),
    poison_affinity         NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (poison_affinity      BETWEEN 0.0 AND 1.0),
    dragon_affinity         NUMERIC(3,2)    NOT NULL DEFAULT 0.0 CHECK (dragon_affinity      BETWEEN 0.0 AND 1.0)
);

COMMENT ON TABLE  pokemon_type_affinity IS '포켓몬 타입 친화도 (TYPE_TO_AFFINITY 룰 기반 자동 계산)';


-- =============================================================================
-- 11. 배치 작업 로그 (pokemon_annotation_log)
--     Gemini Vision / Flash 배치 실행 이력 추적
-- =============================================================================
CREATE TABLE pokemon_annotation_log (
    log_id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    pokemon_id          SMALLINT        NOT NULL REFERENCES pokemon_master(pokemon_id),
    batch_type          VARCHAR(30)     NOT NULL,   -- 'gemini_vision' / 'gemini_flash_text'
    status              VARCHAR(20)     NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'success', 'failed', 'manual_override')),
    raw_response        JSONB,                      -- API 원본 응답 저장 (디버깅용)
    error_message       TEXT,
    executed_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    model_version       VARCHAR(40)                -- 예: 'gemini-1.5-flash-002'
);

CREATE INDEX idx_annotation_log_pokemon ON pokemon_annotation_log(pokemon_id);
CREATE INDEX idx_annotation_log_status  ON pokemon_annotation_log(status);

COMMENT ON TABLE  pokemon_annotation_log            IS 'Gemini 배치 주석 실행 이력 및 디버깅 로그';
COMMENT ON COLUMN pokemon_annotation_log.raw_response IS 'API 원본 JSON 응답 저장. 검수/재처리 시 활용';


-- =============================================================================
-- 12. 검수 플래그 뷰 (v_pokemon_review_needed)
--     reviewed = FALSE 이거나 confidence < 0.7 인 레코드 추적
-- =============================================================================
CREATE VIEW v_pokemon_review_needed AS
SELECT
    m.pokemon_id,
    m.name_kr,
    m.name_en,
    m.primary_type,
    CASE WHEN fs.reviewed = FALSE  THEN TRUE ELSE FALSE END AS face_shape_needs_review,
    CASE WHEN ey.reviewed = FALSE  THEN TRUE ELSE FALSE END AS eye_needs_review,
    CASE WHEN nm.reviewed = FALSE  THEN TRUE ELSE FALSE END AS nose_mouth_needs_review,
    CASE WHEN st.reviewed = FALSE  THEN TRUE ELSE FALSE END AS style_needs_review,
    CASE WHEN em.reviewed = FALSE  THEN TRUE ELSE FALSE END AS emotion_needs_review,
    COALESCE(fs.confidence, 0) AS face_confidence,
    COALESCE(ey.confidence, 0) AS eye_confidence,
    COALESCE(nm.confidence, 0) AS nose_mouth_confidence
FROM pokemon_master m
LEFT JOIN pokemon_face_shape            fs ON m.pokemon_id = fs.pokemon_id
LEFT JOIN pokemon_eye_features          ey ON m.pokemon_id = ey.pokemon_id
LEFT JOIN pokemon_nose_mouth_features   nm ON m.pokemon_id = nm.pokemon_id
LEFT JOIN pokemon_style_features        st ON m.pokemon_id = st.pokemon_id
LEFT JOIN pokemon_emotion_features      em ON m.pokemon_id = em.pokemon_id
WHERE
    fs.reviewed = FALSE OR ey.reviewed = FALSE
    OR nm.reviewed = FALSE OR st.reviewed = FALSE
    OR em.reviewed = FALSE
    OR COALESCE(fs.confidence, 0) < 0.70
    OR COALESCE(ey.confidence, 0) < 0.70
    OR COALESCE(nm.confidence, 0) < 0.70;

COMMENT ON VIEW v_pokemon_review_needed IS '수동 검수가 필요한 포켓몬 목록 (reviewed=FALSE 또는 confidence<0.7)';


-- =============================================================================
-- 13. 커버리지 체크 뷰 (v_pokemon_coverage)
--     151마리 전체 데이터 완성도 확인
-- =============================================================================
CREATE VIEW v_pokemon_coverage AS
SELECT
    m.pokemon_id,
    m.name_kr,
    (fs.pokemon_id IS NOT NULL)  AS has_face_shape,
    (ey.pokemon_id IS NOT NULL)  AS has_eye,
    (nm.pokemon_id IS NOT NULL)  AS has_nose_mouth,
    (st.pokemon_id IS NOT NULL)  AS has_style,
    (em.pokemon_id IS NOT NULL)  AS has_emotion,
    (im.pokemon_id IS NOT NULL)  AS has_impression,
    (ta.pokemon_id IS NOT NULL)  AS has_type_affinity,
    (fv.pokemon_id IS NOT NULL)  AS has_vector,
    -- 전체 완성 여부
    (
        fs.pokemon_id IS NOT NULL AND ey.pokemon_id IS NOT NULL
        AND nm.pokemon_id IS NOT NULL AND st.pokemon_id IS NOT NULL
        AND em.pokemon_id IS NOT NULL AND im.pokemon_id IS NOT NULL
        AND ta.pokemon_id IS NOT NULL AND fv.pokemon_id IS NOT NULL
    ) AS is_complete
FROM pokemon_master m
LEFT JOIN pokemon_face_shape            fs ON m.pokemon_id = fs.pokemon_id
LEFT JOIN pokemon_eye_features          ey ON m.pokemon_id = ey.pokemon_id
LEFT JOIN pokemon_nose_mouth_features   nm ON m.pokemon_id = nm.pokemon_id
LEFT JOIN pokemon_style_features        st ON m.pokemon_id = st.pokemon_id
LEFT JOIN pokemon_emotion_features      em ON m.pokemon_id = em.pokemon_id
LEFT JOIN pokemon_impression_scores     im ON m.pokemon_id = im.pokemon_id
LEFT JOIN pokemon_type_affinity         ta ON m.pokemon_id = ta.pokemon_id
LEFT JOIN pokemon_feature_vectors       fv ON m.pokemon_id = fv.pokemon_id
ORDER BY m.pokemon_id;

COMMENT ON VIEW v_pokemon_coverage IS '포켓몬 DB 구축 완성도 확인용 뷰 (151마리 커버리지)';


-- =============================================================================
-- 14. 유용한 조회 함수
-- =============================================================================

-- 포켓몬 전체 특징 통합 조회
CREATE OR REPLACE FUNCTION get_pokemon_full_profile(p_pokemon_id SMALLINT)
RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
    SELECT jsonb_build_object(
        'pokemon_id',   m.pokemon_id,
        'name_kr',      m.name_kr,
        'name_en',      m.name_en,
        'type',         jsonb_build_object('primary', m.primary_type, 'secondary', m.secondary_type),
        'face_shape',   jsonb_build_object(
                            'face_aspect_ratio', fs.face_aspect_ratio,
                            'jawline_angle',     fs.jawline_angle),
        'eye',          jsonb_build_object(
                            'eye_size_ratio',     ey.eye_size_ratio,
                            'eye_distance_ratio', ey.eye_distance_ratio,
                            'eye_slant_angle',    ey.eye_slant_angle),
        'nose_mouth',   jsonb_build_object(
                            'nose_length_ratio',  nm.nose_length_ratio,
                            'nose_width_ratio',   nm.nose_width_ratio,
                            'mouth_width_ratio',  nm.mouth_width_ratio,
                            'lip_thickness_ratio',nm.lip_thickness_ratio,
                            'philtrum_ratio',     nm.philtrum_ratio),
        'style',        jsonb_build_object(
                            'has_glasses',        st.has_glasses,
                            'has_facial_hair',    st.has_facial_hair,
                            'has_bangs',          st.has_bangs),
        'emotion',      jsonb_build_object(
                            'smile_score',        em.smile_score,
                            'emotion_class',      em.emotion_class,
                            'personality_class',  em.personality_class),
        'impression',   jsonb_build_object(
                            'cute',      im.cute_score,
                            'calm',      im.calm_score,
                            'smart',     im.smart_score,
                            'fierce',    im.fierce_score,
                            'gentle',    im.gentle_score,
                            'lively',    im.lively_score,
                            'innocent',  im.innocent_score,
                            'confident', im.confident_score,
                            'unique',    im.unique_score),
        'feature_vector', fv.feature_vector::TEXT
    )
    FROM pokemon_master m
    LEFT JOIN pokemon_face_shape            fs ON m.pokemon_id = fs.pokemon_id
    LEFT JOIN pokemon_eye_features          ey ON m.pokemon_id = ey.pokemon_id
    LEFT JOIN pokemon_nose_mouth_features   nm ON m.pokemon_id = nm.pokemon_id
    LEFT JOIN pokemon_style_features        st ON m.pokemon_id = st.pokemon_id
    LEFT JOIN pokemon_emotion_features      em ON m.pokemon_id = em.pokemon_id
    LEFT JOIN pokemon_impression_scores     im ON m.pokemon_id = im.pokemon_id
    LEFT JOIN pokemon_feature_vectors       fv ON m.pokemon_id = fv.pokemon_id
    WHERE m.pokemon_id = p_pokemon_id;
$$;

COMMENT ON FUNCTION get_pokemon_full_profile IS '포켓몬 전체 특징 JSONB 통합 조회';


-- =============================================================================
-- 15. 테이블 생성 순서 요약 (의존성 순서)
-- =============================================================================
-- 1. pokemon_master          (기준 테이블, FK 없음)
-- 2. pokemon_stats           (FK → pokemon_master)
-- 3. pokemon_face_shape      (FK → pokemon_master)
-- 4. pokemon_eye_features    (FK → pokemon_master)
-- 5. pokemon_nose_mouth_features (FK → pokemon_master)
-- 6. pokemon_style_features  (FK → pokemon_master)
-- 7. pokemon_emotion_features(FK → pokemon_master)
-- 8. pokemon_impression_scores (FK → pokemon_master)
-- 9. pokemon_type_affinity   (FK → pokemon_master)
-- 10. pokemon_feature_vectors (FK → pokemon_master)
-- 11. pokemon_annotation_log  (FK → pokemon_master)
-- 12. VIEW: v_pokemon_review_needed
-- 13. VIEW: v_pokemon_coverage
-- 14. FUNCTION: get_pokemon_full_profile
-- =============================================================================
