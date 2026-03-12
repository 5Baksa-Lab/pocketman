# 백엔드 기능 설계: 인증 (Auth)

- 작성일: 2026-03-12
- 상태: 설계 확정 (미구현)
- 관련 프론트엔드: `/login`, `/signup`

---

## 개요

NextAuth.js (Auth.js v5)와 연동하는 인증 엔드포인트.
JWT 전략 사용, Railway PostgreSQL `users` 테이블 기반.

---

## DB 스키마 — `users` 테이블

```sql
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       VARCHAR(255) UNIQUE NOT NULL,
  name        VARCHAR(100) NOT NULL,
  password    VARCHAR(255),           -- 소셜 가입 시 NULL
  provider    VARCHAR(20),            -- 'google' | 'kakao' | null
  provider_id VARCHAR(255),
  avatar_url  VARCHAR(500),
  bio         VARCHAR(100),
  dark_mode   BOOLEAN DEFAULT FALSE,
  font_size   SMALLINT DEFAULT 16,    -- 14 | 16 | 18
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 엔드포인트

### POST `/auth/register`

이메일 회원가입.

**Request**:
```json
{
  "name": "홍길동",
  "email": "user@example.com",
  "password": "password123"
}
```

**Response 201**:
```json
{
  "access_token": "eyJ...",
  "user": { "id": "uuid", "name": "홍길동", "email": "user@example.com" }
}
```

**에러**:
- `409 Conflict`: 이미 존재하는 이메일

**처리 로직**:
1. 이메일 중복 확인
2. `bcrypt.hash(password, 12)`
3. DB insert
4. JWT 발급 (access_token 15분, refresh_token 7일)

---

### POST `/auth/login`

이메일 로그인.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "user": { "id": "uuid", "name": "홍길동", "email": "user@example.com" }
}
```

**에러**:
- `401 Unauthorized`: 이메일/비밀번호 불일치

---

### POST `/auth/social`

소셜 OAuth 콜백 처리. NextAuth.js 콜백에서 호출.

**Request**:
```json
{
  "provider": "google",
  "code": "oauth_authorization_code"
}
```

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "user": { "id": "uuid", "name": "Jane", "email": "jane@gmail.com" }
}
```

**처리 로직**:
1. OAuth provider에서 토큰 교환
2. provider_id + provider로 users 테이블 조회
3. 없으면 신규 생성 (password = NULL)
4. JWT 발급

---

### GET `/auth/me`

현재 로그인 사용자 프로필 조회.

**Header**: `Authorization: Bearer {token}`

**Response 200**:
```json
{
  "id": "uuid",
  "name": "홍길동",
  "email": "user@example.com",
  "bio": "포켓몬 트레이너",
  "avatar_url": "https://...",
  "dark_mode": false,
  "font_size": 16,
  "provider": null,
  "created_at": "2026-03-12T00:00:00Z"
}
```

---

## JWT 정책

| 항목 | 값 |
|------|-----|
| Access Token 만료 | 15분 |
| Refresh Token 만료 | 7일 |
| 저장 위치 | httpOnly cookie (Refresh), Authorization header (Access) |
| 서명 알고리즘 | HS256 |

---

## Route 보호 대상 (middleware.ts)

```
/upload
/generate/*
/result/*
/my/*
/plaza        (크리처 없으면 안내 모달)
```
