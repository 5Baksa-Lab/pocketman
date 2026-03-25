# database/

## 파일 구성

| 파일 | 설명 |
|------|------|
| `01_schema.sql` | 전체 DB 스키마 (유일한 DDL 파일) |

## 01_schema.sql 테이블 목록

| # | 테이블 | 역할 | 데이터 소스 |
|---|--------|------|------------|
| 1 | `pokemon_master` | 포켓몬 기본 정보 (이름, 타입, 세대 등) | PokeAPI 배치 수집 |
| 2 | `pokemon_stats` | 6개 능력치 (HP, 공격, 방어 등) | PokeAPI 배치 수집 |
| 3 | `pokemon_visual` | 시각 특징 10차원 스코어 | Gemini Vision 주석 |
| 4 | `pokemon_impression` | 인상/성격 점수 9차원 | 규칙 기반 자동 계산 |
| 5 | `pokemon_type_affinity` | 타입 친화도 8차원 | 룰 기반 자동 계산 |
| 6 | `pokemon_vectors` | 28차원 통합 벡터 (pgvector) | Steps 2~5 산출물 |
| 7 | `user_face_features` | 사용자 얼굴 특징 원시값 | MediaPipe 추출 |
| 8 | `creatures` | 사용자 생성 크리처 결과 | `/match` 선택 결과 저장 |
| 9 | `veo_jobs` | Veo 영상 생성 비동기 작업 상태 | 백엔드 생성 파이프라인 |
| 10 | `reactions` | 이모지 리액션 로그 | 광장 피드 상호작용 |

## 28차원 벡터 구성 (기획안 v5 §6-1)

```
[0-9]   visual 10차원  : eye_size, eye_distance, eye_roundness, eye_tail,
                         face_roundness, face_proportion, feature_size,
                         feature_emphasis, mouth_curve, overall_symmetry
[10-18] impression 9차원: cute, calm, smart, fierce, gentle,
                         lively, innocent, confident, unique
[19-26] type_affinity 8차원: water, fire, grass, electric,
                             psychic, normal, fighting, ghost
[27]    glasses 1차원   : 0.0 or 1.0
```

## DB 환경 구축 방법 (Railway-only)

```bash
# 1. Railway DATABASE_URL 설정
# 예: postgresql://postgres:<password>@<tcp-proxy-host>:<port>/railway
export DATABASE_URL="postgresql://postgres:<password>@<tcp-proxy-host>:<port>/railway"

# 2. 스키마 적용
psql "$DATABASE_URL" -f database/01_schema.sql

# 3. 파이프라인 실행 (데이터 채우기)
python scripts/01_fetch_pokeapi.py          # 포켓몬 기본 정보 수집
USE_MOCK_AI=true python scripts/02_annotate_gemini_vision.py  # 시각 특징 주석
python scripts/03_calc_impression.py        # 인상 점수 계산
python scripts/04_calc_type_affinity.py     # 타입 친화도 계산
python scripts/05_build_vectors.py          # 28차원 벡터 생성
```
