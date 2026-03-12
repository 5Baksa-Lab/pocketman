# Stage F3 구현전략: Share + Feed + My

> **상태: 미착수 (F2 완료 후 착수)**

---

## 1. Stage 목표

- 공유 이후 사용자가 머무를 소셜 공간을 완성한다.
- 광장(Phaser.js 멀티플레이어 월드), 크리처 상세, 마이페이지를 통해 재방문 루프를 만든다.

핵심 성공 지표:
- 크리처 공개 전환률
- `/plaza` 재방문율
- 댓글/좋아요 참여율
- `/my`에서 프로필/설정 완료율

---

## 2. 포함/제외 범위

포함 라우트:
- `/plaza`
- `/creatures/[id]`
- `/my`
- `/my/edit`
- `/my/password`

제외 라우트:
- 업로드/생성 코어 퍼널 개선 (F4 이후)

---

## 3. F3 내부 단계 분할

### F3-1: 크리처 상세 + 마이페이지 (소셜 기반)
- `/creatures/[id]`, `/my`, `/my/edit`, `/my/password`
- 댓글, 좋아요, 프로필, 설정

### F3-2: 광장 정적 (Phaser 맵 + 내 캐릭터 이동)
- `/plaza` — 싱글플레이어 수준 맵 탐색
- Phaser.js 타일맵, 스프라이트, 카메라, D-pad

### F3-3: 광장 멀티플레이어 + 채팅
- socket.io 실시간 위치 동기화
- 공개 채팅 말풍선
- 1:1 비밀 채팅(DM)

---

## 4. 페이지별 UI 구현 단계

---

### 4.1 `/plaza`

목표:
- 포켓몬 Platinum Wi-Fi 광장 스타일 실시간 인터랙티브 소셜 공간

**기술 스택:**
- 렌더링: Phaser.js 3.x (타일맵 + 스프라이트 + 카메라)
- 실시간: socket.io-client + 백엔드 python-socketio
- 맵: 32×32 타일, 1개 = 32px → 1024×1024 월드
- 아트 스타일: 픽셀아트 탑뷰

**맵 구성:**
```
1024×1024 픽셀 월드 (32×32 타일 그리드)

바닥: 체크무늬 타일 (베이지 #f6f2e8 / 연한 틸 #d4edea)
중앙: 분수 랜드마크 (이동 불가, 좌표 x:400~624, y:400~624)
장식: 나무/덤불 (이동 불가 영역, 맵 설정 파일에 좌표 목록)
건물: 장식용 픽셀아트 (좌상단, 우상단)
```

**크리처 스프라이트:**
```
원형 마스크 크리처 이미지 (32×32px 또는 48×48px)
+ 픽셀 테두리 2px (#1a1a2e)
+ 닉네임 태그 (말풍선 스타일, 크리처 위 8px)

이동: 2프레임 bounce 애니메이션
  @keyframes sprite-bounce {
    0%,100% { transform: translateY(0); }
    50%     { transform: translateY(-4px); }
  }
정지: idle breathing
  @keyframes idle-breath {
    0%,100% { transform: scale(1.0); }
    50%     { transform: scale(1.03); }
  }
  animation: idle-breath 2s ease-in-out infinite;
```

**HUD 구성:**
```
상단 바 (fixed, z-index 100):
  [← 나가기]  온라인 인원: {count}명  [🔇 BGM]  [채팅]

하단 좌 (mobile only, fixed):
  D-pad 방향키 (상/하/좌/우 버튼)
  터치 시 연속 이동 (touchstart → interval, touchend → clearInterval)

하단 우:
  온라인 유저 목록 미니 패널 (최근 5명, 스크롤)
```

#### F3-2 구현 단계 (정적 맵)

1. Next.js에서 Phaser 초기화:
   ```typescript
   // Phaser는 SSR 불가 → dynamic import로 클라이언트 전용 로드
   const PlazaCanvas = dynamic(() => import('@/components/plaza/PlazaCanvas'), { ssr: false })
   ```
2. 타일맵 에셋 준비 (픽셀아트 PNG)
3. Phaser.Scene 구성: 맵 렌더링 + 플레이어 스프라이트
4. 키보드 (WASD/방향키) + D-pad 입력 통합
5. 카메라 플레이어 추적 (`camera.startFollow(player)`)
6. 이동 불가 타일 충돌 설정
7. HUD 오버레이 (React 컴포넌트, Phaser canvas 위에 absolute)
8. BGM 토글 (기본 OFF, localStorage 저장)

