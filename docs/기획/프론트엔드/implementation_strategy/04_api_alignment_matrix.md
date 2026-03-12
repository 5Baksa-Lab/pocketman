# API 정렬 매트릭스 (기획 vs 구현)

> 마지막 업데이트: 2026-03-12
> 기준: 백엔드 실제 구현 코드 분석 완료

---

## 1. 우선 기준

- 기준은 "현재 동작 가능한 API"를 우선으로 삼는다.
- 기획 전용 API는 `신규 추가 필요`로 분리하고 담당 Stage를 명시한다.
- API가 변경되면 이 문서를 먼저 수정 → Stage 문서 반영 → 페이지 설계 문서 반영 순서를 지킨다.

---

## 2. 공통 응답 구조 (확정)

**성공 응답:**
```json
{
  "success": true,
  "request_id": "8자 UUID",
  "duration_ms": number,
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

모든 API URL 앞에 `/api/v1` 접두사가 붙는다.

---

## 3. 구현 완료 API 목록 (사용 가능)

| Method | Path | 설명 | 사용 Stage |
|--------|------|------|-----------|
| GET | `/health` | 서버 헬스 체크 | — |
| POST | `/match` | 얼굴 → Top3 매칭 | F1 |
| POST | `/creatures` | 크리처 레코드 생성 | F2 |
| GET | `/creatures/public` | 공개 크리처 목록 | F1(샘플), F3 |
| GET | `/creatures/{id}` | 크리처 상세 조회 | F2, F3 |
| POST | `/creatures/{id}/generate` | 생성 파이프라인 트리거 | F2 |
| POST | `/creatures/{id}/reactions` | 이모지 리액션 추가 | F3 |
| GET | `/creatures/{id}/reactions/summary` | 리액션 집계 조회 | F3 |
| POST | `/veo-jobs` | Veo Job 생성 | 내부 |
| GET | `/veo-jobs/{job_id}` | Veo Job 상태 조회 (폴링) | F2 |
| PATCH | `/veo-jobs/{job_id}` | Veo Job 상태 수동 업데이트 | 내부 |

---

## 4. 신규 추가 필요 API 목록

> F2/F3 착수 전 백엔드에서 구현 필요.

### F2에서 필요 (F2 착수 전 추가)

| Method | Path | 설명 | 요청 | 응답 |
|--------|------|------|------|------|
| POST | `/auth/register` | 이메일 회원가입 | `{ name, email, password }` | `{ access_token, user }` / 409 `EMAIL_ALREADY_EXISTS` |
| POST | `/auth/login` | 이메일 로그인 | `{ email, password }` | `{ access_token, user }` / 401 `INVALID_CREDENTIALS` |
| POST | `/auth/social` | 소셜 OAuth 처리 | `{ provider, code }` | `{ access_token, user }` |
| GET | `/auth/me` | 현재 사용자 정보 | Header Bearer | `{ id, name, email, bio, ... }` |
| PATCH | `/creatures/{id}` | 크리처 이름/공개 수정 | `{ name?, is_public? }` | `{ id, name, is_public }` / 403 |

### F3에서 필요 (F3 착수 전 추가)

| Method | Path | 설명 | 요청 | 응답 |
|--------|------|------|------|------|
| DELETE | `/creatures/{id}` | 크리처 삭제 | — | 204 / 403 |
| GET | `/creatures/my` | 내 크리처 목록 | Header Bearer | `{ items, total }` |
| GET | `/creatures/liked` | 좋아요한 크리처 목록 | Header Bearer | `{ items, total }` |
| DELETE | `/creatures/{id}/reactions` | 좋아요 취소 | Header Bearer | 204 |
| POST | `/creatures/{id}/comments` | 댓글 작성 | `{ content }` | `{ id, content, author, created_at }` / 422 |
| GET | `/creatures/{id}/comments` | 댓글 목록 | `?page&limit` | `{ items, total, page }` (최신순) |
| DELETE | `/creatures/{id}/comments/{id}` | 댓글 삭제 | Header Bearer | 204 / 403 |
| GET | `/users/check-nickname` | 닉네임 중복 검사 | `?q=닉네임` | `{ available: bool }` |
| PATCH | `/users/me` | 프로필 수정 | `{ name?, bio?, avatar_creature_id?, dark_mode?, font_size? }` | `{ id, name, bio, ... }` |
| PATCH | `/users/me/password` | 비밀번호 변경 | `{ current_password, new_password }` | 200 / 400 `INVALID_CURRENT_PASSWORD` |
| DELETE | `/users/me` | 회원 탈퇴 | `{ password? }` | 204 |
| GET | `/plaza/online/{user_id}` | 광장 온라인 여부 | — | `{ is_online, x?, y? }` |
| GET | `/plaza/online` | 광장 전체 온라인 목록 | — | `{ online_users: [user_id] }` |

---

## 5. 선행 결정 사항 (확정 완료)

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
| 실패 조건 | `status === 'failed'` 또는 `status === 'canceled'` 또는 25회 초과 |
| Fallback | `veo_job`이 null이거나 실패 시 `image_url`로 결과 표시 |
| 기존 기획의 `GET /creatures/{id}/status` | `GET /veo-jobs/{job_id}`로 대체 |

veo_job status 값:
```
queued    → 대기 중 (polling 계속)
running   → 생성 중 (polling 계속)
succeeded → 완료 (video_url 확보 → /result 이동)
failed    → 실패 (에러 UI)
canceled  → 취소 (image_url fallback)
```

---

### 결정 3: 이름 수정 / 공개 전환 API

| 항목 | 결정 |
|------|------|
| 경로 | `PATCH /api/v1/creatures/{id}` (단일 PATCH) |
| 이유 | 전용 `/name` PATCH보다 확장성 좋음 |
| 요청 | partial update 허용 (`{ name? }` 또는 `{ is_public? }` 또는 둘 다) |
| 상태 | **신규 추가 필요** (F2 착수 전) |

---

### 결정 4: 좋아요 vs 이모지 리액션

| 항목 | 결정 |
|------|------|
| MVP | 이모지 리액션 API(`POST /creatures/{id}/reactions`) 사용, `emoji_type: "❤️"`로 좋아요 구현 |
| 이유 | 백엔드에 이미 구현된 리액션 API 재활용. 추후 다른 이모지 확장 가능 |
| 좋아요 취소 | `DELETE /creatures/{id}/reactions` — F3에서 추가 필요 |
| F4 이후 | 이모지 다양화 (👍 😮 😂 등) |

---

### 결정 5: 폴링 훅 이름

| 항목 | 결정 |
|------|------|
| 훅 이름 | `useVeoPolling` (페이지 설계 문서 기준으로 통일) |
| 이전 F2 문서의 `useGenerationPolling` | `useVeoPolling`으로 수정 완료 |

---

### 결정 6: users 테이블

| 항목 | 결정 |
|------|------|
| DB | Railway PostgreSQL (기존 연결 유지) |
| 신규 테이블 | `users` — F2 착수 전 마이그레이션 |
| `creatures` 수정 | `is_public` 컬럼 이미 있음 (확인 완료), `name` 컬럼 확인 필요 |

`users` 테이블 DDL:
```sql
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       VARCHAR(255) UNIQUE NOT NULL,
  name        VARCHAR(100) NOT NULL,
  password    VARCHAR(255),
  provider    VARCHAR(20),
  provider_id VARCHAR(255),
  avatar_url  VARCHAR(500),
  bio         VARCHAR(100),
  dark_mode   BOOLEAN DEFAULT FALSE,
  font_size   SMALLINT DEFAULT 16,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 결정 7: 광장 피드 vs Phaser 순서

