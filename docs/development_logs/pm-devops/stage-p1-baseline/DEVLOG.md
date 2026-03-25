# Stage 개발일지

## 0) 기본 정보
- 파트: `pm-devops`
- Stage: `p1-baseline`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 파트 간 공통 기준선(스키마, API 명세, 인프라)을 동결하여 병렬 개발 병목 제거
  - Docker 기반 로컬 실행 환경 확립
  - 브랜치/PR 협업 규칙 및 개발일지 정책 고지
- 이번 Stage에서 포함한 범위:
  - PostgreSQL + pgvector 기반 DB 스키마 확정 (`database/01_schema.sql`)
  - Docker Compose 서비스 구성 (`docker-compose.yml`)
  - 공통 응답/에러 포맷 확정 (`backend/app/core/schemas.py`)
  - 환경변수 키셋 정의 및 공지
  - 개발 규칙 문서 배포 (`docs/develop_rule/`)
- 제외한 범위:
  - CI/CD 파이프라인 자동화 (→ P2)
  - 실제 배포 환경(Railway/Vercel) 구성
  - 인증/인가 설계

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **Schema First 원칙 적용**
  - 28차원 벡터 구조(`visual 10d + impression 9d + type_affinity 8d + glasses 1d`)를 Day 1 동결
  - `database/01_schema.sql` 단일 파일이 전체 파트의 데이터 계약 원장
- 결정 2: **pgvector/pg17 기반 컨테이너 선택**
  - `pgvector/pgvector:pg17` 이미지로 PostgreSQL 17 + pgvector 확장 동시 제공
- 결정 3: **공통 응답 Envelope 확정**
  - 모든 API 응답: `{ "success": bool, "data": ..., "error_code": str }` 구조
- 결정 4: **USE_MOCK_AI 피처 플래그 도입**
  - 외부 AI API 없이도 전 파트 병렬 개발 가능하도록 환경변수 토글 제공

### 2.2 핵심 로직 설명
- 로직 A: DB 스키마 구조 (`database/01_schema.sql`) — 10개 테이블:
  - `pokemon_master` → 386마리 기본 정보 (Gen 1-3)
  - `pokemon_stats` → PokeAPI 기본 스탯 6종
  - `pokemon_visual` → Gemini Vision 기반 시각 스코어 10차원
  - `pokemon_impression` → 인상 스코어 9차원
  - `pokemon_type_affinity` → 타입 친화도 8차원
  - `pokemon_vectors` → 28차원 L2 정규화 벡터 (pgvector, IVFFlat 인덱스)
  - `user_face_features` → 사용자 얼굴 특징 PoC 저장용
  - `creatures` → 생성 크리처 JSONB 기반 저장
  - `veo_jobs` → 비동기 영상 생성 상태 추적
  - `reactions` → 이모지 리액션
- 로직 B: Docker Compose (`docker-compose.yml`)
  - `db` 서비스: pgvector/pg17, 헬스체크(`pg_isready`), 볼륨 영속화
  - `backend` 서비스: `depends_on: db(healthy)` 조건부 기동
- 로직 C: 환경변수 키셋 (`backend/app/core/config.py`)
  - `DATABASE_URL`, `USE_MOCK_AI`, `GEMINI_API_KEY`, `GEMINI_FLASH_MODEL`
  - `IMAGEN_API_URL`, `VEO_API_URL`
  - `AI_REQUEST_TIMEOUT_SEC=30`, `AI_MAX_RETRIES=2`, `AI_RETRY_BASE_DELAY_SEC=0.8`
  - `TOP_K=3`, `VECTOR_DIM=28`

### 2.3 변경 파일 목록
- `database/01_schema.sql`: v5 최종 통합 스키마 (10개 테이블, pgvector 인덱스 포함)
- `docker-compose.yml`: DB + Backend 컨테이너 의존성/헬스체크 정의
- `backend/app/core/config.py`: 환경변수 로딩 및 상수 정의
- `backend/app/core/schemas.py`: 공통 응답 Envelope DTO 확정
- `backend/app/core/errors.py`: 표준 에러 코드 및 예외 클래스 정의
- `docs/develop_rule/`: 개발 규칙 문서 전체 배포
- `docs/기획/프로젝트_기획안_v5_최종확정.md`: 최종 기획 확정본

## 3) 테스트/검증
### 3.1 실행한 테스트
- 테스트 항목: Docker Compose 기동 및 DB 스키마 적용 확인
- 실행 방법:
  ```bash
  docker compose up -d
  docker exec -i pocketman-db psql -U pocketman -d pocketman < database/01_schema.sql
  docker exec pocketman-db psql -U pocketman -d pocketman -c "\dt"
  ```
- 결과: 10개 테이블 생성 확인 (※ 사후 작성 — 실제 증빙 없음)

### 3.2 수동 검증
- 시나리오 1: `01_schema.sql` 테이블 10종이 계획서(v5 §10)와 1:1 일치 확인
- 시나리오 2: docker-compose 헬스체크 `condition: service_healthy` 확인
- 시나리오 3: `config.py` 환경변수 키셋이 `docker-compose.yml` environment 블록과 일치 확인

## 4) 이슈/리스크
- 잔여 리스크:
  - `CORS allow_origins=["*"]` — 배포 전 제한 필요
  - `.env` 파일에 실제 API 키 포함 가능성 — `.gitignore` 적용 확인 필요
  - 인증/인가 미설계 — 모든 write API 공개 상태
  - `USE_MOCK_AI` 운영 실수 설정 위험

## 5) 다음 Stage 인수인계 (P2)
- P2에서 바로 해야 할 일:
  - GitHub Actions CI 구성 (Python lint/compile, frontend lint/build)
  - `/api/v1/health` 스모크 테스트 자동화
- 주의할 점:
  - `database/01_schema.sql`은 계약 원장 — 변경 시 RFC 프로세스 필수
  - 응답 Envelope 구조 변경 시 Frontend `lib/api.ts` 동시 수정 필요

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 핵심 프롬프트 요약: 코드베이스 전체 분석 후 개발일지 사후 작성
- 생성 결과 중 채택한 부분: 스키마 구조, 환경변수 키셋, 리스크 목록
- 수동 수정한 부분: 실제 파일명/경로 확인 후 보정

## 7) 완료 체크
- [x] DB 스키마 확정 완료
- [x] Docker Compose 구성 완료
- [x] 환경변수 키셋 정의 완료
- [x] 공통 응답 Envelope 확정 완료
- [x] 개발 규칙 문서 배포 완료
- [ ] 실제 Docker 기동 증빙 첨부 (사후 작성으로 누락)
- [x] 개발일지 파일 생성: `docs/development_logs/pm-devops/stage-p1-baseline/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
