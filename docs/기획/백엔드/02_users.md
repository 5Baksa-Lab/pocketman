# 백엔드 기능 설계: 사용자 관리 (Users)

- 작성일: 2026-03-12
- 상태: 설계 확정 (미구현)
- 관련 프론트엔드: `/my`, `/my/edit`, `/my/password`

---

## 개요

로그인 사용자의 프로필 편집, 비밀번호 변경, 닉네임 중복 검사, 회원 탈퇴 기능.

---

## 엔드포인트

### GET `/users/check-nickname`

닉네임(이름) 중복 여부 확인. 인증 불필요.

**Query**: `?q={nickname}`

**Response 200**:
```json
{ "available": true }
```
또는
```json
{ "available": false }
```

**사용처**: `/my/edit` 프로필 편집 — debounce 300ms 실시간 검사

---

### PATCH `/users/me`

프로필 정보 수정.

**Header**: `Authorization: Bearer {token}`

**Request** (부분 업데이트, 모두 선택적):
```json
{
  "name": "새닉네임",
  "bio": "새 한 줄 소개",
  "avatar_creature_id": "creature_uuid",
  "dark_mode": true,
  "font_size": 18
}
```

**Response 200**:
```json
{
  "id": "uuid",
  "name": "새닉네임",
  "bio": "새 한 줄 소개",
  "avatar_url": "https://...",
  "dark_mode": true,
  "font_size": 18
}
```

**에러**:
- `409 Conflict`: `name` 중복

**처리 로직**:
- `name` 변경 시 중복 검사 (본인 제외)
- `avatar_creature_id` 변경 시 해당 크리처의 소유자가 본인인지 확인

---

### PATCH `/users/me/password`

비밀번호 변경.

**Header**: `Authorization: Bearer {token}`

**Request**:
```json
{
  "current_password": "oldpass123",
  "new_password": "newpass456"
}
```

**Response 200**:
```json
{ "message": "비밀번호가 변경됐습니다." }
```

**에러**:
- `400 Bad Request`: 현재 비밀번호 불일치
- `400 Bad Request`: 소셜 로그인 계정 (password = NULL인 경우)

**처리 로직**:
1. 현재 비밀번호 bcrypt 검증
2. 새 비밀번호 bcrypt 해시
3. DB 업데이트

---

### DELETE `/users/me`

회원 탈퇴. 모든 데이터 즉시 삭제.

**Header**: `Authorization: Bearer {token}`

**Request**:
```json
{
  "password": "password123"    // 소셜 계정은 빈 문자열 또는 생략
}
```

**Response 204**: No Content

**삭제 대상** (CASCADE 또는 명시적 삭제):
1. 해당 유저의 모든 크리처
2. 해당 유저의 모든 댓글
3. 해당 유저의 좋아요 기록
4. users 레코드

**처리 로직**:
1. 이메일 계정: 비밀번호 재확인
2. 소셜 계정: 비밀번호 확인 생략
3. DB 트랜잭션으로 순차 삭제
4. 응답 후 쿠키 초기화

---

## 관련 DB 컬럼 추가

`users` 테이블에 아래 컬럼 추가 필요 (기존 테이블에 ALTER):

```sql
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS dark_mode  BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS font_size  SMALLINT DEFAULT 16;
```