| 항목 | 결정 |
|------|------|
| F3-1 | 크리처 상세 + 마이페이지 (소셜 기반, Phaser 없음) |
| F3-2 | 광장 정적 맵 (Phaser.js 싱글플레이어) |
| F3-3 | 광장 멀티플레이어 + 채팅 (socket.io) |
| 이유 | Phaser+socket.io 동시 구현은 난이도 높음. 단계적 검증으로 위험 분산 |
| 멀티플레이어 MVP 포함 여부 | F3 전체 범위에 포함 (F3-3에서 구현) |

---

## 6. Top3 응답 필드 매핑 (확정)

백엔드 `POST /api/v1/match` 응답 → 프론트 사용 필드:

| 백엔드 필드 | 프론트 사용 | 비고 |
|---|---|---|
| `rank` | 카드 순위, 1위 강조 | 필수 |
| `pokemon_id` | serebii.net URL 조합, `POST /creatures` 전달 | 필수 |
| `name_kr` | 카드 표시 이름 | 필수 |
| `name_en` | 부제 (선택) | 선택 |
| `primary_type` | 카드 배경 색상, TypeBadge | 필수 |
| `secondary_type` | TypeBadge (있으면 추가) | 선택 |
| `sprite_url` | null이면 serebii.net fallback | 선택 |
| `similarity` | 유사도 % 표시, 프로그레스바 | 필수 |
| `reasons[0..2].label` | 카드 설명 텍스트 | 선택 |