#### F3-3 구현 단계 (멀티플레이어)

1. socket.io 연결 (JWT auth 포함):
   ```typescript
   const socket = io('/plaza', {
     auth: { token: session.accessToken }
   })
   ```
2. `join` 이벤트 전송 → 서버에서 현재 플레이어 목록 수신
3. 타 플레이어 스프라이트 렌더링 (닉네임 태그 포함)
4. `player_move` 수신 → 타 플레이어 위치 업데이트 (보간 이동)
5. 공개 채팅 구현 (말풍선 3초 fadeOut)
6. DM 구현 (요청/수락/거절/채팅창)

**크리처 없는 신규 유저 처리:**
```
/plaza 진입 시:
  1. GET /api/v1/creatures/my 호출
  2. 크리처 없으면 → 안내 모달 표시

안내 모달:
  "광장을 이용하려면 먼저 크리처를 만들어야 해요!"
  [지금 크리처 만들러 가기] → /upload
  [다음에 하기] → 관전 모드 (이동 불가, 맵 탐색만 가능)
```

**공개 채팅 말풍선 구현:**
```typescript
// 입력: 최대 20자 (서버에서도 truncate)
// 전송 → socket.emit('chat', { message })
// 수신 → socket.on('chat_broadcast', ({ user_id, message }) => {
//   showBubble(user_id, message)  // 해당 플레이어 위에 말풍선
// })

// 말풍선 컴포넌트:
// - 흰 배경 + 2px 픽셀 테두리 (#1a1a2e) + 아래 꼬리
// - 3초 후 opacity 0 (CSS transition 1s)
// - setTimeout으로 DOM에서 제거
```

**DM 상태 전이:**
```
타 플레이어 카드 [비밀채팅] 클릭
  → socket.emit('dm_request', { target_user_id })
  → 상대방: socket.on('dm_incoming', { requester_user_id, nickname })
    → [수락]: socket.emit('dm_accept', { requester_user_id })
    → [거절]: socket.emit('dm_reject', { requester_user_id })

수락됨: 양쪽 socket.on('dm_started', { room_id, partner })
  → DM 채팅창 오픈 (화면 우하단 float)
  → socket.emit('dm_message', { room_id, message })
  → socket.on('dm_receive', { room_id, from_user_id, message })

거절됨: socket.on('dm_rejected') → "거절됐어요" Toast

닫기: socket.emit('dm_close', { room_id }) → 대화 종료
```

**BGM:**
```
기본: OFF (브라우저 자동재생 정책)
토글: 우상단 🔇/🔊
저장: localStorage('plaza_bgm') = 'on' | 'off'
소스: 저작권 무료 픽셀 BGM (8bit 루프, ~1MB)
```

상태:
- `loading` | `spectator` | `active` | `disconnected` | `reconnecting`

완료 기준 (F3-2):
- 맵 탐색, 카메라 추적, 이동 불가 충돌 정상 동작
- D-pad 모바일 이동 정상

완료 기준 (F3-3):
- 타 플레이어 위치 실시간 동기화
- 말풍선 3초 표시 후 fadeOut
- DM 수락/거절 플로우 정상
- WebSocket 끊김 후 재연결 또는 fallback(관전 모드) 전환

---

### 4.2 `/creatures/[id]`

목표:
- 공개 크리처 상세 + 소셜 액션 (좋아요/댓글/공유)

UI 구조 (davidkpiano 카드 — match/result와 동일 `PokemonCard` 컴포넌트):

```
배경: 크리처 주 타입 색상 + 다이아몬드 패턴

좌측:
  - 크리처 이미지 (기본)
  - 영상 있으면: 클릭 시 재생 (자동재생 없음)
    video.paused ? video.play() : video.pause()
  - 재생 아이콘 오버레이 (▶, 재생 중에는 숨김)

우측 (Lato 폰트):
  ◉ #{number}  {name}
  Type: <TypeBadge />
  by @{username}  ·  {날짜}
  닮은 포켓몬: {pokemon_name} {similarity}%
  {story}
  [버튼 — 내/타인 분기]

하단: 댓글 섹션
```

