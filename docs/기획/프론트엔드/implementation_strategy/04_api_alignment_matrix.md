# API 정렬 매트릭스 (기획 vs 구현)

> 마지막 업데이트: 2026-03-13
> 기준: 백엔드 실제 구현 코드 분석 완료 (schemas.py / routers/*.py / creature_repository.py)
> F2 신규 API (PATCH creatures + Auth), F3 신규 API 스펙 확정 반영

---

## 1. 우선 기준

- 기준은 "현재 동작 가능한 API"를 우선으로 삼는다.
- 기획 전용 API는 `신규 추가 필요`로 분리하고 담당 Stage를 명시한다.
- API가 변경되면 이 문서를 먼저 수정 → Stage 문서 반영 → 페이지 설계 문서 반영 순서를 지킨다.
- 모든 API URL 앞에 `/api/v1` 접두사가 붙는다.

---

## 2. 공통 응답 구조 (확정)

**성공 응답:**
```json
{
  "success": true,
  "request_id": "8자 UUID",
  "duration_ms": 123,
  "data": { /* 엔드포인트별 */ }
}
```

**실패 응답:**
```json
{
  "success": false,
  "error_code": "대문자_스네이크_케이스",
  "message": "사용자 친화적 메시지"
}
```

**인증 헤더 (F2 이후 보호 엔드포인트):**
```
Authorization: Bearer {access_token}
```

---

## 3. 구현 완료 API 목록 (사용 가능)

> 백엔드 코드(`schemas.py`, `routers/*.py`) 기준으로 응답 DTO 전수 검증 완료.

| Method | Path | 설명 | 사용 Stage | 인증 필요 |
|--------|------|------|-----------|-----------|
| GET | `/health` | 서버 헬스 체크 | — | N |
| POST | `/match` | 얼굴 → Top3 매칭 | F1 | N |
| POST | `/creatures` | 크리처 레코드 생성 | F2 | N |
| GET | `/creatures/public` | 공개 크리처 목록 | F1(샘플), F3 | N |
| GET | `/creatures/{id}` | 크리처 상세 조회 | F2, F3 | N |
| POST | `/creatures/{id}/generate` | 생성 파이프라인 트리거 | F2 | N |
| POST | `/creatures/{id}/reactions` | 이모지 리액션 추가 | F3 | N |
| GET | `/creatures/{id}/reactions/summary` | 리액션 집계 조회 | F3 | N |
| GET | `/veo-jobs/{job_id}` | Veo Job 상태 조회 (폴링) | F2 | N |

> **경로 충돌 주의**: FastAPI는 라우트 등록 순서에 따라 매칭. `GET /creatures/public`은 반드시 `GET /creatures/{id}` 보다 먼저 등록되어야 함. 현재 코드에서 올바르게 유지 중.

> **내부 전용 API** (프론트엔드 직접 호출 금지):
> - `POST /veo-jobs` — 생성 파이프라인 내부에서 자동 호출
> - `PATCH /veo-jobs/{job_id}` — 생성 파이프라인 내부에서 자동 호출

---

## 4. 구현 완료 API — 응답 DTO 명세

### POST `/match`

**요청**: `multipart/form-data`
| 필드 | 타입 | 설명 |
|------|------|------|
| `file` | File | JPEG / PNG / WebP, 최대 10MB |

**성공 응답 data:**
```json
{
  "top3": [
    {
      "rank": 1,
      "pokemon_id": 25,
      "name_kr": "피카츄",
      "name_en": "Pikachu",
      "primary_type": "electric",
      "secondary_type": null,
      "sprite_url": "https://...",
      "similarity": 0.8923,
      "reasons": [
        {
          "dimension": "eye_size_score",
          "label": "큰 눈",
          "user_value": 0.82,
          "pokemon_value": 0.78
        }
      ]
    }
  ],
  "user_vector": [0.82, 0.54, ...]
}
```

> `user_vector`: 28차원 float 배열 (디버그용, 프론트에서 직접 표시 불필요)
> `reasons`: 최대 3개, 배열이 비어있을 수 있음
> `sprite_url`: null 가능 → serebii.net fallback 사용

---

### POST `/creatures`

**요청 body:**
```json
{
  "matched_pokemon_id": 25,
  "match_rank": 1,
  "similarity_score": 0.8923,
  "match_reasons": [
    { "dimension": "eye_size_score", "label": "큰 눈", "user_value": 0.82, "pokemon_value": 0.78 }
  ],
  "name": "임시이름",
  "story": null,
  "image_url": null,
  "video_url": null,
  "is_public": false
}
```

> `name`: `/generate` 단계에서 AI가 재생성하므로 임시값 허용 (1~40자 필수)
> `story`, `image_url`, `video_url`: null 허용

**성공 응답 data:** → `CreatureResponse` (§4 `/creatures/{id}` 참고)

---

### GET `/creatures/public`

**쿼리 파라미터:**
| 파라미터 | 타입 | 기본값 | 범위 |
|---------|------|--------|------|
| `limit` | int | 20 | 1~100 |
| `offset` | int | 0 | 0~ |

**성공 응답 data:**
```json
{
  "items": [ /* CreatureResponse 배열 */ ],
  "limit": 20,
  "offset": 0
}
```

---

### GET `/creatures/{id}`

**성공 응답 data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "matched_pokemon_id": 25,
  "match_rank": 1,
  "similarity_score": 0.8923,
  "match_reasons": [ { "dimension": "...", "label": "...", "user_value": 0.0, "pokemon_value": 0.0 } ],
  "name": "빛의 크리처",
  "story": "크리처 설명 텍스트...",
  "image_url": "https://...",
  "video_url": "https://...",
  "is_public": false,
  "created_at": "2026-03-13T12:00:00Z",
  "matched_pokemon_name_kr": "피카츄"
}
```

