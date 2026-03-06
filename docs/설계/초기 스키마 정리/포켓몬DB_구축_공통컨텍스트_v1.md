# 포켓몬 DB 구축 공통 컨텍스트
**대상:** 2세대 (#152~#251) / 3세대 (#252~#386) 담당 팀원
**목적:** 각자의 생성형 AI를 활용해 세대별 포켓몬 DB 데이터를 동일한 기준으로 구축하기 위한 공통 참고 문서
**작성일:** 2026-03-06

---

## 0. 이 문서를 읽기 전에

> 1세대(#001~#151) 작업은 완료된 상태입니다.
> 이 문서를 AI에게 통째로 전달하면, 해당 세대 포켓몬 데이터를 동일한 기준으로 뽑아낼 수 있습니다.

### AI에게 전달할 때 이렇게 말하세요

```
아래 문서는 포켓몬 DB 구축을 위한 공통 컨텍스트입니다.
이 기준에 맞춰서 [2세대 / 3세대] 포켓몬 (#XXX~#XXX) 의
특징 데이터를 분석하고 SQL INSERT 문으로 작성해주세요.
```

---

## 1. 프로젝트 배경 (AI에게 전달할 내용)

### 무엇을 만드는가

**Pokéman** 프로젝트는 사용자의 얼굴 사진을 분석해 가장 닮은 포켓몬을 찾아주는 서비스입니다.

- 사용자 사진 → MediaPipe로 얼굴 특징 수치 추출 → **28차원 벡터** 생성
- 포켓몬 DB → 동일한 스키마로 각 포켓몬의 특징 수치 저장 → **28차원 벡터** 생성
- 두 벡터를 **pgvector 코사인 유사도**로 비교 → 가장 닮은 포켓몬 Top-3 반환

### 핵심 원칙

> 사람의 얼굴 특징과 포켓몬의 시각적/성격적 특징을 **동일한 수치 기준**으로 표현해야 합니다.
> 포켓몬의 얼굴/두부 구조를 인간 얼굴에 비유하여 해석합니다.

---

## 2. 스키마 명세 (필드 정의)

모든 값은 별도 명시가 없으면 **0.0 ~ 1.0** 사이의 실수입니다.

### 2-1. 얼굴형 (face_shape)

| 필드명 | 타입 | 설명 | 포켓몬 적용 기준 |
|--------|------|------|----------------|
| `face_aspect_ratio` | FLOAT | 얼굴 가로÷세로 비율 | 두부(머리) 가로÷세로. 0=매우 세로형, 1=매우 가로형/둥글 |
| `jawline_angle` | FLOAT | 턱선 형태 | 하턱/주둥이 끝 형태. 0=뾰족한 V라인, 1=둥근 U라인 |

### 2-2. 눈 (eye)

| 필드명 | 타입 | 설명 | 포켓몬 적용 기준 |
|--------|------|------|----------------|
| `eye_size_ratio` | FLOAT | 눈 크기 | 눈 크기÷얼굴 크기. 0=눈 없음, 1=매우 큰 눈 (예: 푸린=1.0) |
| `eye_distance_ratio` | FLOAT | 미간 넓이 | 양눈 중심 간 거리÷얼굴 가로. 0=매우 붙음, 1=매우 넓음 |
| `eye_slant_angle` | FLOAT | 눈꼬리 방향 | 0=매우 처짐(온화/강아지상), 0.5=수평(중립), 1=매우 올라감(공격적/고양이상) |

### 2-3. 코/입 (nose & mouth)

| 필드명 | 타입 | 설명 | 포켓몬 적용 기준 |
|--------|------|------|----------------|
| `nose_length_ratio` | FLOAT | 코/주둥이 길이 | 코·주둥이 돌출 길이÷얼굴 세로. 코 없으면 0.1 |
| `nose_width_ratio` | FLOAT | 코볼 너비 | 코볼·콧구멍 너비÷얼굴 가로. 코 없으면 0.1 |
| `mouth_width_ratio` | FLOAT | 입 너비 | 입·부리 너비÷얼굴 가로. 0=매우 작음, 1=매우 큼 |
| `lip_thickness_ratio` | FLOAT | 입술 두께감 | 0=선 형태(얇음), 1=매우 두꺼운 입술. 비인간형은 주로 0.1~0.3 |
| `philtrum_ratio` | FLOAT | 인중 길이 | 비인간형 포켓몬은 **0.1 고정**. 인간형 포켓몬만 실측 |

### 2-4. 스타일/부가 특징 (style) — Boolean

| 필드명 | 타입 | 판단 기준 |
|--------|------|---------|
| `has_glasses` | BOOLEAN | 안경 또는 안경 형태의 디자인 요소 보유 여부 |
| `has_facial_hair` | BOOLEAN | 수염·콧수염·갈기·수염털 유사 요소 보유 여부 |
| `has_bangs` | BOOLEAN | 두부 전면을 덮는 털·잎·갈기·장식 유무 |

### 2-5. 감정/성격 (emotion)

| 필드명 | 타입 | 허용 값 |
|--------|------|--------|
| `smile_score` | FLOAT | 0=찌푸림, 0.5=무표정, 1=환한 미소 |
| `emotion_class` | VARCHAR | **기쁨 / 무표정 / 분노 / 신비 / 온화 / 슬픔 / 공포** 중 1개 |
| `personality_class` | VARCHAR | 아래 키워드 풀에서 **최대 4개** 선택, 쉼표 구분 |

**personality_class 키워드 풀:**
```
용감한 / 온화한 / 조심스러운 / 명랑한 / 냉정한 / 건방진
고집스러운 / 느긋한 / 개구쟁이 / 뻔뻔한 / 호기심많은
외로움을타는 / 수줍은 / 사나운 / 신중한 / 충성스러운
```

---

## 3. 예외 처리 규칙 (반드시 준수)

포켓몬은 다양한 형태를 가지므로 아래 규칙을 우선 적용합니다.

| 케이스 | 예시 포켓몬 | 처리 방법 |
|--------|-----------|---------|
| 눈이 없는 포켓몬 | 주뱃(Gen1 원본) | eye_size_ratio=0.0, eye_distance_ratio=0.5, eye_slant_angle=0.5 |
| 전신이 눈인 포켓몬 | 왕눈해, 윤겔라 계열 | eye_size_ratio=1.0 |
| 코·입 구분 불명확 | 캐터피, 단데기 | nose_* = 0.1, mouth_width_ratio = 0.2 |
| 얼굴이 몸 전체인 포켓몬 | 고오스, 팬텀 | 몸 전체를 얼굴로 간주하여 분석 |
| 비인간형 포켓몬 (대부분) | 대부분 | philtrum_ratio = **0.1 고정** |
| 다면체·무기물 포켓몬 | 자브·코일 계열 | face_aspect_ratio는 실루엣 전체 기준 |
| 수중 생물 (지느러미=bangs?) | 발챙이 계열 | 두부 전면을 실제로 덮는 요소만 has_bangs=TRUE |

---

## 4. 실제 예시 데이터 (1세대 기준, AI 참고용)

AI가 일관성 있는 값을 뽑도록 아래 예시를 참고 기준으로 제공합니다.

### 예시 A: 귀여운/둥근 계열 — 이상해씨 (#001)

```sql
-- pokemon_face_shape
INSERT INTO pokemon_face_shape VALUES (1, 0.80, 0.80, 'gemini_vision', 0.85, FALSE);

-- pokemon_eye_features
INSERT INTO pokemon_eye_features VALUES (1, 0.60, 0.50, 0.40, NULL, 'gemini_vision', 0.85, FALSE);

-- pokemon_nose_mouth_features
INSERT INTO pokemon_nose_mouth_features VALUES (1, 0.20, 0.20, 0.40, 0.25, 0.10, FALSE, NULL, 'gemini_vision', 0.80, FALSE);

-- pokemon_style_features
INSERT INTO pokemon_style_features VALUES (1, FALSE, FALSE, FALSE, NULL, NULL, NULL, 'gemini_vision', FALSE);

-- pokemon_emotion_features
INSERT INTO pokemon_emotion_features VALUES (1, 0.60, '온화', '온화한,조심스러운,명랑한', 'gemini_flash_text', FALSE);
```

### 예시 B: 공격적/날카로운 계열 — 리자몽 (#006)

```sql
INSERT INTO pokemon_face_shape VALUES (6, 0.65, 0.35, 'gemini_vision', 0.90, FALSE);
INSERT INTO pokemon_eye_features VALUES (6, 0.50, 0.40, 0.85, NULL, 'gemini_vision', 0.90, FALSE);
INSERT INTO pokemon_nose_mouth_features VALUES (6, 0.35, 0.25, 0.55, 0.30, 0.10, FALSE, NULL, 'gemini_vision', 0.85, FALSE);
INSERT INTO pokemon_style_features VALUES (6, FALSE, FALSE, FALSE, NULL, NULL, NULL, 'gemini_vision', FALSE);
INSERT INTO pokemon_emotion_features VALUES (6, 0.20, '분노', '용감한,고집스러운,사나운', 'gemini_flash_text', FALSE);
```

### 예시 C: 신비로운 계열 — 팬텀 (#093)

```sql
INSERT INTO pokemon_face_shape VALUES (93, 0.70, 0.90, 'gemini_vision', 0.80, FALSE);
INSERT INTO pokemon_eye_features VALUES (93, 0.80, 0.60, 0.45, 'full_body_eye', 'gemini_vision', 0.80, FALSE);
INSERT INTO pokemon_nose_mouth_features VALUES (93, 0.10, 0.10, 0.50, 0.10, 0.10, FALSE, 'no_mouth', 'gemini_vision', 0.75, FALSE);
INSERT INTO pokemon_style_features VALUES (93, FALSE, FALSE, FALSE, NULL, NULL, NULL, 'gemini_vision', FALSE);
INSERT INTO pokemon_emotion_features VALUES (93, 0.30, '신비', '수줍은,외로움을타는,신중한', 'gemini_flash_text', FALSE);
```

### 예시 D: 인간형 포켓몬 — 괴력몬 (#068)

```sql
INSERT INTO pokemon_face_shape VALUES (68, 0.60, 0.55, 'gemini_vision', 0.88, FALSE);
INSERT INTO pokemon_eye_features VALUES (68, 0.40, 0.45, 0.75, NULL, 'gemini_vision', 0.88, FALSE);
INSERT INTO pokemon_nose_mouth_features VALUES (68, 0.30, 0.30, 0.45, 0.40, 0.25, TRUE, NULL, 'gemini_vision', 0.82, FALSE);
INSERT INTO pokemon_style_features VALUES (68, FALSE, TRUE, FALSE, NULL, 'mustache_shape_marking', NULL, 'gemini_vision', FALSE);
INSERT INTO pokemon_emotion_features VALUES (68, 0.25, '분노', '용감한,뻔뻔한,고집스러운,사나운', 'gemini_flash_text', FALSE);
```

---

## 5. AI에게 전달할 프롬프트 템플릿

아래 프롬프트를 그대로 복사해서 AI에게 전달하세요.

---

### [프롬프트 시작]

```
당신은 포켓몬스터 데이터베이스 구축 전문가입니다.
아래 기준에 따라 포켓몬의 특징을 분석하고 SQL INSERT 문을 생성해주세요.

## 작업 대상
- 포켓몬: [여기에 담당 세대 및 번호 범위 입력]
- 예시: 2세대 #152 치코리타 ~ #180 플레임꼬 (30마리씩 나눠서 요청 권장)

## 값 기준
모든 float 값은 0.00 ~ 1.00 사이의 소수점 2자리 실수입니다.

### face_shape 테이블
- face_aspect_ratio: 두부(머리) 가로÷세로 비율
  - 0.0 = 매우 세로형(뱀·긴 형태)
  - 0.5 = 균형형(일반적 포켓몬)
  - 1.0 = 매우 가로형·둥글(잠만보·푸린류)
- jawline_angle: 하턱·주둥이 끝 곡선
  - 0.0 = 뾰족한 V라인(용·파충류)
  - 1.0 = 둥근 U라인(귀여운·통통한 계열)

### eye_features 테이블
- eye_size_ratio: 눈 크기 상대 비율 (0=없음, 1=매우 큼)
- eye_distance_ratio: 양눈 간격 (0=붙음, 1=매우 넓음)
- eye_slant_angle: 눈꼬리 방향 (0=처짐/온화, 0.5=수평, 1=올라감/공격적)
- eye_note: 특수 케이스 메모 (no_eyes / compound_eyes / full_body_eye / NULL)

### nose_mouth_features 테이블
- nose_length_ratio: 코·주둥이 돌출 길이 (코 없으면 0.10)
- nose_width_ratio: 코볼·콧구멍 너비 (코 없으면 0.10)
- mouth_width_ratio: 입·부리 너비 (0=작음, 1=매우 큼)
- lip_thickness_ratio: 입술 두께감 (0=선 형태, 1=두꺼움)
- philtrum_ratio: 비인간형=0.10 고정, 인간형만 실측
- is_humanoid: 인간형 포켓몬 여부 (TRUE/FALSE)
- mouth_note: 특수 케이스 (beak / no_mouth / full_body_mouth / NULL)

### style_features 테이블
- has_glasses: 안경 또는 안경 형태 디자인 (TRUE/FALSE)
- has_facial_hair: 수염·갈기·콧수염 유사 요소 (TRUE/FALSE)
- has_bangs: 두부 전면 덮는 털·잎·갈기 (TRUE/FALSE)
- glasses_note: has_glasses=TRUE일 때 근거 메모
- facial_hair_note: has_facial_hair=TRUE일 때 근거 메모
- bangs_note: has_bangs=TRUE일 때 근거 메모

### emotion_features 테이블
- smile_score: 0=찌푸림, 0.5=무표정, 1=환한 미소
- emotion_class: 기쁨/무표정/분노/신비/온화/슬픔/공포 중 1개
- personality_class: 아래 키워드 중 최대 4개 쉼표 구분
  [용감한/온화한/조심스러운/명랑한/냉정한/건방진/고집스러운/느긋한/개구쟁이/뻔뻔한/호기심많은/외로움을타는/수줍은/사나운/신중한/충성스러운]

## 예외 처리 규칙 (반드시 준수)
- 눈 없는 포켓몬: eye_size_ratio=0.0, eye_slant_angle=0.5, eye_note='no_eyes'
- 코 없는 포켓몬: nose_length_ratio=0.10, nose_width_ratio=0.10
- 비인간형 대부분: philtrum_ratio=0.10, is_humanoid=FALSE
- 인간형 포켓몬(루주라·엘리어드 등): is_humanoid=TRUE, philtrum_ratio 실측

## 출력 형식
각 포켓몬마다 아래 5개 INSERT 문을 순서대로 생성하세요.
pokemon_master INSERT는 생략합니다 (PokeAPI 배치 수집으로 별도 처리).

-- ★ #[번호] [이름]
INSERT INTO pokemon_face_shape (pokemon_id, face_aspect_ratio, jawline_angle, extraction_source, confidence, reviewed)
VALUES ([id], [val], [val], 'gemini_vision', [0.70~0.95], FALSE);

INSERT INTO pokemon_eye_features (pokemon_id, eye_size_ratio, eye_distance_ratio, eye_slant_angle, eye_note, extraction_source, confidence, reviewed)
VALUES ([id], [val], [val], [val], [NULL or 'note'], 'gemini_vision', [val], FALSE);

INSERT INTO pokemon_nose_mouth_features (pokemon_id, nose_length_ratio, nose_width_ratio, mouth_width_ratio, lip_thickness_ratio, philtrum_ratio, is_humanoid, mouth_note, extraction_source, confidence, reviewed)
VALUES ([id], [val], [val], [val], [val], [val], [TRUE/FALSE], [NULL or 'note'], 'gemini_vision', [val], FALSE);

INSERT INTO pokemon_style_features (pokemon_id, has_glasses, has_facial_hair, has_bangs, glasses_note, facial_hair_note, bangs_note, extraction_source, reviewed)
VALUES ([id], [T/F], [T/F], [T/F], [NULL or 'note'], [NULL or 'note'], [NULL or 'note'], 'gemini_vision', FALSE);

INSERT INTO pokemon_emotion_features (pokemon_id, smile_score, emotion_class, personality_class, extraction_source, reviewed)
VALUES ([id], [val], '[class]', '[p1,p2,p3]', 'gemini_flash_text', FALSE);

## 참고 예시 (일관성 유지를 위해 반드시 참고)
-- 귀여운/둥근 계열: face_aspect=0.8~1.0, jawline=0.7~1.0, eye_size=0.6~1.0, eye_slant=0.3~0.5, smile=0.6~0.9, emotion=기쁨/온화
-- 공격적/날카로운: face_aspect=0.5~0.7, jawline=0.2~0.4, eye_slant=0.7~1.0, smile=0.1~0.3, emotion=분노
-- 신비로운 계열: eye_size=0.6~0.9, eye_slant=0.4~0.6, smile=0.3~0.5, emotion=신비
-- 뱀·벌레 계열: face_aspect=0.2~0.4, jawline=0.4~0.7, eye_size=0.3~0.5
-- 인간형: is_humanoid=TRUE, philtrum_ratio=0.15~0.35, lip_thickness=0.3~0.6
```

### [프롬프트 끝]

---

## 6. 세대별 담당 범위 및 주요 주의 포켓몬

### 2세대 (#152 ~ #251, 100마리)

| 번호 범위 | 마리 수 | 특이 포켓몬 (주의) |
|---------|--------|-----------------|
| #152~#180 | 29마리 | #165 레디바(복수 눈), #175 토게피(껍질 머리) |
| #181~#210 | 30마리 | #196 에브이(이마 보석), #197 블래키(귀 무늬), #199 야도킹(왕관) |
| #211~#251 | 41마리 | #234 노고치(뿔=bangs?), #238 루주라(인간형), #248 마기라스(갑옷형) |

### 3세대 (#252 ~ #386, 135마리)

| 번호 범위 | 마리 수 | 특이 포켓몬 (주의) |
|---------|--------|-----------------|
| #252~#290 | 39마리 | #280 랄토스(머리 뿔=bangs), #286 나무킹(후드형 머리) |
| #291~#330 | 40마리 | #302 깜눈크(눈=몸 전체), #307 마크탕(이마 무늬) |
| #331~#386 | 56마리 | #352 켈리몬(가면), #360 로토무(없음), #385 지라치(별 모양 머리), #386 테오키스(외계형) |

---

## 7. 품질 기준 (QA Checklist)

AI가 생성한 데이터를 삽입하기 전에 아래 항목을 반드시 확인하세요.

```
[ ] 모든 float 값이 0.00 ~ 1.00 범위 내인가?
[ ] emotion_class가 허용 값 7개 중 하나인가?
[ ] personality_class 키워드가 허용 풀 내에서만 선택됐는가?
[ ] personality_class가 4개 이하인가?
[ ] 비인간형 포켓몬의 philtrum_ratio가 0.10인가?
[ ] 눈 없는 포켓몬의 eye_size_ratio가 0.00인가?
[ ] 같은 진화 라인에서 값 차이가 극단적이지 않은가?
  - 예: 치코리타(0.7) → 메가니움(0.9) 는 자연스러움
  - 예: 치코리타(0.7) → 메가니움(0.1) 은 재검토 필요
[ ] extraction_source가 올바르게 입력됐는가?
  - 시각 필드: 'gemini_vision'
  - 텍스트 필드: 'gemini_flash_text'
[ ] 모든 INSERT 문이 5개인가? (face_shape/eye/nose_mouth/style/emotion)
```

---

## 8. 완성된 데이터 제출 방법

각자 작업이 완료되면 아래 형식으로 팀에 공유합니다.

### 파일 명명 규칙

```
database/
├── 포켓몬_DDL_gen1_v1.sql         ← 1세대 (구조 + 데이터)
├── 포켓몬_seed_gen2_v1.sql        ← 2세대 담당자 생성 (데이터만)
└── 포켓몬_seed_gen3_v1.sql        ← 3세대 담당자 생성 (데이터만)
```

### 파일 헤더 형식

```sql
-- =============================================================
-- Pokéman Project: Gen [X] Pokemon Seed Data
-- 대상: [X]세대 포켓몬 #[시작] ~ #[끝]
-- 작성자: [이름]
-- 작성일: [날짜]
-- 검수 완료: [ ]
-- =============================================================

BEGIN;

-- #[번호] [이름]
INSERT INTO pokemon_face_shape ...
INSERT INTO pokemon_eye_features ...
INSERT INTO pokemon_nose_mouth_features ...
INSERT INTO pokemon_style_features ...
INSERT INTO pokemon_emotion_features ...

COMMIT;
```

> `BEGIN;` ~ `COMMIT;` 트랜잭션으로 감싸서 제출하면
> 오류 발생 시 해당 세대 전체가 롤백되어 부분 삽입을 방지할 수 있습니다.

---

## 9. 자주 묻는 질문 (FAQ)

**Q. confidence 값은 어떻게 정하나요?**
A. AI가 얼마나 확신을 가지고 값을 뽑았는지를 주관적으로 입력합니다. 판단이 명확한 포켓몬 0.85~0.95, 애매한 경우 0.70~0.80으로 입력하세요. 0.70 미만이면 팀 검수 대상으로 자동 분류됩니다.

**Q. 진화 전후 포켓몬의 값 차이는 얼마나 달라야 하나요?**
A. 진화할수록 강해지는 방향으로 변화하는 것이 자연스럽습니다. 예를 들어 `eye_slant_angle`은 진화할수록 올라가고, `smile_score`는 진화할수록 낮아지는 경향이 있습니다. 단, 0.2 이상 급격한 차이는 재검토하세요.

**Q. 메가진화·지역 폼은 포함해야 하나요?**
A. 이번 범위에서는 **기본 폼만** 작성합니다. 메가진화·지역 폼은 추후 별도 확장 작업으로 처리합니다.

**Q. pokemon_master INSERT는 언제 하나요?**
A. PokeAPI 배치 수집 스크립트가 자동으로 처리합니다. 직접 작성하지 않아도 됩니다.

**Q. 값이 도저히 판단이 안 되는 포켓몬은 어떻게 하나요?**
A. 모든 float 값을 0.50으로, boolean은 FALSE로, emotion_class는 '무표정'으로 입력하고 confidence=0.60으로 낮게 설정하세요. 팀 검수 대상으로 자동 분류됩니다.
