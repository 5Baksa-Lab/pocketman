# Stage 개발일지

## 0) 기본 정보
- 파트: `pm-devops`
- Stage: `p3-release-demo`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 사후 작성 / 미완료 Stage`

## 1) Stage 목표/범위
- 목표:
  - E2E 시나리오 3회 연속 성공으로 데모 준비 완료
  - 고심각도 리스크 처리 (CORS, 임시 파일 누수)
  - Plan A/B 전환 기준 점검
- ⚠️ **이 Stage는 아직 완료되지 않았습니다.**

## 2) 미완료 항목 현황

| 항목 | 우선순위 | 상태 |
|---|---|---|
| `cv_adapter.py` try/finally 수정 | 높음 | ✅ 완료 (2026-03-09) |
| CORS `allow_origins` 제한 | 높음 | ✅ 완료 (2026-03-09) |
| DB 커넥션 풀 구현 | 중간 | ✅ 완료 (2026-03-09) |
| Railway-only 런타임 정리 (Docker DB 제거) | 높음 | ✅ 완료 (2026-03-09) |
| 카카오톡 공유 결정 | 중간 | ❌ 미결정 |
| E2E 시나리오 3회 연속 성공 | 높음 | ❌ 미수행 |
| 이름 편집 서버 반영 | 낮음 | ❌ 미완 |

## 3) 잔여 즉시 처리 필요 수정 코드
- 현재 없음 (고심각도 즉시 수정 항목 3건 처리 완료)

## 4) E2E 데모 시나리오 (Plan A)
1. `http://localhost:3000` 접속
2. 정면 얼굴 사진 업로드
3. "매칭 시작" → 약 2초 후 Top-3 포켓몬 표시
4. 포켓몬 선택 → "내 크리처 만들기"
5. 이름/스토리/이미지 생성 (~10-15초) + Veo 폴링 (~1-3분)
6. 결과 화면 → URL 복사 또는 Twitter 공유
7. "광장에 등록" → `/plaza` 이동 → 이모지 리액션

## 5) Plan B 전환 기준

| 조건 | Plan B |
|---|---|
| Veo 완료율 70% 미만 | CSS 애니메이션 fallback 기본 모드 |
| Gemini/Imagen 쿼터 초과 | USE_MOCK_AI=true 전환 |
| DB 연결 불가 | Railway 상태 확인 + `DATABASE_URL` 재검증 + 스키마 재적용 |

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: 미완료 현황 표, 수정 코드 스니펫 직접 작성
- 사용한 AI(추가): Codex (GPT-5)
- 채택 내용: Railway-only compose 정리, CORS 환경변수화, 실행 문서 동기화

## 7) 완료 체크 (현재 미완)
- [x] cv_adapter.py try/finally 수정
- [x] CORS 제한
- [x] DB 커넥션 풀
- [x] Railway-only 런타임 정리 (docker-compose에서 DB 제거)
- [ ] E2E 시나리오 3회 연속 성공
- [ ] 카카오톡 공유 결정
- [x] 미완료 항목 + 수정 코드 문서화 완료
- [x] 개발일지 파일 생성: `docs/development_logs/pm-devops/stage-p3-release-demo/DEVLOG.md`
- [ ] PM/리드 리뷰 완료

## 8) 2026-03-09 추가 작업 기록 (Railway-only 전환)

### 작업 목표 및 범위
- 목표: 로컬 Docker DB 의존을 제거하고 Railway DB만 사용하도록 실행 경로 단일화
- 범위: compose/env/CORS 설정 + 실행 문서 동기화
- 제외: `cv_adapter.py` try/finally, `db.py` 커넥션 풀

### 구현 상세
- `docker-compose.yml`에서 `db` 서비스 및 `depends_on(db)` 제거
- Backend는 `.env`의 `DATABASE_URL`을 직접 사용하도록 단순화
- `backend/app/core/config.py`에 `ALLOWED_ORIGINS` CSV 파서 추가
- `backend/app/main.py` CORS를 `ALLOWED_ORIGINS`로 전환
- 루트 `.env.example` 추가, 기존 문서의 로컬 DB 절차를 Railway 기준으로 수정

### 변경 파일 목록
- `.env.example` (신규)
- `.gitignore`
- `docker-compose.yml`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/.env.example`
- `database/README.md`
- `scripts/README.md`
- `docs/common_rule/devops_qa_context.md`
- `docs/common_rule/frontend_context.md`
- `docs/ARCHITECTURE.md`

### 테스트/검증
- `python3 -m compileall backend/app` 통과
- Railway DB 연결 확인: `current_database=railway`, `vector/pgcrypto extension` 확인
- `docker compose config`는 로컬 환경에 Docker CLI 부재(`command not found`)로 미실행

### 이슈/리스크
- (기록 시점 기준) 고심각도 잔여 항목은 이후 섹션 9에서 처리 완료
- Railway 접속 시 프로젝트별로 SSL 요구사항이 다를 수 있어 `DATABASE_URL` 파라미터 확인 필요

## 9) 2026-03-09 추가 작업 기록 (Backend 안정화)

### 작업 목표 및 범위
- 목표: `cv_adapter.py` 임시파일 누수 제거 + `db.py` 커넥션풀 적용
- 범위: Backend adapter/core/repository 계층
- 제외: Rate Limiting, 인증/인가, Kakao 공유

### 구현 상세
- `backend/app/adapter/cv_adapter.py`
  - `extractor.extract(tmp_path)`를 `try/finally`로 감싸 예외 시에도 임시파일 삭제 보장
- `backend/app/core/db.py`
  - `ThreadedConnectionPool(min=2,max=10)` 도입
  - `get_connection()`은 pool에서 `getconn()` 반환
  - `release_connection()` 추가로 repository에서 반납 강제
  - pool 반환 전 `rollback()` 수행으로 트랜잭션 상태 누수 방지
- `backend/app/repository/*`
  - 기존 `conn.close()`를 `release_connection(conn)`으로 전환
  - 트랜잭션(commit/rollback) 로직은 유지

### 변경 파일 목록
- `backend/app/adapter/cv_adapter.py`
- `backend/app/core/config.py`
- `backend/app/core/db.py`
- `backend/app/repository/pokemon_repository.py`
- `backend/app/repository/creature_repository.py`
- `backend/app/repository/veo_job_repository.py`
- `.env.example`
- `backend/.env.example`

### 테스트/검증
- `python3 -m compileall backend/app` 통과
- 정적 확인:
  - `cv_adapter.py`에 `try/finally` + `os.unlink` 존재 확인
  - repository 전역 `conn.close()` 제거 및 `release_connection()` 반납 확인
- 제한사항:
  - 로컬 Docker CLI 부재로 통합 실행(`docker compose`) 검증 미수행

### 이슈/리스크
- 잔여 고심각도는 해소됨
- 남은 운영 리스크: E2E 3회 연속 검증 미수행, 카카오 공유 정책 미결정