> `story`, `image_url`, `video_url`, `matched_pokemon_name_kr`: null 가능

---

### POST `/creatures/{id}/generate`

**요청 body:**
```json
{
  "regenerate_name_story": true,
  "regenerate_image": true,
  "trigger_video": true
}
```

**성공 응답 data:**
```json
{
  "creature": { /* CreatureResponse */ },
  "veo_job": {
    "id": "veo-job-uuid",
    "creature_id": "creature-uuid",
    "status": "queued",
    "video_url": null,
    "error_message": null,
    "requested_at": "2026-03-13T12:00:00Z",
    "updated_at": "2026-03-13T12:00:00Z"
  },
  "image": { "source": "imagen", "used_fallback": false, "retries": 0, "message": null },
  "story": { "source": "gemini_flash", "used_fallback": false, "retries": 0, "message": null },
  "video": { "source": "veo", "used_fallback": false, "retries": 0, "message": null }
}
```

> `veo_job`: null 가능 (`trigger_video: false`이거나 영상 생성 스킵 시)
> `veo_job.status`: `queued` | `running` | `succeeded` | `failed` | `canceled`
> 프론트엔드는 `data.veo_job.id`를 꺼내어 폴링 시작

---

### GET `/veo-jobs/{job_id}`

**성공 응답 data:**
```json
{
  "id": "veo-job-uuid",
  "creature_id": "creature-uuid",
  "status": "succeeded",
  "video_url": "https://...",
  "error_message": null,
  "requested_at": "2026-03-13T12:00:00Z",
  "updated_at": "2026-03-13T12:01:15Z"
}
```

**폴링 종료 조건:**
| status | 처리 |
|--------|------|
| `queued` / `running` | 폴링 계속 |
| `succeeded` | `video_url` 확보 → `/result/{id}` 이동 |
| `failed` / `canceled` | 폴링 종료, `image_url` fallback으로 결과 표시 |
| 25회 초과 (75초) | 폴링 강제 종료, `image_url` fallback |

---

### POST `/creatures/{id}/reactions`

**요청 body:**
```json
{ "emoji_type": "❤️" }
```

**성공 응답 data:**
```json
{
  "id": "reaction-uuid",
  "creature_id": "creature-uuid",
  "emoji_type": "❤️",
  "created_at": "2026-03-13T12:00:00Z"
}
```

---

### GET `/creatures/{id}/reactions/summary`

**성공 응답 data:**
```json
{
  "creature_id": "creature-uuid",
  "counts": [
    { "emoji_type": "🔥", "count": 12 },
    { "emoji_type": "❤️", "count": 8 }
  ],
  "total": 20
}
```

---

## 5. 신규 추가 필요 API 목록

### 5-1. F2 착수 전 추가 (백엔드 구현 필요)

---

#### PATCH `/creatures/{id}` — 크리처 이름/공개 수정

