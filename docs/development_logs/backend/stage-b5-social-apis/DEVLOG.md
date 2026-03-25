# Stage 개발일지

## 0) 기본 정보
- 파트: `backend`
- Stage: `b5-social-apis`
- 작성자: `Claude (PM + Tech Lead)`
- 작성일: `2026-03-13`
- 관련 이슈/PR: `N/A`

## 1) Stage 목표/범위
- 목표: F3-1 프론트엔드를 위한 백엔드 소셜 API 전체 구현
- 포함 범위:
  - DB 마이그레이션 002~005
  - creatures 상세 조회 (소유자, 좋아요 포함)
  - 좋아요 추가/제거
  - 댓글 CRUD
  - 마이페이지 API (내 크리처, 좋아요한 크리처)
  - 유저 프로필 조회/수정, 비밀번호 변경, 계정 삭제
  - 닉네임 중복 확인

## 2) 구현 상세

### 2.1 DB 마이그레이션

| 파일 | 내용 |
|------|------|
| `migrations/002_add_user_id_to_creatures.sql` | `creatures.user_id UUID NULLABLE FK → users` |
| `migrations/003_create_likes.sql` | `likes(user_id, creature_id) UNIQUE` |
| `migrations/004_create_comments.sql` | `comments(creature_id, user_id, content VARCHAR(100))` |
| `migrations/005_add_users_columns.sql` | `users` 에 `bio`, `avatar_creature_id`, `dark_mode`, `font_size` 추가 |

### 2.2 핵심 설계/의사결정

**결정 1: creatures.user_id nullable**
- 기존 anonymous 크리처 하위 호환성 유지
- 새 크리처: optional auth로 token 있으면 user_id 저장

**결정 2: GET /creatures/{id} — optional auth**
- 비로그인: is_liked=false, owner 정보 포함
- 로그인: is_liked 실제 상태 반환
- 비공개 크리처 비소유자 접근 → 404 (403 아닌 이유: 정보 노출 방지)

**결정 3: FastAPI 라우트 순서**
- Static routes (`/creatures/public`, `/creatures/my`, `/creatures/liked`) 반드시 dynamic route (`/creatures/{creature_id}`) 앞에 등록
- 미준수 시 "my", "liked" 문자열이 creature_id로 파싱됨

**결정 4: PATCH /creatures/{id} ownership check**
- `creature.user_id IS NULL` → 하위 호환 허용 (누구나 패치 가능)
- `creature.user_id IS NOT NULL` → 소유자만 패치 가능
- 소유자 불일치 → 403 ForbiddenError

**결정 5: 좋아요 구현 — ON CONFLICT DO NOTHING**
- `INSERT INTO likes ... ON CONFLICT DO NOTHING`
- 중복 좋아요 무시, 정확한 like_count를 SELECT COUNT로 반환
- `DELETE FROM likes WHERE user_id=? AND creature_id=?` 후 COUNT 반환

### 2.3 신규/수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `migrations/002~005.sql` | 신규 | DB 스키마 확장 |
| `app/core/errors.py` | 수정 | ForbiddenError(403) 추가 |
| `app/core/schemas.py` | 수정 | 소셜 관련 스키마 20여 개 추가 |
| `app/repository/creature_repository.py` | 재작성 | user_id, likes JOIN, my/liked 목록 |
| `app/repository/comment_repository.py` | 신규 | 댓글 CRUD |
| `app/repository/user_repository.py` | 재작성 | 프로필 조회/수정, 비밀번호, 계정삭제 |
| `app/domain/creatures/creature_service.py` | 재작성 | optional auth, ownership, like toggle |
| `app/domain/comments/comment_service.py` | 신규 | 댓글 서비스 |
| `app/domain/users/user_service.py` | 신규 | 유저 서비스 |
| `app/api/v1/routers/creatures.py` | 재작성 | 전체 creatures 라우터 |
| `app/api/v1/routers/users.py` | 신규 | /users/* 라우터 |
| `app/main.py` | 수정 | users router 등록 |

## 3) 버그/이슈 기록

### 3.1 라우트 순서 문제 (예방)
- FastAPI는 선언 순서대로 매칭 — static route가 반드시 앞에 와야 함
- `/creatures/my` 가 뒤에 오면 `creature_id="my"` 로 파싱되어 404

### 3.2 ModuleNotFoundError 빌드 테스트 방법
- 루트 디렉토리에서 실행 시 `No module named 'app'` 오류
- 반드시 `cd backend && ../.venv/bin/python -c "from app.main import app"` 형태로 실행

## 4) 빌드 결과
```
✓ BACKEND OK (app.main import 성공)
```

## 5) 배포 전 필수 액션 (운영자)

```sql
-- Railway DB에서 순서대로 실행
\i migrations/002_add_user_id_to_creatures.sql
\i migrations/003_create_likes.sql
\i migrations/004_create_comments.sql
\i migrations/005_add_users_columns.sql
```

## 6) 다음 단계

- F3-2: Plaza Phaser.js 맵 구현 (백엔드: WebSocket endpoint 준비)
- F3-3: Socket.io 멀티플레이어 (백엔드: Redis pub/sub 또는 in-memory room)
