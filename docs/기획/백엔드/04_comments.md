# 백엔드 기능 설계: 댓글 (Comments)

- 작성일: 2026-03-12
- 상태: 설계 확정 (미구현)
- 관련 프론트엔드: `/creatures/[id]`

---

## 개요

크리처 상세 페이지의 댓글 기능. 최신순 정렬, 본인 댓글 삭제, 최대 100자.

---

## DB 스키마 — `comments` 테이블

```sql
CREATE TABLE comments (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  creature_id UUID NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content     VARCHAR(100) NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_creature_id ON comments(creature_id);
```

---

## 엔드포인트

### GET `/creatures/{id}/comments`

댓글 목록 조회. 인증 불필요.

**Query** (선택적): `?page=1&limit=20`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "content": "멋진 크리처네요!",
      "author": {
        "id": "uuid",
        "name": "홍길동"
      },
      "created_at": "2026-03-12T10:00:00Z",
      "is_mine": false
    }
  ],
  "total": 15,
  "page": 1
}
```

정렬: `created_at DESC` (최신순)

---

### POST `/creatures/{id}/comments`

댓글 작성. 로그인 필요.

**Header**: `Authorization: Bearer {token}`

**Request**:
```json
{ "content": "멋진 크리처네요!" }
```

**Validation**:
- `content`: 1자 이상 100자 이하

**Response 201**:
```json
{
  "id": "uuid",
  "content": "멋진 크리처네요!",
  "author": { "id": "uuid", "name": "홍길동" },
  "created_at": "2026-03-12T10:00:00Z",
  "is_mine": true
}
```

**에러**:
- `404 Not Found`: 크리처가 존재하지 않거나 비공개인 경우

---

### DELETE `/creatures/{id}/comments/{comment_id}`

댓글 삭제. 본인 댓글만 삭제 가능.

**Header**: `Authorization: Bearer {token}`

**Response 204**: No Content

**에러**:
- `403 Forbidden`: 본인 댓글이 아닌 경우
- `404 Not Found`: 댓글이 존재하지 않는 경우