> **상태: 미구현** | 허용 필드: `name`, `is_public` (둘 중 최소 1개 필수)
> MVP에서는 ownership 검증 없음 (user_id 미연결 상태). F3에서 인증 연동 후 403 추가 예정.

**요청 body** (partial update — 최소 1개 이상 포함):
```json
{ "name": "새 이름" }
```
또는
```json
{ "is_public": true }
```
또는
```json
{ "name": "새 이름", "is_public": true }
```

**제약조건:**
| 필드 | 타입 | 제약 |
|------|------|------|
| `name` | string | 1~40자, 선택 |
| `is_public` | boolean | 선택 |

**성공 응답 (200):** `CreatureResponse` (§4 GET /creatures/{id} 동일 구조)

**에러 응답:**
| HTTP | error_code | 조건 |
|------|------------|------|
| 404 | `CREATURE_NOT_FOUND` | 존재하지 않는 id |
| 422 | `VALIDATION_ERROR` | name 길이 초과 등 |

---

#### POST `/auth/register` — 이메일 회원가입

> **상태: 미구현**

**요청 body:**
```json
{
  "name": "홍길동",
  "email": "user@example.com",
  "password": "password123"
}
```

**제약조건:**
| 필드 | 타입 | 제약 |
|------|------|------|
| `name` | string | 2~20자 |
| `email` | string | RFC 5321 형식 |
| `password` | string | 8자 이상, 영문+숫자 |

**성공 응답 (201):**
```json
{
  "success": true,
  "request_id": "...",
  "duration_ms": 123,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "user-uuid",
      "name": "홍길동",
      "email": "user@example.com"
    }
  }
}
```

**에러 응답:**
| HTTP | error_code | 조건 |
|------|------------|------|
| 409 | `EMAIL_ALREADY_EXISTS` | 이미 가입된 이메일 |
| 422 | `VALIDATION_ERROR` | 입력값 형식 오류 |

---

#### POST `/auth/login` — 이메일 로그인

> **상태: 미구현**

**요청 body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**성공 응답 (200):**
```json
{
  "success": true,
  "request_id": "...",
  "duration_ms": 123,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "user-uuid",
      "name": "홍길동",
      "email": "user@example.com"
    }
  }
}
```

**에러 응답:**
| HTTP | error_code | 조건 |
|------|------------|------|
| 401 | `INVALID_CREDENTIALS` | 이메일 또는 비밀번호 불일치 |

---

#### GET `/auth/me` — 현재 사용자 정보

> **상태: 미구현** | `Authorization: Bearer {access_token}` 헤더 필요

**성공 응답 (200):**
```json
{
  "success": true,
  "request_id": "...",
  "duration_ms": 123,
  "data": {
    "id": "user-uuid",
    "name": "홍길동",
    "email": "user@example.com",
    "created_at": "2026-03-13T00:00:00Z"
  }
}
```

**에러 응답:**
| HTTP | error_code | 조건 |
|------|------------|------|
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료 |

---

### 5-2. F3 착수 전 추가 (백엔드 구현 필요)

> F3 착수 전 백엔드에서 구현 필요. 이 시점에 `creatures` 테이블에 `user_id` 컬럼 추가 예정 (ALTER TABLE, NULL 허용).

| Method | Path | 설명 | 인증 |
|--------|------|------|------|
| DELETE | `/creatures/{id}` | 크리처 삭제 (본인만) | Bearer |
| GET | `/creatures/my` | 내 크리처 목록 | Bearer |
| DELETE | `/creatures/{id}/reactions` | 리액션 취소 | Bearer |
| POST | `/creatures/{id}/comments` | 댓글 작성 | Bearer |
| GET | `/creatures/{id}/comments` | 댓글 목록 | N |
| DELETE | `/creatures/{id}/comments/{comment_id}` | 댓글 삭제 (본인만) | Bearer |
| GET | `/users/check-nickname` | 닉네임 중복 검사 | N |
| PATCH | `/users/me` | 프로필 수정 | Bearer |
| PATCH | `/users/me/password` | 비밀번호 변경 | Bearer |
| DELETE | `/users/me` | 회원 탈퇴 | Bearer |

**경로 충돌 주의** — `GET /creatures/my`:
FastAPI에서 `/creatures/my`가 `/creatures/{id}` 패턴과 충돌할 수 있음.
`/creatures/my`를 반드시 `/creatures/{id}` 라우터보다 **먼저** 등록해야 함.

---

**F3 신규 API 상세 스펙:**

