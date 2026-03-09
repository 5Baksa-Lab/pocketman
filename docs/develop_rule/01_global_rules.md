# 전역 개발 규칙 (Global Rules)

## 1. 아키텍처 규칙

1. 계층 구조를 강제한다: `router → domain → repository → adapter`.
   - `router`: 입력 검증 + 응답 변환만 담당
   - `domain`: 비즈니스 로직 (matching, generation, creatures, video)
   - `repository`: DB 쿼리 전담 (SQL은 여기에만)
   - `adapter`: 외부 시스템 연동 (cv_adapter, generation_adapter)
2. 라우터에 비즈니스 로직을 작성하지 않는다.
3. 외부 API 호출(Gemini/Imagen/Veo/MediaPipe)은 `adapter` 계층에서만 수행한다.
4. 공통 스키마(28차원 벡터, API DTO) 변경은 RFC 승인 후 반영한다.
5. `scripts/shared/feature_mapping.py`는 MLOps와 Backend가 공유한다. 변경 시 양쪽 영향 반드시 확인.

## 2. 코드 품질 규칙

1. 함수 1개는 1개 책임만 수행한다.
2. 하드코딩 상수는 금지하고 설정/상수 모듈로 분리한다.
   - Backend: `app/core/config.py` (Settings)
   - MLOps: `scripts/user_poc/config.py`
   - Frontend: `NEXT_PUBLIC_API_URL` 환경변수
3. 중복 로직 2회 이상 발생 시 공통 모듈로 추출한다.
4. 파일 길이가 400줄을 초과하면 분할을 검토한다.
5. 신규 코드에는 최소 단위 테스트를 동반한다. (불가 시 `USE_MOCK_AI=true` 수동 검증으로 대체 가능하나 이유 명시)

## 3. 브랜치/PR 규칙

1. `main` 직접 푸시 금지. 작업은 `dev/<이름>` 또는 `feature/<파트>-<스테이지>-<이름>` 브랜치에서 수행.
2. PR은 기능 단위(1기능 1PR)로 나눈다.
3. PR 설명에는 `목적/변경/테스트/리스크`를 포함한다.
4. PR 본문에는 이전 Stage 개발일지 경로를 반드시 포함한다.
5. CI 실패 상태에서는 병합하지 않는다. (CI 미구축 기간에는 수동 smoke test 결과 첨부)

## 4. 테스트 규칙

1. Unit 테스트: 핵심 서비스/유틸 로직 (domain, repository).
2. Integration 테스트: API-DB-외부 어댑터 경계.
3. E2E 테스트: 업로드 → 매칭 → 생성 → 광장 공유 (핵심 경로).
4. 실패 케이스(타임아웃/빈값/외부API 오류) 테스트를 포함한다.
5. `USE_MOCK_AI=true` 환경에서도 전체 플로우가 동작해야 한다.

## 5. 로깅/관측성 규칙

1. 모든 주요 API에 `request_id`를 할당한다.
2. 단계별 `stage`, `duration_ms`, `success`, `error_code`를 기록한다.
3. 외부 API 호출(Gemini/Imagen/Veo)은 시작/종료/실패 로그를 남긴다.

## 6. 문서화 규칙

1. 설계 변경은 코드와 같은 PR에서 문서를 갱신한다.
2. Stage 종료 시 개발일지를 필수 작성한다.
3. 개발일지는 "무엇을/왜/어떻게"를 재현 가능 수준으로 남긴다.
4. 기술부채(TODO, 임시 우회코드)는 이유와 제거 시점을 명시한다.
