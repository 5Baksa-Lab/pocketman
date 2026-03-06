# Rule-based 매핑 알고리즘 초안 v1
**사람 얼굴특징 → 포켓몬 타입/스탯 매핑 규칙**

**작성일:** 2026년 3월 6일
**작성자:** 시니어 MLOps 엔지니어
**참고 문서:** 사람_얼굴특징_DB_스키마_v1.md / 포켓몬_DB_스키마_v1.md / DB_스키마_비교분석_v1.md
**용도:** 개발 참고용 초안 (수치는 팀 테스트 후 조정 필요)

---

## 0. 알고리즘 개요

```
[입력] User_Face_Features (20개 컬럼)
         │
         ▼
┌────────────────────────────────┐
│  Step 1: 타입 점수 계산         │  각 포켓몬 타입에 대한 0~100점 산출
│  (Type Score Calculator)       │
└────────────────┬───────────────┘
                 │
                 ▼
┌────────────────────────────────┐
│  Step 2: 스탯 프로파일 계산     │  6개 종족치 선호도 프로파일 생성
│  (Stat Profile Builder)        │
└────────────────┬───────────────┘
                 │
                 ▼
┌────────────────────────────────┐
│  Step 3: 포켓몬 DB 매칭        │  타입 점수 + 스탯 유사도 → Top-K
│  (Pokemon Matcher)             │
└────────────────┬───────────────┘
                 │
                 ▼
┌────────────────────────────────┐
│  Step 4: 근거 문장 생성        │  매칭 이유 자동 생성
│  (Reasoning Generator)         │
└────────────────────────────────┘

[출력] Top-3 포켓몬 + 유사도 점수 + 근거 문장
```

---

## 1. Step 1 — 타입 점수 계산 (Type Score Calculator)

18개 포켓몬 타입 각각에 대해 0~100점을 산출합니다.
여러 규칙이 동시에 적용될 경우 점수를 합산합니다.

### 1-1. 결정적 규칙 (Critical Rules) — 가중치 높음

안경, 수염 등 명확한 시각 신호를 기반으로 타입을 결정짓는 규칙입니다.

```python
def apply_critical_rules(features: dict, type_scores: dict) -> dict:

    # 안경 착용 → 지식/기술 계열 타입
    if features['has_glasses']:
        type_scores['에스퍼'] += 50
        type_scores['전기']   += 35
        type_scores['강철']   += 30
        type_scores['노말']   += 10

    # 수염 존재 → 야성/강인 계열 타입
    if features['has_facial_hair']:
        type_scores['격투'] += 50
        type_scores['바위'] += 40
        type_scores['땅']   += 35
        type_scores['악']   += 20

    # 앞머리 존재 → 자연/유연 계열 타입
    if features['has_bangs']:
        type_scores['풀']   += 40
        type_scores['비행'] += 30
        type_scores['물']   += 15

    return type_scores
```

### 1-2. 눈/눈썹 규칙 (Eye Rules) — 가중치 중상

```python
def apply_eye_rules(features: dict, type_scores: dict) -> dict:

    # 눈꼬리 각도 (eye_slant_angle)
    # +값 = 올라감(고양이상), -값 = 처짐(강아지상)
    angle = features['eye_slant_angle']

    if angle > 15:          # 강하게 올라감
        type_scores['악']   += 45
        type_scores['격투'] += 35
        type_scores['불꽃'] += 25
        type_scores['독']   += 20

    elif angle > 5:         # 약하게 올라감
        type_scores['악']   += 20
        type_scores['불꽃'] += 15
        type_scores['에스퍼'] += 10

    elif angle < -15:       # 강하게 처짐
        type_scores['페어리'] += 45
        type_scores['노말']   += 35
        type_scores['물']     += 20
        type_scores['얼음']   += 15

    elif angle < -5:        # 약하게 처짐
        type_scores['페어리'] += 20
        type_scores['노말']   += 20
        type_scores['물']     += 10

    else:                   # 중립 (-5 ~ +5)
        type_scores['노말']   += 20
        type_scores['에스퍼'] += 15
        type_scores['강철']   += 10

    # 눈 크기 (eye_size_ratio): 0.0(작음) ~ 1.0(큼)
    eye_size = features['eye_size_ratio']

    if eye_size > 0.7:      # 매우 큰 눈
        type_scores['페어리']   += 40
        type_scores['노말']     += 25
        type_scores['에스퍼']   += 20
        type_scores['물']       += 15

    elif eye_size > 0.5:    # 큰 눈
        type_scores['페어리']   += 20
        type_scores['노말']     += 15

    elif eye_size < 0.3:    # 작은 눈
        type_scores['강철']     += 25
        type_scores['바위']     += 20
        type_scores['땅']       += 15
        type_scores['악']       += 15

    # 미간 거리 (eye_distance_ratio): 0.0(좁음) ~ 1.0(넓음)
    eye_dist = features['eye_distance_ratio']

    if eye_dist > 0.65:     # 넓은 미간
        type_scores['물']   += 35
        type_scores['풀']   += 25
        type_scores['비행'] += 20

    elif eye_dist < 0.35:   # 좁은 미간
        type_scores['격투'] += 25
        type_scores['에스퍼'] += 20
        type_scores['악']   += 15

    # 눈썹 두께 (eyebrow_thickness): 0.0(얇음) ~ 1.0(두꺼움)
    brow = features['eyebrow_thickness']

    if brow > 0.6:          # 두꺼운 눈썹
        type_scores['격투'] += 30
        type_scores['바위'] += 25
        type_scores['악']   += 20

    elif brow < 0.3:        # 얇은 눈썹
        type_scores['페어리'] += 25
        type_scores['에스퍼'] += 20
        type_scores['얼음']   += 15

    return type_scores
```