#### GET `/creatures/my`
```
쿼리: ?limit=20&offset=0
Authorization: Bearer {token}
```
**응답 data:** `{ items: CreatureResponse[], limit, offset }`

---

#### DELETE `/creatures/{id}`
**응답:** 204 No Content
**에러:** 404 `CREATURE_NOT_FOUND`, 403 `FORBIDDEN`

---

#### POST `/creatures/{id}/comments`
**요청 body:** `{ "content": "댓글 내용" }` (1~100자)
**응답 data:**
```json
{
  "id": "comment-uuid",
  "content": "댓글 내용",
  "author": { "id": "user-uuid", "name": "홍길동" },
  "created_at": "2026-03-13T12:00:00Z"
}
```

---

#### GET `/creatures/{id}/comments`
```
쿼리: ?page=1&limit=20
```
**응답 data:** `{ items: CommentResponse[], total, page }`

---

#### PATCH `/users/me`
**요청 body** (partial):
```json
{ "name": "새이름", "bio": "자기소개" }
```
**응답 data:** `{ id, name, email, bio, created_at }`

---

#### PATCH `/users/me/password`
**요청 body:** `{ "current_password": "...", "new_password": "..." }`
**에러:** 400 `INVALID_CURRENT_PASSWORD`

---

#### DELETE `/users/me`
**요청 body:** `{ "password": "..." }` (소셜 로그인 유저는 선택)
**응답:** 204 No Content

---

#### GET `/users/check-nickname`
```
쿼리: ?q=닉네임
```
**응답 data:** `{ "available": true }`
**에러:** 409 `NICKNAME_ALREADY_EXISTS`

---

## 6. 선행 결정 사항

### 결정 1: 매칭 경로

| 항목 | 결정 |
|------|------|
| 경로 | `POST /api/v1/match` |
| 이유 | 백엔드 실제 구현 경로 확인 |
| 기존 기획 문서의 `/match/face` | `/match`로 통일 완료 |

---

### 결정 2: 생성 상태 추적 방식

| 항목 | 결정 |
|------|------|
| 방식 | 2단계 — POST 트리거 후 veo-job 폴링 |
| 트리거 | `POST /api/v1/creatures/{id}/generate` → `data.veo_job.id` 반환 |
| 폴링 | `GET /api/v1/veo-jobs/{job_id}` (3초 간격, 최대 25회) |
| 완료 조건 | `veo_job.status === 'succeeded'` |
| 실패 조건 | `status === 'failed'` 또는 `'canceled'` 또는 25회 초과 |
| Fallback | `veo_job`이 null이거나 실패/타임아웃 시 `image_url`로 결과 표시 |

---

### 결정 3: 이름 수정 / 공개 전환 API

| 항목 | 결정 |
|------|------|
| 경로 | `PATCH /api/v1/creatures/{id}` |
| 허용 필드 | `name` (1~40자), `is_public` (boolean) — 두 필드만 허용 |
| 요청 | partial update — 최소 1개 이상 포함 |
| Ownership 검증 | F2 MVP에서는 미적용 (user_id 미연결 상태) / F3에서 추가 |
| 상태 | **신규 추가 필요** (F2 착수 전) |

---

### 결정 4: 좋아요 vs 이모지 리액션

| 항목 | 결정 |
|------|------|
| MVP | 이모지 리액션 API(`POST /creatures/{id}/reactions`) 사용, `emoji_type: "❤️"`로 좋아요 구현 |
| 이유 | 백엔드에 이미 구현된 리액션 API 재활용. 추후 다른 이모지 확장 가능 |
| 리액션 취소 | `DELETE /creatures/{id}/reactions` — F3에서 추가 |

---

### 결정 5: 폴링 훅 이름

| 항목 | 결정 |
|------|------|
| 훅 이름 | `useVeoPolling` |
| 파라미터 | `creatureId: string`, `onSuccess: (id) => void`, `onError: (msg) => void` |

---

### 결정 6: users 테이블

| 항목 | 결정 |
|------|------|
| DB | Railway PostgreSQL (기존 연결 유지) |
| 신규 테이블 | `users` — F2 착수 전 마이그레이션 (신규 테이블만, 기존 테이블 변경 없음) |
| `creatures.user_id` 컬럼 추가 | **F3에서 처리** (ALTER TABLE, NULL 허용) |

