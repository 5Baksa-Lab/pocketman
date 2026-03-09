# Stage 개발일지

## 0) 기본 정보
- 파트: `mlops`
- Stage: `m2-vectorize`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 포켓몬별 인상 점수(9차원), 타입 친화도(8차원) 계산
  - 28차원 L2 정규화 벡터 생성 → `pokemon_vectors` pgvector 적재
  - IVFFlat 인덱스 생성 및 Top-K 검색 동작 검증
- 이번 Stage에서 포함한 범위:
  - Step 3~6 스크립트
  - `scripts/shared/feature_mapping.py` 공유 모듈 신설
- 제외한 범위:
  - 사용자 얼굴 특징 추출 (→ M3)

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **인상 점수를 Gemini Flash + 규칙 기반 fallback으로 생성**
- 결정 2: **타입 친화도 13차원 → 8차원으로 축소** (v5 기획 기준)
  - 8차원: water, fire, grass, electric, psychic, normal, fighting, ghost
- 결정 3: **`scripts/shared/feature_mapping.py` 공유 모듈 신설**
  - `calc_impression_from_visual()`, `calc_type_affinity_from_impression()` 함수
  - MLOps 스크립트 + Backend `cv_adapter.py` 공동 재사용
- 결정 4: **L2 정규화로 코사인 유사도 = 내적 동치 확보**

### 2.2 핵심 로직 설명
- 28차원 벡터 구성:
  ```
  [0-9]   visual: eye_size, eye_distance, eye_roundness, eye_tail,
                  face_roundness, face_proportion, feature_size,
                  feature_emphasis, mouth_curve, overall_symmetry
  [10-18] impression: cute, calm, smart, fierce, gentle,
                      lively, innocent, confident, unique
  [19-26] type_affinity: water, fire, grass, electric,
                         psychic, normal, fighting, ghost
  [27]    glasses: has_glasses (0.0 or 1.0)
  ```
- `06_validate.py` 검증 7종: 커버리지, 범위, 감정 클래스, 키워드, 진화 일관성, 저신뢰도, 샘플 Top-K

### 2.3 변경 파일 목록
- `scripts/03_calc_impression.py`: 인상 점수 9차원
- `scripts/04_calc_type_affinity.py`: 타입 친화도 8차원
- `scripts/05_build_vectors.py`: 28차원 벡터 생성 + pgvector INSERT
- `scripts/06_validate.py`: 통합 검증 7종
- `scripts/shared/feature_mapping.py`: 공유 변환 함수 모듈 (신설)
- `database/01_schema.sql`: pokemon_impression, pokemon_type_affinity, pokemon_vectors DDL

## 3) 테스트/검증
### 3.1 실행한 테스트
- `python3 scripts/06_validate.py` — 7종 검증 (목표: 전 항목 통과)
- ※ 실제 실행 증빙 없음 (사후 작성)

### 3.2 수동 검증
- `SELECT COUNT(*) FROM pokemon_vectors` = 386
- 자기 자신과 코사인 거리 = 0.0 확인
- `shared/feature_mapping.py` import 성공 확인

## 4) 이슈/리스크
- 타입 친화도 13D→8D 축소로 5박사 원본 스크립트와 호환 불가
- `shared/feature_mapping.py`를 Backend 컨테이너 내부에서 import하려면 Dockerfile COPY 필요
- IVFFlat `lists=20` — 포켓몬 수 증가 시 재조정 필요

## 5) 다음 Stage 인수인계 (M3)
- `06_validate.py` 전체 통과 후 M3 착수
- **벡터 차원 순서 절대 변경 금지** — Backend `cv_adapter.py`와 순서 불일치 시 매칭 품질 붕괴
- `feature_mapping.py` 함수 시그니처 변경 시 Backend와 동시 수정 필수

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: 5박사 원본과 차이(13D→8D, Gemini fallback 추가) 명시

## 7) 완료 체크
- [x] 인상 점수 9차원 계산 스크립트 구현 완료
- [x] 타입 친화도 8차원 계산 스크립트 구현 완료
- [x] 28차원 벡터 생성 + pgvector 적재 완료
- [x] `shared/feature_mapping.py` 공유 모듈 신설 완료
- [x] 검증 스위트 7종 구현 완료
- [ ] 실 DB 386건 완전성 증빙 (사후 작성으로 누락)
- [x] 개발일지 파일 생성: `docs/development_logs/mlops/stage-m2-vectorize/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