### 1-3. 얼굴형 규칙 (Face Shape Rules) — 가중치 중

```python
def apply_face_shape_rules(features: dict, type_scores: dict) -> dict:

    # 얼굴 가로/세로 비율 (face_aspect_ratio)
    # 높을수록 가로형(넓적), 낮을수록 세로형(갸름)
    ratio = features['face_aspect_ratio']

    if ratio > 0.85:        # 넓적한 얼굴
        type_scores['노말'] += 25
        type_scores['땅']   += 20
        type_scores['바위'] += 20
        type_scores['물']   += 10

    elif ratio < 0.65:      # 갸름한 얼굴
        type_scores['에스퍼'] += 25
        type_scores['비행']   += 20
        type_scores['얼음']   += 15
        type_scores['독']     += 10

    # 턱선 각도 (jawline_angle): 높을수록 각짐 (V라인 → 각진 턱)
    jaw = features['jawline_angle']

    if jaw > 70:            # 각진 턱
        type_scores['격투'] += 30
        type_scores['강철'] += 25
        type_scores['바위'] += 20

    elif jaw < 50:          # 부드러운 U라인
        type_scores['페어리'] += 25
        type_scores['물']     += 20
        type_scores['노말']   += 15

    # 광대뼈 너비 (cheek_width_ratio)
    cheek = features['cheek_width_ratio']

    if cheek > 0.6:         # 넓은 광대
        type_scores['땅']   += 20
        type_scores['바위'] += 20
        type_scores['격투'] += 15

    return type_scores
```

### 1-4. 색상 규칙 (Color Rules) — 가중치 보조

```python
import colorsys

COLOR_TYPE_MAP = {
    # (Hue 범위, Saturation 기준)
    'red':    {'불꽃': 40, '격투': 20, '드래곤': 15},
    'orange': {'불꽃': 30, '격투': 20, '드래곤': 15},
    'yellow': {'전기': 45, '노말': 20, '강철': 10},
    'green':  {'풀': 50, '독': 20, '벌레': 15},
    'blue':   {'물': 50, '얼음': 25, '비행': 15},
    'purple': {'에스퍼': 45, '독': 30, '고스트': 25},
    'pink':   {'페어리': 50, '노말': 20},
    'brown':  {'땅': 40, '바위': 35, '노말': 15},
    'black':  {'악': 40, '고스트': 30, '강철': 20},
    'white':  {'노말': 35, '얼음': 30, '강철': 20},
    'gray':   {'강철': 40, '바위': 25, '노말': 20},
}

def apply_color_rules(features: dict, type_scores: dict) -> dict:
    hex_color = features.get('dominant_color', '#808080')

    # HEX → HSV 변환으로 색상 분류
    color_category = classify_color(hex_color)
    type_map = COLOR_TYPE_MAP.get(color_category, {})

    for type_name, score in type_map.items():
        type_scores[type_name] += score  # 색상은 50% 가중치
    return type_scores


def classify_color(hex_color: str) -> str:
    """HEX 색상 코드 → 색상 카테고리 분류"""
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    h_deg = h * 360

    if s < 0.15:                        # 무채색
        if v > 0.8: return 'white'
        if v < 0.3: return 'black'
        return 'gray'
    if h_deg < 15 or h_deg >= 345:     return 'red'
    if 15  <= h_deg < 40:              return 'orange'
    if 40  <= h_deg < 70:              return 'yellow'
    if 70  <= h_deg < 160:             return 'green'
    if 160 <= h_deg < 250:             return 'blue'
    if 250 <= h_deg < 290:             return 'purple'
    if 290 <= h_deg < 345:             return 'pink'
    return 'gray'
```