`users` 테이블 DDL:
```sql
CREATE TABLE IF NOT EXISTS users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       VARCHAR(255) UNIQUE NOT NULL,
  name        VARCHAR(100) NOT NULL,
  password    VARCHAR(255),
  provider    VARCHAR(20),
  provider_id VARCHAR(255),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

> `bio`, `avatar_url`, `dark_mode`, `font_size` 등 프로필 확장 컬럼은 F3 `PATCH /users/me` 구현 시 추가.

---

### 결정 7: 광장 피드 아키텍처

| 항목 | 결정 |
|------|------|
| F3-1 | 크리처 상세 + 마이페이지 (소셜 기능, Phaser 없음) |
| F3-2 | 광장 정적 맵 (Phaser.js 싱글플레이어) |
| F3-3 | 광장 멀티플레이어 + 채팅 (socket.io) |

---

### 결정 8: Auth 방식 (신규)

| 항목 | 결정 |
|------|------|
| 방식 | 직접 JWT (NextAuth.js 미사용) |
| 이유 | NextAuth는 설정 복잡도 높음. Next.js App Router와 충돌 가능성. 서버/클라이언트 경계 관리 불필요. |
| 토큰 종류 | Access Token 단일 발급 (Refresh Token 없음) |
| 만료 시간 | 86400초 (24시간) |
| 저장 위치 | `sessionStorage["pm_access_token"]` (프론트엔드) |
| 요청 방식 | `Authorization: Bearer {token}` 헤더 |
| 소셜 로그인 | F2 범위 외 — Google/Kakao OAuth는 F3에서 처리 |

---

### 결정 9: 프론트엔드 인증 상태 관리 (신규)

| 항목 | 결정 |
|------|------|
| 인증 상태 전역화 | 미사용 — sessionStorage 직접 확인 |
| 토큰 저장 키 | `pm_access_token` (sessionStorage) |
| 토큰 만료 시 | 자동 로그아웃 + Toast 안내 + `/login?next={현재경로}` 이동 |
| 비로그인 보호 | `AuthGateModal` — 저장/공유 액션 클릭 시 표시 |
| 로그인 후 복귀 | `?next=` URL 파라미터로 원래 경로 복귀 |

`storage.ts` 추가 키:
```typescript
sessionStorage["pm_access_token"]  // JWT access token
sessionStorage["pm_user"]          // { id, name, email } JSON
```

---

## 7. Top3 응답 필드 매핑 (확정)

`POST /api/v1/match` 응답 → 프론트 사용 필드:

| 백엔드 필드 | 타입 | 프론트 사용 | 비고 |
|------------|------|-----------|------|
| `rank` | int | 카드 순위, 1위 강조 (BEST MATCH 뱃지) | 필수 |
| `pokemon_id` | int | serebii.net URL 조합, POST /creatures 전달 | 필수 |
| `name_kr` | string | 카드 표시 이름 | 필수 |
| `name_en` | string | 부제 | 선택 |
| `primary_type` | string | 카드 배경 색상, TypeBadge | 필수 |
| `secondary_type` | string \| null | TypeBadge (있으면 추가) | 선택 |
| `sprite_url` | string \| null | null이면 serebii.net fallback | 선택 |
| `similarity` | float | 유사도 % 표시, ProgressBar | 필수 |
| `reasons[].label` | string | 카드 설명 텍스트 (최대 3개) | 선택 |

**serebii.net URL 조합:**
```typescript
const getSpriteUrl = (id: number) =>
  `https://www.serebii.net/pokemongo/pokemon/${String(id).padStart(3, '0')}.png`