serebii.net URL 조합:
```typescript
const getPokeGoImageUrl = (id: number) =>
  `https://www.serebii.net/pokemongo/pokemon/${String(id).padStart(3, '0')}.png`
```

---

## 7. 에러 코드 → 사용자 메시지 매핑 (전체)

### 기존 에러 코드 (백엔드 구현 완료)

| error_code | HTTP | 사용자 메시지 |
|---|---|---|
| `UNSUPPORTED_MEDIA_TYPE` | 415 | JPG, PNG, WebP 파일만 업로드할 수 있어요 |
| `FILE_TOO_LARGE` | 413 | 파일 크기가 10MB를 초과해요 |
| `FACE_NOT_DETECTED` | 422 | 얼굴을 찾지 못했어요. 얼굴이 잘 보이는 사진을 사용해 주세요 |
| `MULTIPLE_FACES` | 422 | 얼굴이 2개 이상 감지됐어요. 혼자 찍은 사진을 사용해 주세요 |
| `LOW_QUALITY` | 422 | 이미지 화질이 너무 낮아요. 더 선명한 사진을 사용해 주세요 |
| `CREATURE_NOT_FOUND` | 404 | 크리처를 찾을 수 없어요 |
| `VEO_JOB_NOT_FOUND` | 404 | 생성 작업을 찾을 수 없어요 |
| `NO_MATCH_FOUND` | 404 | 유사한 포켓몬을 찾지 못했어요 |
| `INTERNAL_ERROR` | 500 | 잠시 후 다시 시도해 주세요 |

### 신규 추가 에러 코드 (F2/F3에서 추가)

| error_code | HTTP | 사용자 메시지 |
|---|---|---|
| `EMAIL_ALREADY_EXISTS` | 409 | 이미 사용 중인 이메일이에요 |
| `INVALID_CREDENTIALS` | 401 | 이메일 또는 비밀번호가 올바르지 않아요 |
| `UNAUTHORIZED` | 401 | 로그인이 필요해요 |
| `FORBIDDEN` | 403 | 권한이 없어요 |
| `NICKNAME_ALREADY_EXISTS` | 409 | 이미 사용 중인 닉네임이에요 |
| `INVALID_CURRENT_PASSWORD` | 400 | 현재 비밀번호가 올바르지 않아요 |
| `USER_OFFLINE` | 400 | 해당 유저가 광장에 없어요 |

---

## 8. 미결 사항 (F3 착수 전 결정)

| 항목 | 현황 | 결정 필요 시점 |
|------|------|--------------|
| `creatures` 테이블 `name` 컬럼 존재 여부 확인 | 백엔드 스키마 확인 필요 | F2 착수 전 |
| `/creatures/my` 경로 충돌 가능성 (`{id}` 패턴과) | FastAPI path ordering 확인 필요 | F3 착수 전 |
| 소셜 로그인 OAuth 앱 등록 (Google, Kakao) | 미등록 | F2 착수 전 |
| WebSocket 서버 FastAPI 통합 방식 확정 | `python-socketio` ASGIApp 마운트 방식 채택 예정 | F3-3 착수 전 |