### 1-5. 감정/웃음 규칙 (Emotion Rules) — 가중치 보조

```python
EMOTION_TYPE_MAP = {
    '기쁨':   {'페어리': 30, '노말': 20, '불꽃': 10},
    '슬픔':   {'물': 25, '얼음': 20, '고스트': 15},
    '화남':   {'격투': 35, '악': 25, '불꽃': 20},
    '놀람':   {'전기': 30, '에스퍼': 20, '비행': 15},
    '혐오':   {'독': 30, '악': 20},
    '무표정': {'에스퍼': 25, '강철': 20, '고스트': 15},
}

def apply_emotion_rules(features: dict, type_scores: dict) -> dict:

    # 웃음 점수 (smile_score): 0.0~1.0
    smile = features['smile_score']
    if smile > 0.7:
        type_scores['페어리'] += 25
        type_scores['노mal']  += 20
    elif smile < 0.2:
        type_scores['에스퍼'] += 20
        type_scores['강철']   += 15
        type_scores['악']     += 10

    # 감정 분류 (emotion_class)
    emotion = features.get('emotion_class', '무표정')
    for type_name, score in EMOTION_TYPE_MAP.get(emotion, {}).items():
        type_scores[type_name] += score

    return type_scores
```

---

## 2. Step 2 — 스탯 프로파일 계산 (Stat Profile Builder)

6개 종족치 각각에 대한 선호도 점수를 0~255 스케일로 산출합니다.

```python
def build_stat_profile(features: dict) -> dict:
    """
    사람 얼굴 특징 → 포켓몬 종족치 선호 프로파일
    반환값: 각 스탯의 선호 점수 (0~255, 높을수록 해당 스탯이 높은 포켓몬과 매칭)
    """
    stats = {
        'hp': 0, 'attack': 0, 'defense': 0,
        'special_attack': 0, 'special_defense': 0, 'speed': 0
    }

    # HP: 둥글고 넓적한 얼굴 = 높은 체력
    stats['hp'] += features['cheek_width_ratio'] * 100
    stats['hp'] += (1 - features['face_aspect_ratio']) * 80  # 둥글수록 HP 높음
    stats['hp'] = min(stats['hp'], 255)

    # ATTACK: 각진 턱 + 두꺼운 눈썹 + 올라간 눈꼬리
    jaw_score  = (features['jawline_angle'] - 30) / 60      # 30~90도 정규화
    brow_score = features['eyebrow_thickness']
    slant_score = max(0, features['eye_slant_angle']) / 30  # 올라간 정도
    stats['attack'] = int((jaw_score * 100 + brow_score * 80 + slant_score * 75) / 3 * 2.55)
    stats['attack'] = min(stats['attack'], 255)

    # DEFENSE: 넓적한 얼굴 + 넓은 코볼
    stats['defense'] += features['face_aspect_ratio'] * 120
    stats['defense'] += features['nose_width_ratio'] * 80
    stats['defense'] = min(int(stats['defense']), 255)

    # SPECIAL ATTACK: 큰 눈 + 안경
    stats['special_attack'] += features['eye_size_ratio'] * 150
    if features['has_glasses']:
        stats['special_attack'] += 80
    stats['special_attack'] = min(int(stats['special_attack']), 255)

    # SPECIAL DEFENSE: 넓은 미간 + 큰 눈
    stats['special_defense'] += features['eye_distance_ratio'] * 120
    stats['special_defense'] += features['eye_size_ratio'] * 60
    stats['special_defense'] = min(int(stats['special_defense']), 255)

    # SPEED: 갸름한 얼굴 + 올라간 눈꼬리
    stats['speed'] += (1 - features['face_aspect_ratio']) * 120  # 갸름할수록 빠름
    stats['speed'] += max(0, features['eye_slant_angle']) / 30 * 80
    stats['speed'] = min(int(stats['speed']), 255)

    return stats
```

