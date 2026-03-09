# Stage 개발일지

## 0) 기본 정보
- 파트: `backend`
- Stage: `b3-video-feed-stabilize`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - Veo 비동기 영상 생성 Job 상태 추적 API 구현
  - 광장(Plaza) 공개 피드 CRUD + 이모지 리액션 API 구현
- 이번 Stage에서 포함한 범위:
  - `routers/veo.py`, `domain/video/veo_job_service.py`, `repository/veo_job_repository.py`
  - `adapter/generation_adapter.py` Veo 연동 추가
  - `routers/creatures.py` 공개 피드 + 리액션 엔드포인트

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **Veo Job을 `veo_jobs` 테이블 상태 머신으로 관리**
  - 상태 전이: queued → running → succeeded / failed
- 결정 2: **광장 피드를 `creatures.is_public=true` 필터로 구현** (별도 피드 테이블 없음)
- 결정 3: **리액션을 `reactions` 테이블 원자적 카운터로 구현** (중복 허용)

### 2.2 핵심 로직 설명
- Veo Job API:
  - `POST /api/v1/veo-jobs` → queued 상태 생성
  - `GET /api/v1/veo-jobs/{id}` → 상태 조회
  - `PATCH /api/v1/veo-jobs/{id}` → 상태 업데이트
- 광장 피드: `SELECT * FROM creatures WHERE is_public=true ORDER BY created_at DESC LIMIT %s OFFSET %s`
- 리액션 추가: `INSERT INTO reactions (creature_id, emoji) VALUES (%s, %s)`
- 리액션 집계: `SELECT emoji, COUNT(*) FROM reactions WHERE creature_id=%s GROUP BY emoji`

### 2.3 변경 파일 목록
- `routers/veo.py`, `domain/video/veo_job_service.py`, `repository/veo_job_repository.py`
- `adapter/generation_adapter.py` (Veo 연동 추가)
- `routers/creatures.py`, `creature_service.py`, `creature_repository.py` (피드/리액션 추가)

## 3) 테스트/검증
- `python3 -m compileall -q backend/app/` → exit=0
- VeoJobResponse ↔ 프론트 types.ts VeoJob 필드 매칭 확인
- ※ Veo API 실 연동 테스트 미수행 (API 접근 미확보)

## 4) 이슈/리스크
- **Veo API 실 연동 불명확** — `VEO_API_URL` 값 미확정
- 광장 피드 LIMIT/OFFSET — 대량 데이터 시 성능 저하 (cursor 기반으로 마이그레이션 필요)
- Rate limiting 없음
- **카카오톡 공유 미구현** (기획서 §9-1 요구사항 미달)

## 5) 다음 Stage 인수인계 (P3)
- Rate limiting 미들웨어 추가
- DB 커넥션 풀 구현
- cv_adapter.py try/finally 수정 (반드시 처리)
- E2E 시나리오 테스트

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: Veo API 실 연동 불명확성 리스크, 카카오톡 미구현 명시

## 7) 완료 체크
- [x] Veo Job CRUD API 구현 완료
- [x] 광장 공개 피드 API 구현 완료
- [x] 이모지 리액션 + 집계 API 구현 완료
- [ ] Veo Real API 연동 (미완)
- [ ] Rate limiting (미완)
- [ ] 카카오톡 공유 (미완 — 기획 요구사항 미달)
- [x] 개발일지 파일 생성: `docs/development_logs/backend/stage-b3-video-feed-stabilize/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
