# Stage 개발일지

## 0) 기본 정보
- 파트: `backend`
- Stage: `b1-core-mock`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - Router-Service-Repository-Adapter 4계층 폴더 구조 확립
  - 공통 응답 Envelope, 에러 코드, 요청 로깅 미들웨어 구현
  - 프론트엔드가 Mock 응답으로 독립 개발할 수 있는 API 뼈대 제공
- 이번 Stage에서 포함한 범위:
  - 프로젝트 폴더 구조, `backend/app/core/`, `backend/app/main.py`, health router
- 제외한 범위:
  - 실제 CV 벡터 생성 (→ M3/B2), pgvector 실 검색 (→ B2), 생성 AI 연동 (→ B2/B3)

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **4계층 디렉토리 강제**
  ```
  api/v1/routers/  ← HTTP 입출력, 예외 변환만
  domain/          ← 비즈니스 로직
  adapter/         ← 외부 시스템 연동
  repository/      ← DB 쿼리
  core/            ← 설정, 스키마, 에러
  ```
- 결정 2: **공통 응답 Envelope**
  - 성공: `{ "success": true, "data": {...} }`
  - 실패: `{ "success": false, "error_code": "...", "message": "..." }`
- 결정 3: **request_id + duration_ms 로깅 표준화**
- 결정 4: **USE_MOCK_AI 피처 플래그**

### 2.2 핵심 로직 설명
- `main.py`: CORS, 라우터 5종 등록 (health, match, creatures, veo, generation)
- `core/schemas.py`: SuccessResponse, ErrorResponse, MatchResponse, CreatureResponse, VeoJobResponse, GenerationPipelineResponse, ReactionSummaryResponse
- `core/errors.py`: FaceNotDetectedError(422), MultipleFacesError(422), LowQualityError(422), VectorSearchError(500), NotFoundError(404), InvalidRequestError(400)
- `routers/health.py`: `GET /api/v1/health` → DB 통계 반환

### 2.3 변경 파일 목록
- `backend/app/main.py` (39줄), `core/config.py` (22줄), `core/schemas.py` (153줄), `core/errors.py` (57줄), `core/db.py` (17줄)
- `backend/app/api/v1/routers/health.py`
- `backend/requirements.txt`, `backend/Dockerfile`

## 3) 테스트/검증
- `python3 -m compileall -q backend/app/` → exit=0
- `GET /api/v1/health` Envelope 형식 확인

## 4) 이슈/리스크
- `allow_origins=["*"]` — 배포 전 제한 필요
- `db.py`가 요청마다 새 커넥션 (`psycopg2.connect`) — 커넥션 풀 미구현
- 단위 테스트 없음

## 5) 다음 Stage 인수인계 (B2)
- `match.py`, `creatures.py`, `generation.py`, `veo.py` 라우터 실제 로직 구현
- M3 산출물 (`scripts/user_poc/`, `scripts/shared/`) 준비 확인

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6

## 7) 완료 체크
- [x] 4계층 폴더 구조 확립 완료
- [x] 공통 응답 Envelope + 에러 코드 정의 완료
- [x] 헬스체크 엔드포인트 구현 완료
- [x] USE_MOCK_AI 인프라 완료
- [ ] 단위 테스트 없음 (B2로 이관)
- [x] 개발일지 파일 생성: `docs/development_logs/backend/stage-b1-core-mock/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