---

## 3. Step 3 — 포켓몬 DB 매칭 (Pokemon Matcher)

### 3-1. 타입 점수 → 포켓몬 타입 필터

```python
def filter_by_type(type_scores: dict, top_n: int = 3) -> list[str]:
    """
    타입 점수 상위 N개 타입 반환
    예: ['에스퍼', '전기', '노말']
    """
    sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_types[:top_n]]


def match_pokemon(
    type_scores: dict,
    stat_profile: dict,
    k: int = 3
) -> list[dict]:
    """
    1. 상위 타입 필터링으로 후보 포켓몬 추출
    2. 스탯 유사도로 최종 Top-K 결정
    """

    # 1단계: 타입 필터 (상위 3개 타입에 해당하는 포켓몬 추출)
    top_types = filter_by_type(type_scores, top_n=3)
    candidates = db.query("""
        SELECT p.*, ps.*
        FROM Pokemon p
        JOIN Pokemon_Stats ps ON p.id = ps.pokemon_id
        JOIN Pokemon_Types pt ON p.id = pt.pokemon_id
        JOIN Types t ON pt.type_id = t.id
        WHERE t.name_ko IN ({})
    """.format(','.join(['%s'] * len(top_types))), top_types)

    # 2단계: 스탯 유사도 계산 (코사인 유사도)
    user_vector  = normalize_stats(stat_profile)
    scored = []

    for pokemon in candidates:
        poke_stats = {
            'hp': pokemon.hp, 'attack': pokemon.attack,
            'defense': pokemon.defense, 'special_attack': pokemon.special_attack,
            'special_defense': pokemon.special_defense, 'speed': pokemon.speed
        }
        poke_vector = normalize_stats(poke_stats)
        stat_similarity = cosine_similarity(user_vector, poke_vector)

        # 3단계: 타입 점수 가중 합산
        type_score_sum = sum(
            type_scores.get(t, 0)
            for t in get_pokemon_types(pokemon.id)
        )
        type_score_norm = min(type_score_sum / 200, 1.0)  # 0~1 정규화

        # 최종 점수: 타입 60% + 스탯 40%
        final_score = (type_score_norm * 0.6) + (stat_similarity * 0.4)

        scored.append({
            'pokemon': pokemon,
            'final_score': final_score,
            'type_score': type_score_norm,
            'stat_similarity': stat_similarity,
        })

    # Top-K 반환
    scored.sort(key=lambda x: x['final_score'], reverse=True)
    return scored[:k]


def normalize_stats(stats: dict) -> list[float]:
    """스탯 딕셔너리 → 정규화된 벡터 (0~1)"""
    keys = ['hp', 'attack', 'defense', 'special_attack', 'special_defense', 'speed']
    return [stats[k] / 255 for k in keys]


def cosine_similarity(a: list, b: list) -> float:
    import math
    dot = sum(x*y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x**2 for x in a))
    mag_b = math.sqrt(sum(x**2 for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
```

---

## 4. Step 4 — 근거 문장 생성 (Reasoning Generator)

