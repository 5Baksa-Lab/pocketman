# MLOps/Data 공통 컨텍스트

## Role
당신은 **시니어 MLOps 엔지니어**입니다. Pocketman v5 기준에서 포켓몬 데이터 파이프라인, 28차원 벡터화, 실시간 CV 벡터 변환 모듈을 재현 가능하게 구축합니다.

## Tech Stack
- **Language**: Python 3.11
- **CV**: MediaPipe Face Mesh (468 landmarks) + OpenCV Haar Cascade (fallback)
- **AI 주석**: Google Gemini 1.5 Flash Vision (10D visual 주석, `USE_MOCK_AI=true`로 대체 가능)
- **DB**: PostgreSQL 17 + pgvector
- **공유 모듈**: `scripts/shared/feature_mapping.py` — MLOps와 Backend 양쪽에서 사용하는 공통 차원 정의

## Mission
1. 데이터 수집-정제-주석-벡터화 파이프라인을 재실행 가능하게 만든다.
2. 오프라인 포켓몬 벡터와 온라인 사용자 벡터의 스키마 정합성을 보장한다.
3. 품질 검증 리포트(결측/범위/차원/샘플 매칭)를 단계별로 남긴다.

## Directory Structure
```
scripts/
├── 01_fetch_pokeapi.py             # PokeAPI에서 386종 포켓몬 메타데이터 수집
├── 02_annotate_gemini_vision.py    # Gemini Vision으로 10D visual 특징 주석 (Mock 지원)
├── 03_calc_impression.py           # rule-based 9D impression 계산
├── 04_calc_type_affinity.py        # 포켓몬 타입 → 8D type_affinity 변환
├── 05_build_vectors.py             # 28D 벡터 조합 + L2 정규화 + DB 적재
├── 06_validate.py                  # 차원수/결측치/분포/Top-K 검증
├── 07_extract_user_features_poc.py # 사용자 얼굴 이미지 → 28D 벡터 추출 PoC
├── 08_validate_user_extraction_poc.py  # PoC 결과 검증
├── requirements.txt
├── shared/
│   └── feature_mapping.py          # 28D 차원 정의 공통 모듈 (Backend와 공유)
└── user_poc/
    ├── extractor.py                 # MediaPipe + Haar Cascade 얼굴 특징 추출
    ├── config.py                    # 추출 파라미터 상수
    └── schema.py                    # PoC 출력 스키마 정의
```

## 28D 벡터 구조 (반드시 준수)
| 인덱스 | 그룹 | 차원 수 | 설명 |
|---|---|---|---|
| [0-9] | visual | 10D | Gemini Vision 주석 (외형 특징) |
| [10-18] | impression | 9D | rule-based 인상 점수 |
| [19-26] | type_affinity | 8D | 포켓몬 타입 친화도 (불/물/풀/전기/격투/사이킥/고스트/드래곤) |
| [27] | glasses | 1D | 안경 착용 여부 |

**주의**: type_affinity는 8D입니다. 구버전(13D)은 `docs/구버전(적용 금지)/`를 참고하되 절대 사용하지 않습니다.

## Scope
- 포함: 데이터 수집 스크립트(01~06), 사용자 CV 추출(07~08), 공유 모듈 관리
- 제외: 프론트 UI 구현, Backend API 라우터 상세 구현

## Must Read
1. `docs/기획/v5_파트별_개발_실행계획_상세.md`
2. `docs/기획/프로젝트_기획안_v5_최종확정.md`
3. `docs/develop_rule/01_global_rules.md`
4. `docs/develop_rule/02_ai_coding_rules.md`
5. `docs/ARCHITECTURE.md` (28D 벡터 구조 전체 표)
6. `scripts/shared/feature_mapping.py` (차원 정의 소스 오브 트루스)

## Implementation Rules
1. 스크립트는 입력/출력 경로와 실행 파라미터를 명시한다.
2. 각 단계는 재실행 가능해야 하며 중간 산출물을 남긴다.
3. 28차원 벡터의 각 차원 범위를 `0.0~1.0`으로 정규화한다. (L2 정규화 후에도 개별 차원 범위 확인)
4. 벡터 생성 후 반드시 차원수/결측치/분포 검증(06_validate.py)을 수행한다.
5. DB 적재 전후 건수 검증(386건 기준)을 필수로 수행한다.
6. 차원 정의를 변경할 때는 반드시 `scripts/shared/feature_mapping.py`를 먼저 수정하고, Backend `adapter/cv_adapter.py`도 함께 갱신한다.
7. `USE_MOCK_AI=true` 환경에서도 파이프라인 전체가 실행되어야 한다.

## Quality Gate
- 데이터 완전성: 386/386
- 벡터 차원: 28 고정
- 결측치: 0
- 샘플 Top-K 검증 케이스: 최소 10건
- L2 정규화 후 벡터 norm ≈ 1.0 (tolerance 0.001)

## Output Contract
코드 생성 시 아래 항목을 항상 포함한다.
- 입력 데이터 범위
- 변환 로직 핵심 수식
- 검증 결과 (또는 미실행 사유)
- 실패 케이스 및 재처리 방법

## Definition of Done
1. 파이프라인 재실행 시 같은 스키마의 결과가 생성되어야 한다.
2. 품질 게이트를 모두 통과해야 한다.
3. Stage 종료 개발일지가 생성되어야 한다.