**버튼 분기:**
```typescript
if (isOwner) {
  // [이름 편집] [공개/비공개 전환] [삭제] [공유]
} else {
  // [❤️ 좋아요 {count}] [📤 공유] [광장에서 찾기]
}
```

**광장에서 찾기 버튼:**
```typescript
// GET /api/v1/plaza/online/{owner_user_id} → { is_online: boolean }
// is_online === true  → 활성화, 클릭 시 /plaza?focus={creature_id}
// is_online === false → disabled (회색, cursor: not-allowed), "오프라인"
```

**좋아요 구현 (이모지 리액션 API 사용):**
```typescript
// POST /api/v1/creatures/{id}/reactions { emoji_type: "❤️" }
// 좋아요 취소: 별도 DELETE API 추가 필요 (현재 미구현)
// 임시: 좋아요는 토글 불가, 한 번만 추가 (MVP)
// GET /api/v1/creatures/{id}/reactions/summary
//   → { counts: [{ emoji_type: "❤️", count: 42 }], total: 42 }
```

**댓글 섹션:**
```
최신순 정렬 (created_at DESC)
최대 100자 입력

각 댓글:
  아바타 + 닉네임 + 내용 + 날짜
  (본인 댓글) → [삭제] 버튼

비로그인: 입력창 탭 → 로그인 유도 모달
```

상태:
- `loading` | `ready` | `notFound` | `forbidden`

구현 단계:
1. `GET /api/v1/creatures/{id}` 데이터 로딩
2. 내/타인 소유 판별 + 버튼 분기 렌더링
3. 영상 click-to-play 구현
4. 좋아요 → `POST /api/v1/creatures/{id}/reactions { emoji_type: "❤️" }`
5. 공개/비공개 전환 → `PATCH /api/v1/creatures/{id} { is_public }`
6. `GET /api/v1/plaza/online/{owner_id}` → "광장에서 찾기" 활성/비활성
7. 댓글 로드 + 작성 + 삭제 구현

완료 기준:
- 비공개 크리처 외부 접근 → 404 처리 (`notFound()`)
- 댓글/좋아요 권한 분기 명확 (비로그인 차단)
- 영상 click-to-play 정상 동작

---

### 4.3 `/my`

목표:
- 계정/크리처 관리 홈. Instagram 프로필 구조.

UI 구조:
```
프로필 헤더:
  아바타 (대표 크리처 이미지, 원형)
  닉네임 + 한 줄 소개 (bio)
  통계: 크리처 {n}개 · 좋아요 받은 수 {m}개
  [프로필 편집] 버튼

탭:
  [내 크리처] / [좋아요한 크리처]

크리처 그리드 (3열):
  각 카드:
    - 크리처 thumbnail
    - 공개: 🌍 배지 / 비공개: 🔒 배지
    - 클릭 → /creatures/{id}

  빈 상태:
    내 크리처: "아직 크리처가 없어요. [크리처 만들러 가기]"
    좋아요: "좋아요한 크리처가 없어요"

설정 섹션:
  다크 모드 토글
  글자 크기 슬라이더 (3단계)

계정 섹션:
  [비밀번호 변경] → /my/password
  [회원 탈퇴]
```

**다크 모드:**
```typescript
// 초기값: localStorage('theme') || prefers-color-scheme
// 전환: document.documentElement.classList.toggle('dark')
//       + localStorage 저장
//       + PATCH /api/v1/users/me { dark_mode: boolean }
// CSS: html.dark { background-color: #1a1a2e; ... }
// transition: { transition: background-color 0.3s ease }
```

**글자 크기 조절:**
```typescript
const FONT_SIZES = { small: 14, medium: 16, large: 18 }
// document.documentElement.style.fontSize = `${size}px`
// + localStorage 저장
// + PATCH /api/v1/users/me { font_size: number }
// 슬라이더 조작 즉시 미리보기 적용 (debounce 500ms for API)
```

**회원 탈퇴 2단계 확인:**
```
1단계 모달: "탈퇴 시 크리처/댓글/좋아요/계정 정보가 즉시 삭제됩니다. 복구 불가."
           [취소] [다음]

2단계 모달:
  - 이메일 계정: 비밀번호 입력 확인
  - 소셜 계정: "탈퇴합니다" 텍스트 직접 입력

확인 후 DELETE /api/v1/users/me → 세션 종료 → / 이동
```