```python
REASON_TEMPLATES = {
    # 시각적 근거
    'eye_size_large':     "{name}처럼 눈이 크고 인상적입니다",
    'eye_size_small':     "{name}처럼 작고 날카로운 눈매를 가졌습니다",
    'eye_slant_up':       "올라간 눈꼬리가 {name}의 날카로운 인상과 닮았습니다",
    'eye_slant_down':     "처진 눈꼬리의 온화한 인상이 {name}와 어울립니다",
    'eye_distance_wide':  "넓은 미간이 {name}의 여유로운 눈매와 유사합니다",
    'face_round':         "둥근 얼굴형이 {name}의 체형과 닮았습니다",
    'face_long':          "갸름한 얼굴형이 {name}의 날씬한 실루엣과 어울립니다",
    'jawline_sharp':      "각진 턱선이 {name}의 강인한 인상을 공유합니다",
    'cheek_wide':         "넓은 볼이 {name}의 포근한 느낌과 닮았습니다",

    # 스타일 근거
    'glasses':            "안경을 쓴 지적인 분위기가 {name}의 지능형 속성과 일치합니다",
    'facial_hair':        "수염의 야성적인 느낌이 {name}의 강인한 특성과 닮았습니다",
    'bangs':              "앞머리로 덮인 스타일이 {name}의 디자인과 유사합니다",

    # 감정/분위기 근거
    'smile_high':         "밝은 미소가 {name}의 친근하고 활발한 성격과 어울립니다",
    'emotion_calm':       "차분한 표정이 {name}의 온화한 성격과 잘 맞습니다",
    'emotion_fierce':     "강렬한 눈빛이 {name}의 전투적인 기질과 닮았습니다",

    # 색상 근거
    'color_blue':         "차분하고 깊은 분위기가 물 타입인 {name}와 잘 어울립니다",
    'color_yellow':       "밝고 에너지 넘치는 느낌이 전기 타입인 {name}와 잘 어울립니다",
    'color_red':          "열정적인 에너지가 불꽃 타입인 {name}와 어울립니다",
}


def generate_reasons(features: dict, pokemon: dict, max_reasons: int = 3) -> list[str]:
    """
    사람 특징과 매칭된 포켓몬을 비교하여 납득 가능한 근거 문장 생성
    """
    reasons = []
    name = pokemon['name_ko']

    # 눈 크기
    if features['eye_size_ratio'] > 0.6:
        reasons.append(REASON_TEMPLATES['eye_size_large'].format(name=name))
    elif features['eye_size_ratio'] < 0.3:
        reasons.append(REASON_TEMPLATES['eye_size_small'].format(name=name))

    # 눈꼬리 각도
    if features['eye_slant_angle'] > 10:
        reasons.append(REASON_TEMPLATES['eye_slant_up'].format(name=name))
    elif features['eye_slant_angle'] < -10:
        reasons.append(REASON_TEMPLATES['eye_slant_down'].format(name=name))

    # 미간
    if features['eye_distance_ratio'] > 0.6:
        reasons.append(REASON_TEMPLATES['eye_distance_wide'].format(name=name))

    # 얼굴형
    if features['face_aspect_ratio'] < 0.65:
        reasons.append(REASON_TEMPLATES['face_long'].format(name=name))
    elif features['face_aspect_ratio'] > 0.85:
        reasons.append(REASON_TEMPLATES['face_round'].format(name=name))

    # 스타일 (최우선)
    if features['has_glasses']:
        reasons.insert(0, REASON_TEMPLATES['glasses'].format(name=name))
    if features['has_facial_hair']:
        reasons.insert(0, REASON_TEMPLATES['facial_hair'].format(name=name))
    if features['has_bangs']:
        reasons.append(REASON_TEMPLATES['bangs'].format(name=name))

    # 웃음
    if features['smile_score'] > 0.65:
        reasons.append(REASON_TEMPLATES['smile_high'].format(name=name))

    # 색상 기반 근거
    color = classify_color(features.get('dominant_color', '#808080'))
    color_key = f'color_{color}'
    if color_key in REASON_TEMPLATES:
        reasons.append(REASON_TEMPLATES[color_key].format(name=name))

    # 중복 제거 후 최대 3개 반환
    seen = set()
    unique_reasons = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            unique_reasons.append(r)

    return unique_reasons[:max_reasons]
```

---

## 5. 전체 실행 흐름 (메인 함수)

```python
def find_matching_pokemon(face_features: dict, k: int = 3) -> list[dict]:
    """
    사람 얼굴 특징 → Top-K 포켓몬 매칭 메인 함수

    Args:
        face_features: User_Face_Features 테이블 기반 딕셔너리
        k: 반환할 포켓몬 수 (기본 3)

    Returns:
        [
            {
                "rank": 1,
                "pokemon_id": 196,
                "name_ko": "에브이",
                "types": ["에스퍼"],
                "final_score": 0.84,
                "type_score": 0.82,
                "stat_similarity": 0.87,
                "reasons": ["안경을 쓴 지적인 분위기가...", ...]
            },
            ...
        ]
    """

    # 타입 점수 초기화 (18개 타입)
    type_scores = {
        '노말': 0, '불꽃': 0, '물': 0, '전기': 0, '풀': 0, '얼음': 0,
        '격투': 0, '독': 0, '땅': 0, '비행': 0, '에스퍼': 0, '벌레': 0,
        '바위': 0, '고스트': 0, '드래곤': 0, '악': 0, '강철': 0, '페어리': 0
    }

    # Step 1: 타입 점수 계산 (4개 규칙 순차 적용)
    type_scores = apply_critical_rules(face_features, type_scores)  # 안경/수염 등
    type_scores = apply_eye_rules(face_features, type_scores)       # 눈/눈썹
    type_scores = apply_face_shape_rules(face_features, type_scores) # 얼굴형
    type_scores = apply_color_rules(face_features, type_scores)      # 색상 (50% 반영)
    type_scores = apply_emotion_rules(face_features, type_scores)    # 감정 (보조)

    # Step 2: 스탯 프로파일 계산
    stat_profile = build_stat_profile(face_features)

    # Step 3: DB 매칭 (타입 60% + 스탯 40%)
    top_k_pokemon = match_pokemon(type_scores, stat_profile, k=k)

    # Step 4: 근거 문장 생성
    results = []
    for rank, match in enumerate(top_k_pokemon, start=1):
        reasons = generate_reasons(face_features, match['pokemon'])
        results.append({
            "rank":           rank,
            "pokemon_id":     match['pokemon'].id,
            "name_ko":        match['pokemon'].name_ko,
            "types":          get_pokemon_types(match['pokemon'].id),
            "final_score":    round(match['final_score'], 3),
            "type_score":     round(match['type_score'], 3),
            "stat_similarity":round(match['stat_similarity'], 3),
            "reasons":        reasons,
            "image_url":      match['pokemon'].image_url,
        })

    return results
```

