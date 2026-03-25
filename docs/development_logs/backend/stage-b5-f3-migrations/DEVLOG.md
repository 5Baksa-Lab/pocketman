# Stage 개발일지

## 0) 기본 정보
- 파트: `backend`
- Stage: `b5-f3-migrations`
- 작성자: `Claude (PM + Tech Lead)`
- 작성일: `2026-03-13`
- 관련 이슈/PR: `N/A`

## 1) Stage 목표/범위
- 목표: F3-1 소셜 기능을 위한 DB 스키마 확장 (마이그레이션 002~006 정식 적용)
- 이번 Stage에서 포함한 범위:
  - `backend/migrations/002_add_user_id_to_creatures.sql` — creatures 소유자 추적
  - `backend/migrations/003_create_likes.sql` — 좋아요 기능
  - `backend/migrations/004_create_comments.sql` — 댓글 기능
  - `backend/migrations/005_add_users_columns.sql` — 유저 프로필 확장
  - `backend/migrations/006_fix_constraints.sql` — 제약 조건 정정 (forward migration)
- 제외한 범위:
  - 백엔드 API 구현 (별도 Stage)
  - 프론트엔드 구현 (별도 Stage)

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: creatures.user_id nullable**
- 기존 anonymous 크리처 하위 호환 유지
- 새 크리처: optional auth 토큰 있으면 user_id 저장, 없으면 NULL
- `ON DELETE CASCADE` — 유저 탈퇴 시 해당 유저의 크리처 전체 삭제 (기획서 11_my.md:114)

**결정 2: likes UNIQUE(user_id, creature_id)**
- 동일 유저가 같은 크리처에 중복 좋아요 DB 레벨에서 차단
- 백엔드에서 `ON CONFLICT DO NOTHING` 패턴 활용 가능

**결정 3: comments.content VARCHAR(100)**
- 기획서 기준 최대 100자 제한
- 짧은 소통 중심 설계 (SNS 댓글 스타일)

**결정 4: users 확장 컬럼 기본값**
- `dark_mode BOOLEAN NOT NULL DEFAULT FALSE`
- `font_size SMALLINT NOT NULL DEFAULT 16 CHECK (font_size IN (14, 16, 18))` — 기획서 11_my.md:94-96 3단계 제한
- `bio`, `avatar_creature_id`: nullable (선택 입력)

### 2.2 핵심 로직 설명

**마이그레이션 순서 (의존성)**
```
001_create_users          (users 테이블 — 이미 적용됨)
  ↓
002_add_user_id_to_creatures  (creatures → users FK)
  ↓
003_create_likes              (users + creatures 모두 필요)
004_create_comments           (users + creatures 모두 필요)
  ↓
005_add_users_columns         (creatures → users FK avatar_creature_id)
```

### 2.3 변경 파일 목록

| 파일 | 변경 내용 |
|------|---------|
| `backend/migrations/002_add_user_id_to_creatures.sql` | creatures.user_id UUID nullable FK + 인덱스 |
| `backend/migrations/003_create_likes.sql` | likes 테이블 + UNIQUE 제약 + 인덱스 |
| `backend/migrations/004_create_comments.sql` | comments 테이블 + 인덱스 |
| `backend/migrations/005_add_users_columns.sql` | users bio/avatar_creature_id/dark_mode/font_size |

## 3) 테스트/검증

### 3.1 실행한 테스트
- USE_MOCK_AI=true 환경 기준
- 롤백 → 재적용 순서 검증 완료

### 3.2 검증 결과

```
✅ 롤백 (002~005 역순) 성공
✅ 마이그레이션 002 적용: creatures.user_id UUID nullable + ON DELETE CASCADE
✅ 마이그레이션 003 적용: likes 테이블 + UNIQUE(user_id, creature_id)
✅ 마이그레이션 004 적용: comments 테이블 + 복합 인덱스 (creature_id, created_at DESC)
✅ 마이그레이션 005 적용: users 프로필 컬럼 4개 + font_size CHECK(14,16,18)
✅ 인덱스 7개 확인 (idx_creatures_user_id, idx_likes_*, idx_comments_*)
✅ CHECK constraint chk_font_size 확인
✅ 백엔드 빌드: BACKEND OK
✅ 프론트엔드 빌드: 14 pages 성공
✅ uvicorn 서버 재시작: 정상 기동
```

### 3.4 코드 리뷰 후 수정 이력

| 리뷰 항목 | 심각도 | 수정 내용 |
|-----------|--------|----------|
| 002: ON DELETE SET NULL → CASCADE | High | 기획서 11_my.md:114 정책 반영 |
| 004: 단일 인덱스 → 복합 인덱스 (creature_id, created_at DESC) | Medium | 최신순 정렬 쿼리 최적화 |
| 005: font_size CHECK 제약 누락 | Medium | CHECK (font_size IN (14, 16, 18)) 추가 |
| API 매트릭스: 댓글 300자 → 100자 | Low | 04_api_alignment_matrix.md 469행 수정 |
| DEVLOG: 파일 경로 누락 | Low | migrations/... → backend/migrations/... |

### 3.3 DB 최종 스키마 상태

| 테이블 | 주요 변경 |
|--------|---------|
| creatures | user_id UUID nullable FK 추가 |
| likes | 신규 생성 (id, user_id, creature_id, created_at) |
| comments | 신규 생성 (id, creature_id, user_id, content, created_at) |
| users | bio, avatar_creature_id, dark_mode, font_size 추가 |

## 4) 이슈/리스크/미해결 항목

| 항목 | 상태 | 비고 |
|------|------|------|
| 마이그레이션 이력 관리 | 🟡 수동 | Alembic 등 마이그레이션 도구 미사용 — 추후 도입 검토 |
| 백엔드 서버 재시작 필요 | ✅ 완료 | 스키마 변경 후 uvicorn 재시작 완료 |

## 5) 다음 작업 인수인계

- **다음 Stage**: `b5-f3-social-api` — 새 스키마 기반 소셜 API 구현
  - `creature_repository.py` user_id 포함 쿼리
  - `comment_repository.py` 신규
  - `user_repository.py` 프로필 쿼리
  - 라우터 `/creatures`, `/users` 업데이트
- 마이그레이션 재실행 시: `IF NOT EXISTS` / `IF EXISTS` 구문으로 **컬럼·테이블 생성** 멱등성 보장
  - 단, 정책·제약 변경(FK 타입, CHECK 조건)은 IF NOT EXISTS로 보장되지 않음
  - 해당 변경은 `006_fix_constraints.sql` (DROP IF EXISTS → ADD 패턴)로 별도 처리

## 6) AI 활용 기록

- Claude Sonnet 4.6 활용
- 롤백 SQL 생성 및 적용 순서 검증
- 스키마 검증 쿼리 (`information_schema`) 작성