상태:
- `loading` | `ready` | `tabMyCreatures` | `tabLiked`

구현 단계:
1. `GET /api/v1/auth/me` 프로필 로딩
2. 탭별 `GET /api/v1/creatures/my` / `GET /api/v1/creatures/liked`
3. 다크 모드 토글 + localStorage + API 동기화
4. 글자 크기 슬라이더 즉시 적용 + API 동기화
5. 회원 탈퇴 2단계 모달 구현

완료 기준:
- 탭 전환 시 스크롤 위치 및 데이터 캐시 보존
- 빈 데이터 상태 안내 문구 명확

---

### 4.4 `/my/edit`

목표:
- 프로필 수정 + 실시간 카드 미리보기

UI 구조:
```
상단: PokemonCard 미리보기 (davidkpiano 스타일)
      편집 내용 즉시 반영 (controlled form → live preview)

하단 편집 폼:
  닉네임: input + 중복 검사 상태 아이콘 (✅/❌/⏳)
  한 줄 소개: textarea (최대 50자, 글자 수 카운터)
  대표 크리처: 가로 스크롤 카드 목록에서 선택

  [저장] [취소]
```

**닉네임 중복 검사:**
```typescript
// debounce 300ms
// GET /api/v1/users/check-nickname?q={nickname}
// 응답: { available: true | false }
// available === true:  초록 ✅ 표시
// available === false: "이미 사용 중인 닉네임이에요" 인라인 에러
// 본인 현재 닉네임: 중복 검사 skip
```

**저장/취소:**
```typescript
// [저장]: PATCH /api/v1/users/me { name, bio, avatar_creature_id }
//   - 성공: Toast "프로필이 업데이트됐어요" + /my 복귀
//   - 실패: Toast 에러 + 입력 상태 유지 (재시도 가능)
// [취소]: 변경 사항 버리기 확인 → /my 복귀
// 페이지 이탈 방지: 변경된 내용 있으면 `beforeunload` 경고
```

상태:
- `idle` | `checkingNickname` | `nicknameTaken` | `nicknameAvailable` | `saving`

완료 기준:
- 저장 실패 시 사용자 입력 보존
- 미리보기 카드가 편집 내용 즉시 반영

---

### 4.5 `/my/password`

목표:
- 계정 유형별 비밀번호 관리

UI 구조:
```
이메일 계정:
  현재 비밀번호 (show/hide 토글)
  새 비밀번호 + 강도 인디케이터
  새 비밀번호 확인
  [변경하기]

소셜 계정 (provider !== null):
  "Google/Kakao 계정은 비밀번호를 사용하지 않아요"
  폼 숨김
```

**API:**
```typescript
// PATCH /api/v1/users/me/password
// { current_password: string, new_password: string }
// 성공: Toast "비밀번호가 변경됐어요" + /my 복귀
// 실패 400 INVALID_CURRENT_PASSWORD: "현재 비밀번호가 올바르지 않아요"
```

완료 기준:
- 소셜 계정 분기가 UX 혼선을 만들지 않음
- 비밀번호 표시/숨기기 토글 정상 동작

---

## 5. 공통 컴포넌트/모듈 계획

신규 구현:
- `PlazaCanvas` (Phaser.js 래퍼, SSR 방지)
- `PlayerBadge` (크리처 스프라이트 + 닉네임)
- `ChatBubble` (말풍선, 3초 fadeOut)
- `DMPanel` (1:1 채팅창, 우하단 float)
- `CommentList` + `CommentEditor`
- `ReactionBar` (좋아요 버튼 + 카운트)
- `ProfileHeader`
- `SettingsPanel` (다크모드 + 글자크기)
- `ConfirmModal` (회원 탈퇴 2단계)

신규 훅/모듈:
- `usePlazaSocket(options)` — 광장 WebSocket 연결/이벤트 관리
- `useDarkMode()` — localStorage + html.dark + API 동기화
- `useFontSize()` — localStorage + html style + API 동기화

---

## 6. 상태 전이 모델