---

## 6. 매핑 규칙 요약표 (팀 참고용)

| 사람 특징 | 조건 | 타입 가산점 | 스탯 영향 |
|----------|------|----------|---------|
| `has_glasses` | True | 에스퍼+50, 전기+35, 강철+30 | SP.ATK ↑ |
| `has_facial_hair` | True | 격투+50, 바위+40, 땅+35 | ATK ↑ |
| `has_bangs` | True | 풀+40, 비행+30 | — |
| `eye_slant_angle` | > 15 | 악+45, 격투+35, 불꽃+25 | ATK ↑, SPD ↑ |
| `eye_slant_angle` | < -15 | 페어리+45, 노말+35, 물+20 | SP.DEF ↑ |
| `eye_size_ratio` | > 0.7 | 페어리+40, 에스퍼+20 | SP.ATK ↑ |
| `eye_size_ratio` | < 0.3 | 강철+25, 악+15 | ATK ↑ |
| `eye_distance_ratio` | > 0.65 | 물+35, 풀+25 | SP.DEF ↑ |
| `eyebrow_thickness` | > 0.6 | 격투+30, 바위+25 | ATK ↑ |
| `face_aspect_ratio` | > 0.85 | 노말+25, 땅+20 | HP ↑, DEF ↑ |
| `face_aspect_ratio` | < 0.65 | 에스퍼+25, 비행+20 | SPD ↑ |
| `jawline_angle` | > 70 | 격투+30, 강철+25 | ATK ↑, DEF ↑ |
| `smile_score` | > 0.7 | 페어리+25, 노말+20 | — |
| `dominant_color` | 파랑 | 물+50 | SP.DEF ↑ |
| `dominant_color` | 노랑 | 전기+45 | SPD ↑ |
| `dominant_color` | 초록 | 풀+50 | — |
| `dominant_color` | 빨강 | 불꽃+40 | ATK ↑ |
| `dominant_color` | 보라 | 에스퍼+45, 독+30 | SP.ATK ↑ |

---

## 7. 주의사항 및 튜닝 가이드

```
1. 가중치 수치는 모두 초안입니다.
   팀원 20명 이상의 얼굴로 테스트 후 수치 조정이 필요합니다.

2. 타입 점수 합산 시 상한(Cap)을 설정하세요.
   동일 타입에 여러 규칙이 쌓이면 200점 이상이 될 수 있습니다.
   → 각 타입 최대 점수: 150점으로 cap 처리 권장

3. 매핑 결과가 "이상한" 경우의 기준을 팀이 사전에 정의해야 합니다.
   예: 귀여운 얼굴인데 드래곤 타입이 나오면 → 이상한 결과

4. has_glasses, has_facial_hair는 결정적 규칙이므로
   다른 규칙보다 먼저 적용되고 가중치가 높아야 합니다.

5. 색상/감정 규칙은 보조 수단입니다.
   메인 규칙(눈/얼굴형/스타일)이 충분할 경우 비중을 낮추세요.
```

---

*이 초안을 기반으로 팀이 협의하여 최종 규칙을 확정하고, 테스트 케이스를 통해 수치를 조정해주세요.*
