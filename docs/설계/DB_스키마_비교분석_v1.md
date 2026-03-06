# DB 스키마 비교분석 문서 v1
**사람 얼굴특징 DB  ↔  포켓몬 DB**

**작성일:** 2026년 3월 6일
**작성자:** 시니어 MLOps 엔지니어
**목적:** 두 DB의 구조를 비교하여 매핑 가능한 연결고리를 시각적으로 파악

---

## 1. 전체 구조 한눈에 보기

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       전체 스키마 비교 구조도                                 │
├─────────────────────────────┬────────────────────────────────────────────────┤
│     사람 얼굴특징 DB         │              포켓몬 DB                          │
│   (User_Face_Features)      │                                                 │
├─────────────────────────────┼────────────────────────────────────────────────┤
│                             │                                                 │
│  [ 단일 테이블 구조 ]        │  [ 관계형 다중 테이블 구조 ]                    │
│                             │                                                 │
│  ┌───────────────────┐      │  ┌──────────┐   ┌──────────────┐               │
│  │ User_Face_Features│      │  │ Pokemon  │──▶│Pokemon_Stats │               │
│  │                   │      │  └────┬─────┘   └──────────────┘               │
│  │ • 메타 데이터 (3)  │      │       │                                         │
│  │ • 얼굴형 데이터 (3)│      │       ├──▶ ┌──────────────┐                   │
│  │ • 눈/눈썹 데이터(4)│      │       │    │Pokemon_Types │──▶ ┌───────┐      │
│  │ • 코/입 데이터 (4) │      │       │    └──────────────┘    │ Types │      │
│  │ • 스타일/부가 (3)  │      │       │                        └───────┘      │
│  │ • 색상/감정 (3)    │      │       └──▶ ┌──────────────────┐               │
│  │                   │      │            │ Pokemon_Abilities │──▶┌──────────┐│
│  │  총 20개 컬럼     │      │            └──────────────────┘   │Abilities ││
│  └───────────────────┘      │                                    └──────────┘│
│                             │        총 6개 테이블 / 약 30개 컬럼             │
└─────────────────────────────┴────────────────────────────────────────────────┘
```

---

## 2. 카테고리별 1:1 대응 비교표

### 2-1. 신체/외형 데이터

| 사람 컬럼 | 타입 | 범위 | ↔ | 포켓몬 컬럼 | 타입 | 매핑 근거 |
|----------|------|------|---|------------|------|----------|
| `face_aspect_ratio` | FLOAT | 0.0~1.0 | → | `height`, `weight` | FLOAT | 얼굴 가로세로 비율 ≈ 포켓몬 체형 |
| `jawline_angle` | FLOAT | 각도값 | → | `defense`, `attack` | INT | 각진 턱 = 강인한 방어/공격 |
| `cheek_width_ratio` | FLOAT | 0.0~1.0 | → | `hp` | INT | 볼 넓이 ≈ 체력/볼륨감 |
| `nose_width_ratio` | FLOAT | 0.0~1.0 | → | `weight` | FLOAT | 코볼 넓이 ≈ 묵직한 체형 |

### 2-2. 눈/인상 데이터

| 사람 컬럼 | 타입 | 설명 | ↔ | 포켓몬 컬럼 | 타입 | 매핑 근거 |
|----------|------|------|---|------------|------|----------|
| `eye_size_ratio` | FLOAT | 눈 크기 | → | `special_attack` | INT | 큰 눈 = 감지력/특수공격 |
| `eye_distance_ratio` | FLOAT | 미간 거리 | → | `Types.name_ko` | VARCHAR | 넓은 눈 = 수생/풀 타입 계열 |
| `eye_slant_angle` | FLOAT | 눈꼬리 각도 | → | `attack`, `Types` | INT/VARCHAR | 올라감 = 격투/악, 처짐 = 페어리/노말 |
| `eyebrow_thickness` | FLOAT | 눈썹 두께 | → | `attack` | INT | 두꺼운 눈썹 = 공격성 |

### 2-3. 스타일/부가 특징

| 사람 컬럼 | 타입 | ↔ | 포켓몬 데이터 | 매핑 근거 |
|----------|------|---|-------------|----------|
| `has_glasses` | BOOLEAN | → | 에스퍼/강철/전기 타입 | 지적인 느낌 = 정신/기술 계열 |
| `has_facial_hair` | BOOLEAN | → | 격투/바위/땅 타입 | 수염 = 야성적/강인함 |
| `has_bangs` | BOOLEAN | → | 풀/비행 타입 | 앞머리 = 덮인 디자인 포켓몬 |

### 2-4. 색상/감정 데이터

| 사람 컬럼 | 타입 | ↔ | 포켓몬 데이터 | 매핑 근거 |
|----------|------|---|-------------|----------|
| `dominant_color` | VARCHAR(7) | → | `Types.name_ko` | 사진 주조색 = 포켓몬 타입 색상 |
| `smile_score` | FLOAT | → | `Types` + `Abilities` | 웃음 = 페어리/노말, 무표정 = 에스퍼 |
| `emotion_class` | VARCHAR(20) | → | `Types` + `Abilities` | 감정 분류 = 타입 + 특성 |

---

## 3. 매핑 관계 시각화

### 3-1. 사람 특징 → 포켓몬 타입 매핑 흐름

```
사람 특징 데이터                        포켓몬 타입 (Types)
─────────────────                       ──────────────────────

