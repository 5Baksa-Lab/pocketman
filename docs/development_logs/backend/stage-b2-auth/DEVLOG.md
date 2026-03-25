# Stage 개발일지

## 0) 기본 정보
- 파트: `backend`
- Stage: `b2-auth`
- 작성자: `sups`
- 작성일: `2026-03-13`
- 관련 이슈/PR: N/A

## 1) Stage 목표/범위
- 목표: JWT 기반 이메일 인증 API 추가 (회원가입 / 로그인 / 내 정보)
- 이번 Stage에서 포함한 범위:
  - Railway PostgreSQL `users` 테이블 migration
  - `python-jose[cryptography]`, `passlib[bcrypt]` 패키지 추가
  - `AuthRegisterRequest`, `AuthLoginRequest`, `AuthUserResponse`, `AuthTokenResponse` 스키마 추가
  - `UnauthorizedError`, `ConflictError` 에러 클래스 추가
  - `user_repository.py` — create_user, get_user_by_email, get_user_by_id
  - `auth_service.py` — register_user, login_user, get_current_user (JWT 검증)
  - `auth.py` 라우터 — POST /auth/register, POST /auth/login, GET /auth/me
  - `main.py` — auth router 등록
  - `.env`, `config.py` — JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_HOURS 추가
- 제외한 범위:
  - Refresh Token (F3 보안 고도화)
  - 소셜 로그인 OAuth (F3)
  - 비밀번호 변경/재설정 (F3)
  - creature.user_id 연결 (F3 — 현재 ownership 미검증 상태 유지)

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: Access Token only (24h), Refresh Token 없음**
- Refresh Token은 별도 저장소(Redis/DB) 필요 → F2 MVP 범위 초과
- 24h 만료로 보안과 편의성 균형 확보
- 재로그인이 필요한 경우 UX 영향 낮음 (세션 기반 서비스 특성)

**결정 2: JWT 페이로드 최소화 (`sub`만 포함)**
- `sub`: user_id (UUID)만 포함
- 매 요청마다 `get_user_by_id()`로 최신 유저 정보 조회
- 이유: 닉네임 변경 등 유저 정보 변경 시 토큰 재발급 불필요

**결정 3: nickname 필드 (name 아님)**
- 프론트엔드 `AuthRegisterPayload`와 일치시켜 통일
- DB 컬럼: `nickname VARCHAR(50) NOT NULL`

**결정 4: `Header(default=None)` 방식 (FastAPI Depends 미사용)**
- `GET /auth/me`에서 `Authorization: str | None = Header(default=None)` 직접 주입
- 이유: 다른 엔드포인트는 인증 불필요 — Depends 전역 설정 대신 명시적 적용
- F3에서 소유권 검증 시 Depends 방식으로 전환 예정

### 2.2 핵심 로직 설명

**register_user():**
1. `get_user_by_email()` 중복 체크 → 존재 시 `ConflictError(409)`
2. `bcrypt` 해싱 → `create_user()` INSERT
3. JWT 생성 → `AuthTokenResponse` 반환 (자동 로그인)

**login_user():**
1. `get_user_by_email()` 조회
2. `passlib.verify()` 비밀번호 검증 → 실패 시 `UnauthorizedError(401)`
3. JWT 생성 → `AuthTokenResponse` 반환

**get_current_user():**
1. `Authorization: Bearer {token}` 헤더 파싱
2. `jose.jwt.decode()` 검증 → 실패 시 `UnauthorizedError(401)`
3. payload.sub(user_id)로 `get_user_by_id()` 조회 → `AuthUserResponse` 반환

### 2.3 변경 파일 목록

- `.env`: JWT_SECRET_KEY 추가
- `backend/requirements.txt`: python-jose[cryptography]==3.3.0, passlib[bcrypt]==1.7.4 추가
- `backend/migrations/001_create_users.sql`: 신규 (migration 버전관리)
- `backend/app/core/config.py`: JWT_SECRET_KEY(누락 시 RuntimeError), JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_HOURS 추가
- `backend/app/core/errors.py`: UnauthorizedError, ConflictError 추가
- `backend/app/core/schemas.py`: Auth 스키마 4개 추가
- `backend/app/repository/user_repository.py`: 신규
- `backend/app/domain/auth/__init__.py`: 신규
- `backend/app/domain/auth/auth_service.py`: 신규
- `backend/app/api/v1/routers/auth.py`: 신규
- `backend/app/main.py`: auth router include 추가

**코드 리뷰 수정 (2차):**
- `auth_service.py`: psycopg2.errors.UniqueViolation → ConflictError(409) race condition 대응
- `auth_service.py`: _normalize_email() — strip().lower() 정규화 전체 적용
- `auth_service.py`: Bearer 대소문자 case-insensitive 파싱 (RFC 7235 준수)
- `config.py`: JWT_SECRET_KEY 누락 시 RuntimeError 즉시 발생 (기본값 풋건 제거)
- `backend/migrations/001_create_users.sql`: migration DDL 버전관리 추가

## 3) 테스트/검증

### 3.1 빌드 테스트

```bash
cd backend && USE_MOCK_AI=true ../.venv/bin/python -c "from app.main import app; print('OK')"
# → OK
```

### 3.2 라우트 등록 확인

```
{'POST'} /api/v1/auth/register
{'POST'} /api/v1/auth/login
{'GET'}  /api/v1/auth/me
```

### 3.3 DB migration 확인

```sql
SELECT COUNT(*) FROM users;  -- 0 (정상)
```

### 3.4 미검증 항목
- 실서버 회원가입/로그인 엔드-투-엔드 (F2-E 프론트 연동 시 검증)
- bcrypt 해싱 성능 (서버 부하 테스트 미수행)

## 4) 이슈/리스크

| 항목 | 내용 | 대응 |
|------|------|------|
| JWT_SECRET_KEY 임시값 | 현재 임의 생성 값 사용 | 팀원 협의 후 Railway 환경변수로 교체 |
| Refresh Token 없음 | 24h 후 재로그인 필요 | F3에서 Refresh Token 추가 |
| creature.user_id 미연결 | 크리처 소유권 미검증 상태 | F3에서 user_id 컬럼 추가 후 403 연동 |
| 비밀번호 변경/재설정 없음 | 비번 분실 시 방법 없음 | F3에서 추가 |

## 5) 다음 Stage 인수인계

- 다음 작업: F2-E — `/login`, `/signup` 페이지 구현
- 주의할 점:
  - POST /auth/register 성공 응답 status_code=201 (다른 엔드포인트와 다름)
  - AuthGateModal에서 `/login?next={경로}` 파라미터 처리 필요
  - `AUTH_USER` 응답 구조: `{ access_token, token_type, user: { id, email, nickname, created_at } }`

## 6) AI 활용 기록

- 사용한 AI: Claude Sonnet 4.6 (Claude Code)
- 역할: 전체 코드 작성 (B-2 Auth 백엔드)
- 사람이 결정한 것: nickname/name 필드명, Access Token only 정책

## 7) 완료 체크

- [x] users 테이블 Railway DB migration
- [x] python-jose, passlib 패키지 설치
- [x] JWT 설정 (.env, config.py)
- [x] UnauthorizedError, ConflictError 추가
- [x] Auth 스키마 4개 추가
- [x] user_repository.py (create, get_by_email, get_by_id)
- [x] auth_service.py (register, login, get_current_user)
- [x] auth.py 라우터 (register, login, me)
- [x] main.py auth router 등록
- [x] 빌드 테스트 통과 (import OK)
- [x] 라우트 등록 확인 (3개)
- [x] 개발일지 작성
- [ ] PM/리드 리뷰 완료
