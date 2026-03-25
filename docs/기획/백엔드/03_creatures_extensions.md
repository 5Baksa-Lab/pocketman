# 백엔드 기능 설계: 크리처 기능 확장 (Creatures Extensions)

- 작성일: 2026-03-12
- 상태: 설계 확정 (미구현)
- 관련 프론트엔드: `/result/[id]`, `/creatures/[id]`, `/my`

---

## 개요

기존 크리처 생성/조회 API에 추가되는 기능:
이름 편집, 공개/비공개 전환, 삭제, 댓글, 좋아요, 내 크리처 목록, 좋아요한 크리처 목록.

---

## 기존 API (Phase 0/1 구현 완료)

- `POST /match/face` — 얼굴 이미지 → TOP-3 포켓몬 매칭
- `POST /creatures` — 크리처 생성 (Pokemon + 사용자 이미지 → Veo 영상)
- `GET /creatures/{id}/status` — 생성 상태 폴링

---

## 신규 엔드포인트

### PATCH `/creatures/{id}/name`

크리처 이름 인라인 편집 (결과 페이지에서 사용).

**Header**: `Authorization: Bearer {token}` (본인만 가능)

**Request**:
```json
{ "name": "새 크리처 이름" }
```

**Response 200**:
```json
{ "id": "uuid", "name": "새 크리처 이름" }
```

**에러**:
- `403 Forbidden`: 본인 크리처가 아닌 경우

---

### PATCH `/creatures/{id}`

크리처 속성 수정 (이름, 공개/비공개).

**Header**: `Authorization: Bearer {token}` (본인만 가능)

**Request** (부분 업데이트):
```json
{
  "name": "수정된 이름",
  "is_public": false
}
```

**Response 200**: 수정된 크리처 전체 정보

---

### DELETE `/creatures/{id}`

크리처 삭제.

**Header**: `Authorization: Bearer {token}` (본인만 가능)

**Response 204**: No Content

**처리**: 연결된 댓글, 좋아요 기록도 함께 삭제 (CASCADE).

---

### GET `/creatures/{id}`

크리처 상세 조회. 공개 크리처는 인증 불필요.

**Response 200**:
```json
{
  "id": "uuid",
  "name": "크리처 이름",
  "pokemon_id": 25,
  "pokemon_name": "피카츄",
  "similarity_score": 87.3,
  "type": ["전기"],
  "description": "크리처 설명 텍스트",
  "video_url": "https://...",
  "image_url": "https://...",
  "is_public": true,
  "owner": {
    "id": "uuid",
    "name": "홍길동",
    "is_online": false
  },
  "like_count": 42,
  "is_liked": false,
  "created_at": "2026-03-12T00:00:00Z"
}
```

**에러**:
- `404 Not Found`: 비공개 크리처에 타인이 접근한 경우

---

### GET `/creatures/my`

내 크리처 목록 조회.

**Header**: `Authorization: Bearer {token}`

**Query** (선택적): `?page=1&limit=20`

**Response 200**:
```json
{
  "items": [{ "id": "...", "name": "...", "is_public": true, "thumbnail_url": "..." }],
  "total": 5
}
```

---

### GET `/creatures/liked`

좋아요한 크리처 목록 조회.

**Header**: `Authorization: Bearer {token}`

**Response 200**: `/creatures/my`와 동일 구조

---

### POST `/creatures/{id}/like`

크리처 좋아요 추가.

**Header**: `Authorization: Bearer {token}`

**Response 200**:
```json
{ "like_count": 43 }
```

**에러**:
- `409 Conflict`: 이미 좋아요한 경우

---

### DELETE `/creatures/{id}/like`

크리처 좋아요 취소.

**Header**: `Authorization: Bearer {token}`

**Response 200**:
```json
{ "like_count": 42 }
```

---

## DB 스키마 추가 — `creatures` 테이블 컬럼 추가

```sql
ALTER TABLE creatures
  ADD COLUMN IF NOT EXISTS is_public  BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS name       VARCHAR(100);
```

---

## DB 스키마 신규 — `likes` 테이블

```sql
CREATE TABLE likes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  creature_id UUID NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, creature_id)
);
```