```

**포켓몬 타입별 배경 색상 (PokemonCard용):**
```typescript
const TYPE_BG: Record<string, string> = {
  fire:     "linear-gradient(135deg, #fff1ee, #ffd6cc)",
  water:    "linear-gradient(135deg, #eef4ff, #ccdeff)",
  grass:    "linear-gradient(135deg, #efffef, #cdffd0)",
  electric: "linear-gradient(135deg, #fffbee, #ffeec0)",
  psychic:  "linear-gradient(135deg, #ffeef8, #ffd6f0)",
  normal:   "linear-gradient(135deg, #f5f5f0, #e8e8e0)",
  fighting: "linear-gradient(135deg, #fff0ee, #ffd0cc)",
  ghost:    "linear-gradient(135deg, #f0eeff, #d6ccff)",
  ice:      "linear-gradient(135deg, #eef8ff, #ccecff)",
  dragon:   "linear-gradient(135deg, #eeeeff, #ccccff)",
  dark:     "linear-gradient(135deg, #f0eeee, #ddd8d8)",
  steel:    "linear-gradient(135deg, #f0f2f5, #d8dde5)",
  poison:   "linear-gradient(135deg, #f5eeff, #e0ccff)",
  ground:   "linear-gradient(135deg, #fdf6ee, #f0e0c0)",
  flying:   "linear-gradient(135deg, #eef6ff, #cce0ff)",
  bug:      "linear-gradient(135deg, #f5ffee, #d8f0cc)",
  rock:     "linear-gradient(135deg, #f5f0e8, #e0d0b0)",
}
```

---

## 8. 에러 코드 → 사용자 메시지 매핑 (전체)

### 구현 완료 에러 코드 (백엔드 현재 반환 중)

| error_code | HTTP | 사용자 메시지 |
|------------|------|--------------|
| `UNSUPPORTED_MEDIA_TYPE` | 415 | JPG, PNG, WebP 파일만 업로드할 수 있어요 |
| `FILE_TOO_LARGE` | 413 | 파일 크기가 10MB를 초과해요 |
| `FACE_NOT_DETECTED` | 422 | 얼굴을 찾지 못했어요. 얼굴이 잘 보이는 사진을 사용해 주세요 |
| `MULTIPLE_FACES` | 422 | 얼굴이 2개 이상 감지됐어요. 혼자 찍은 사진을 사용해 주세요 |
| `LOW_QUALITY` | 422 | 이미지 화질이 너무 낮아요. 더 선명한 사진을 사용해 주세요 |
| `CREATURE_NOT_FOUND` | 404 | 크리처를 찾을 수 없어요 |
| `VEO_JOB_NOT_FOUND` | 404 | 생성 작업을 찾을 수 없어요 |
| `NO_MATCH_FOUND` | 404 | 유사한 포켓몬을 찾지 못했어요 |
| `INTERNAL_ERROR` | 500 | 잠시 후 다시 시도해 주세요 |

### F2 신규 에러 코드 (백엔드 추가 필요)

| error_code | HTTP | 사용자 메시지 |
|------------|------|--------------|
| `EMAIL_ALREADY_EXISTS` | 409 | 이미 사용 중인 이메일이에요 |
| `INVALID_CREDENTIALS` | 401 | 이메일 또는 비밀번호가 올바르지 않아요 |
| `UNAUTHORIZED` | 401 | 로그인이 필요해요 |
| `VALIDATION_ERROR` | 422 | 입력값을 확인해 주세요 |

### F3 신규 에러 코드 (백엔드 추가 필요)

| error_code | HTTP | 사용자 메시지 |
|------------|------|--------------|
| `FORBIDDEN` | 403 | 권한이 없어요 |
| `NICKNAME_ALREADY_EXISTS` | 409 | 이미 사용 중인 닉네임이에요 |
| `INVALID_CURRENT_PASSWORD` | 400 | 현재 비밀번호가 올바르지 않아요 |
| `COMMENT_NOT_FOUND` | 404 | 댓글을 찾을 수 없어요 |

---

## 9. 미결 사항

| 항목 | 현황 | 결정 필요 시점 | 상태 |
|------|------|--------------|------|
| `creatures` 테이블 `user_id` 컬럼 추가 | F3에서 처리 결정 완료 | F3 착수 전 | ✅ 결정됨 |
| `/creatures/my` 경로 충돌 가능성 | 백엔드 라우터 등록 순서로 해결 (`/my`를 `{id}` 앞에 등록) | F3 착수 전 | ✅ 해결 방법 확정 |
| 소셜 로그인 OAuth 앱 등록 (Google, Kakao) | 미등록 | F3 착수 전 | 🔴 미해결 |
| WebSocket 서버 FastAPI 통합 방식 | `python-socketio` ASGIApp 마운트 방식 채택 예정 | F3-3 착수 전 | 🟡 대기 |
| `PATCH /creatures/{id}` Ownership 검증 | F2 MVP에서는 미적용, F3에서 user_id 연결 후 추가 | F3 착수 전 | ✅ 결정됨 |
| users 테이블 프로필 확장 컬럼 (`bio` 등) | F3 `PATCH /users/me` 구현 시 ALTER TABLE로 추가 | F3 착수 전 | ✅ 결정됨 |