eye_slant_angle (↑올라감)  ──────┐
has_facial_hair = TRUE     ──────┼──▶  격투 / 악 타입
jawline_angle (각짐)       ──────┘

eye_size_ratio (큰 눈)     ──────┐
has_glasses = TRUE         ──────┼──▶  에스퍼 / 전기 타입
dominant_color (보라/노랑) ──────┘

eye_distance_ratio (넓은 미간) ──┐
dominant_color (파랑)       ─────┼──▶  물 / 얼음 타입
lip_thickness_ratio (두꺼운 입술)┘

smile_score (높음)         ──────┐
eye_slant_angle (↓처짐)    ──────┼──▶  페어리 / 노말 타입
has_bangs = TRUE           ──────┘

nose_width_ratio (넓은 코) ──────┐
cheek_width_ratio (넓은 볼)──────┼──▶  땅 / 바위 타입
dominant_color (갈색/주황) ──────┘

has_bangs = TRUE           ──────┐
face_aspect_ratio (세로형) ──────┼──▶  풀 / 비행 타입
dominant_color (초록)      ──────┘

dominant_color (빨강/주황) ──────┐
jawline_angle (각짐)       ──────┼──▶  불꽃 타입
eye_slant_angle (↑올라감)  ──────┘
```

### 3-2. 사람 특징 → 포켓몬 스탯 매핑 흐름

```
사람 특징 데이터                        포켓몬 종족치 (Stats)
─────────────────                       ──────────────────────

cheek_width_ratio (넓음)   ──────────▶  HP (체력) ↑
face_aspect_ratio (둥글)   ──────────▶  HP (체력) ↑

jawline_angle (각짐)       ──────────▶  ATTACK (공격) ↑
eyebrow_thickness (두꺼움) ──────────▶  ATTACK (공격) ↑
eye_slant_angle (올라감)   ──────────▶  ATTACK (공격) ↑

face_aspect_ratio (넓적)   ──────────▶  DEFENSE (방어) ↑
nose_width_ratio (넓음)    ──────────▶  DEFENSE (방어) ↑

eye_size_ratio (큼)        ──────────▶  SP. ATTACK (특수공격) ↑
has_glasses = TRUE         ──────────▶  SP. ATTACK (특수공격) ↑

eye_distance_ratio (넓음)  ──────────▶  SP. DEFENSE (특수방어) ↑