Feed/Detail 권한 전이:
```
anonymous  → readOnly  (댓글/좋아요 차단, 로그인 유도)
owner      → editable  (이름편집/공개전환/삭제)
nonOwner   → socialActions (좋아요/공유/광장에서찾기)
```

실시간 전이:
```
disconnected → connecting  (socket.connect())
connecting   → connected   (socket.on('connect'))
connected    → reconnecting(socket.on('disconnect'))
reconnecting → connected   (자동 재연결)
reconnecting → fallback    (5회 실패 → 관전 모드)
```

DM 전이:
```
idle → requesting  (dm_request 전송)
requesting → chatting  (dm_started 수신)
requesting → rejected  (dm_rejected 수신)
chatting → closed      (dm_close 전송 또는 수신)
```

---

## 7. API 계약 (확정 + 신규 추가 필요)

### 기존 API (확정)

#### GET `/api/v1/creatures/public`

```
쿼리: ?limit=20&offset=0
성공 (200):
{
  "success": true,
  "data": {
    "items": [{ "id", "name", "image_url", "video_url", "matched_pokemon_name_kr", ... }],
    "limit": 20,
    "offset": 0
  }
}
```

#### POST `/api/v1/creatures/{id}/reactions`

좋아요(❤️):
```json
{ "emoji_type": "❤️" }
```

성공 (200):
```json
{ "success": true, "data": { "id": "...", "emoji_type": "❤️", "created_at": "..." } }
```

#### GET `/api/v1/creatures/{id}/reactions/summary`

```json
{
  "success": true,
  "data": {
    "creature_id": "...",
    "counts": [{ "emoji_type": "❤️", "count": 42 }],
    "total": 42
  }
}
```

---

### 신규 추가 필요 API

> 아래 API는 현재 미구현. F3 착수 전 백엔드에서 추가.

#### PATCH `/api/v1/creatures/{id}` — 이름/공개 수정

```json
{ "name": "새 이름", "is_public": true }
```
성공: `{ success: true, data: { id, name, is_public } }`

#### DELETE `/api/v1/creatures/{id}` — 크리처 삭제

성공 (204): No Content

#### GET `/api/v1/creatures/my` — 내 크리처 목록

Header: `Authorization: Bearer {token}`
```json
{ "success": true, "data": { "items": [...], "total": 5 } }
```

#### GET `/api/v1/creatures/liked` — 좋아요한 크리처 목록

Header: `Authorization: Bearer {token}`
동일 구조

#### DELETE `/api/v1/creatures/{id}/reactions` — 좋아요 취소

Header: `Authorization: Bearer {token}`
성공 (204): No Content

#### POST `/api/v1/creatures/{id}/comments` — 댓글 작성

```json
{ "content": "멋진 크리처네요!" }
```
성공 (201): `{ id, content, author: { id, name }, created_at, is_mine: true }`

#### GET `/api/v1/creatures/{id}/comments` — 댓글 목록

```
쿼리: ?page=1&limit=20
성공 (200): { items: [...], total, page }
정렬: created_at DESC (최신순)
```

#### DELETE `/api/v1/creatures/{id}/comments/{comment_id}` — 댓글 삭제

에러: 403 (본인 댓글 아닌 경우)

#### GET `/api/v1/users/check-nickname` — 닉네임 중복 검사

```
쿼리: ?q={nickname}
성공: { "available": true | false }
```

#### PATCH `/api/v1/users/me` — 프로필 수정

```json
{ "name": "닉네임", "bio": "소개", "avatar_creature_id": "uuid", "dark_mode": true, "font_size": 16 }
```

#### PATCH `/api/v1/users/me/password` — 비밀번호 변경

```json
{ "current_password": "old", "new_password": "new" }
```
에러: 400 `INVALID_CURRENT_PASSWORD`

#### DELETE `/api/v1/users/me` — 회원 탈퇴

```json
{ "password": "..." }
```
성공 (204): No Content
처리: 크리처/댓글/좋아요/사용자 레코드 CASCADE 삭제

#### GET `/api/v1/plaza/online/{user_id}` — 광장 온라인 상태

```json
{ "is_online": true, "x": 512, "y": 480 }
```

---

### WebSocket 이벤트 (socket.io, /plaza 네임스페이스)

연결:
```typescript
io('/plaza', { auth: { token: accessToken } })
```