face_aspect_ratio (세로형) ──────────▶  SPEED (스피드) ↑
eye_slant_angle (날카로움) ──────────▶  SPEED (스피드) ↑
```

---

## 4. 데이터 타입 호환성 비교

| 구분 | 사람 DB | 포켓몬 DB | 호환 방식 |
|------|--------|----------|---------|
| 수치형 | FLOAT (0.0~1.0 정규화) | INT (0~255 범위) | 정규화 후 비교 (`INT / 255`) |
| 범주형 | VARCHAR (색상 HEX, 감정) | VARCHAR (타입명, 특성명) | 룰 테이블로 변환 |
| 불리언 | BOOLEAN (안경, 수염 등) | BOOLEAN (숨겨진 특성) | 가중치 점수로 변환 |
| ID | VARCHAR (session_id) | INT (pokemon_id) | 독립적 (매핑 시 연결) |

---

## 5. 스키마 갭 분석 (현재 매핑 안 되는 항목)

### 사람 DB에만 있고 포켓몬 DB에 없는 항목

| 사람 컬럼 | 현재 상태 | 해결 방안 |
|----------|----------|---------|
| `dominant_color` (HEX) | 포켓몬 DB에 color 컬럼 없음 | `Pokemon` 테이블에 `color_category` 컬럼 추가 필요 |
| `emotion_class` | 포켓몬 DB에 감정 데이터 없음 | `Abilities` 설명 텍스트에서 LLM으로 감정 점수 추출 |
| `smile_score` | 직접 대응 컬럼 없음 | 타입 친화도 점수로 변환하여 간접 매핑 |
| `has_bangs` | 포켓몬 DB에 헤어 데이터 없음 | 포켓몬 이미지 분석 시 Gemini Vision으로 주석 추가 |

### 포켓몬 DB에만 있고 사람 DB에 없는 항목

| 포켓몬 컬럼 | 현재 상태 | 해결 방안 |
|-----------|----------|---------|
| `generation` | 매핑 불필요 | 결과 UI에서 세대 정보로 표시 |
| `Abilities` (특성) | 사람 특성 추출 안 됨 | 타입 매칭 후 LLM이 스토리 생성 시 반영 |
| `hp/attack/.../speed` | 사람 스탯 없음 | 얼굴 특징에서 유추하여 간접 매핑 |

---

## 6. 추천 스키마 보완 사항

포켓몬 DB에 아래 컬럼 추가 시 매핑 완성도가 크게 향상됩니다.

```sql
-- Pokemon 테이블 보완 컬럼
ALTER TABLE Pokemon ADD COLUMN color_category VARCHAR(20);
-- 값: 'red', 'blue', 'yellow', 'green', 'purple', 'brown', 'black', 'white', 'pink', 'gray'
-- PokeAPI: /pokemon-species/{id} → color.name 에서 직접 가져올 수 있음

ALTER TABLE Pokemon ADD COLUMN shape_category VARCHAR(20);
-- 값: 'round', 'long', 'wide', 'upright', 'quadruped', 'wings' 등
-- PokeAPI: /pokemon-species/{id} → shape.name 에서 직접 가져올 수 있음

-- 포켓몬 인상 점수 테이블 (Gemini Vision + LLM 배치 주석)
CREATE TABLE Pokemon_Impression (
    pokemon_id       INT PRIMARY KEY REFERENCES Pokemon(id),
    cute_score       FLOAT,   -- 0.0~1.0
    fierce_score     FLOAT,
    calm_score       FLOAT,
    smart_score      FLOAT,
    lively_score     FLOAT,
    gentle_score     FLOAT
);
```

---

## 7. 최종 매핑 가능성 평가

| 사람 데이터 카테고리 | 포켓몬 데이터 | 매핑 난이도 | 신뢰도 |
|------------------|-------------|-----------|-------|
| 얼굴형 (aspect_ratio 등) | hp, defense | ★☆☆ 쉬움 | 중간 |
| 눈/눈썹 (size, angle) | attack, sp_attack, 타입 | ★★☆ 보통 | 높음 |
| 코/입 (width 비율) | 타입, weight | ★★☆ 보통 | 중간 |
| 스타일 부가 (안경, 수염) | 타입 결정적 | ★☆☆ 쉬움 | 매우 높음 |
| 색상 (dominant_color) | 타입 (색상 기반) | ★★★ 어려움 | 중간 |
| 감정 (smile_score) | 타입, 특성 | ★★☆ 보통 | 낮음~중간 |

> **결론:** 안경/수염/눈꼬리 각도가 타입 매핑의 핵심 변수이며, 눈 크기와 눈썹 두께가 스탯 매핑의 핵심입니다. 색상과 감정은 보조 가중치로 활용하는 것이 현실적입니다.