| 방향 | 이벤트 | 데이터 |
|------|--------|--------|
| C→S | `join` | `{ creature_id, x, y }` |
| C→S | `move` | `{ x, y }` |
| C→S | `chat` | `{ message }` (최대 20자) |
| C→S | `dm_request` | `{ target_user_id }` |
| C→S | `dm_accept` | `{ requester_user_id }` |
| C→S | `dm_reject` | `{ requester_user_id }` |
| C→S | `dm_message` | `{ room_id, message }` |
| C→S | `dm_close` | `{ room_id }` |
| S→C | `welcome` | `{ players: [{ user_id, creature_id, nickname, x, y }] }` |
| S→C | `player_join` | `{ user_id, creature_id, nickname, x, y }` |
| S→C | `player_move` | `{ user_id, x, y }` |
| S→C | `player_leave` | `{ user_id }` |
| S→C | `chat_broadcast` | `{ user_id, message }` |
| S→C | `dm_incoming` | `{ requester_user_id, nickname }` |
| S→C | `dm_started` | `{ room_id, partner: { user_id, nickname } }` |
| S→C | `dm_rejected` | `{}` |
| S→C | `dm_receive` | `{ room_id, from_user_id, message }` |
| S→C | `dm_closed` | `{ room_id }` |
| S→C | `error` | `{ code, message }` |

---

## 8. 예외/엣지케이스

1. 피드 로딩 중 중복 페이징 요청 → `isLoadingMore` flag로 중복 차단
2. 좋아요 연타 → 첫 요청 중 버튼 disabled, 완료 후 활성화
3. 비공개 전환 직후 공유 링크 접근 → 404 처리
4. 닉네임 중복 검사 API 지연 (300ms debounce) → ⏳ 아이콘 표시
5. WebSocket 불안정 (모바일 네트워크 전환) → 자동 재연결 5회, 실패 시 fallback
6. DM 요청 시 상대방 오프라인 → `error { code: "USER_OFFLINE" }` → Toast
7. 관전 모드: D-pad 노출하지 않음, 이동 이벤트 전송 안함
8. 회원 탈퇴 후 기존 세션 쿠키 → 백엔드에서 블랙리스트 처리 또는 만료 대기

---

## 9. QA 체크포인트

Happy path:
1. 크리처 공개 → `/plaza` 피드에 노출 확인
2. `/creatures/[id]` → ❤️ 좋아요 → 카운트 증가
3. `/creatures/[id]` → 댓글 작성 → 최신순 정상 정렬
4. `/my` → 프로필 편집 → 카드 미리보기 즉시 반영
5. `/plaza` → 내 크리처 이동 (WASD/D-pad)
6. `/plaza` → 채팅 입력 → 말풍선 3초 후 fadeOut
7. DM 요청 → 수락 → 채팅 → 종료 플로우
8. 다크 모드 토글 → 즉시 전환 + 새로고침 후 유지

Failure path:
1. 비공개 크리처 외부 링크 접근 → 404
2. 비로그인 댓글 작성 클릭 → 로그인 유도 모달
3. WebSocket 연결 실패 → 관전 모드 fallback
4. DM 거절 → "거절됐어요" Toast
5. 닉네임 중복 → 인라인 에러 + 저장 버튼 disabled

Recovery path:
1. WebSocket 끊김 후 재연결 → 타 플레이어 목록 재동기화
2. 댓글 저장 실패 → 입력 내용 유지 + 재시도 가능
3. 회원 탈퇴 취소 → 2단계 모달에서 [취소] → 정상 복귀

---

## 10. 후속 백로그

| 항목 | 미루는 이유 | 예상 Stage | 선행조건 |
|------|-----------|-----------|---------|
| 광장 구역 분할/방 생성 | 현재 단일 맵으로 충분 | F4 | 서버 부하 측정 |
| DM 히스토리 저장 | DB 스키마 추가 필요 | F4 | 메시지 테이블 설계 |
| 이모지 리액션 다양화 | ❤️ 단일로 MVP 충분 | F4 | — |
| 추천 피드/탐색 알고리즘 | ML 파이프라인 필요 | F4 | 충분한 데이터 축적 |
| 신고/차단 기능 | 운영 정책 미확정 | F4 | — |
