# Stage F2 구현전략: Result + Generation + Auth

> **상태: 미착수 (다음 구현 대상)**

---

## 1. Stage 목표

- `/match` 선택 결과를 기반으로 생성 파이프라인을 실행하고 `/result/[id]`까지 안정적으로 연결한다.
- 인증 화면(`/login`, `/signup`)을 도입해 게스트 사용자의 저장/공유 전환을 지원한다.

핵심 성공 지표:
- `/match` 선택 후 `/result/[id]` 도달률
- 생성 실패/타임아웃 복구율
- 로그인 유도 모달에서 인증 전환율

---

## 2. 포함/제외 범위

포함 라우트:
- `/match` (F1 handoff → 카드 완성 + 선택 → 생성 연결)
- `/generate/[id]`
- `/result/[id]`
- `/login`
- `/signup`

제외 라우트:
- `/plaza`
- `/creatures/[id]`
- `/my*`

---

## 3. 사용자 플로우

```
/match
  → 포켓몬 선택
  → POST /api/v1/creatures  (creature 레코드 생성)
  → /generate/{creature_id}
    → POST /api/v1/creatures/{id}/generate  (파이프라인 트리거)
    → GET /api/v1/veo-jobs/{job_id}  (영상 폴링 3초 간격)
    → 완료 → /result/{creature_id}
      → 결과 확인 + 이름 편집 + 공유
      → 비로그인 저장/공유 클릭 → /login?next=/result/{id}
      → 로그인 완료 → 원래 액션 자동 재실행
```

---

## 4. 페이지별 UI 구현 단계

---

### 4.1 `/match` — F1 handoff + F2 카드 완성

목표:
- davidkpiano 카드 디자인 완성 + 선택 → 생성 파이프라인 연결

UI 구조:
- Desktop: 3열 가로 배치 (1위 중앙, scale(1.05), "BEST MATCH" 뱃지)
- Mobile: 세로 스택 (1위 맨 위)

**카드 구현 명세 (`PokemonCard` 컴포넌트):**

```tsx
// 카드 배경: 타입 색상 + 다이아몬드 패턴
style={{
  background: `${TYPE_COLORS[primary_type]}`,
  backgroundImage: `
    repeating-linear-gradient(
      45deg,
      transparent, transparent 4px,
      rgba(0,0,0,0.08) 4px, rgba(0,0,0,0.08) 5px
    )
  `
}}

// 좌측 이미지 패널
<div className="pokemon-image-panel">
  <div className="radial-glow" />  // 라디얼 글로우
  <img
    src={`https://www.serebii.net/pokemongo/pokemon/${String(pokemon_id).padStart(3,'0')}.png`}
    className="bounce-head"  // 바운스 애니메이션
    onError={handleImageError}  // fallback: 포켓볼 placeholder
  />
</div>

// 우측 정보 패널 (font-family: Lato)
<div className="dex-panel">
  <p className="pokemon-number">◉ #{String(pokemon_id).padStart(3,'0')}</p>
  <h2 className="pokemon-name">{name_kr}</h2>
  <div><TypeBadge type={primary_type} /></div>
  <p>유사도: {(similarity * 100).toFixed(1)}%</p>
  {reasons.slice(0,2).map(r => <span>{r.label}</span>)}
  <ProgressBar value={similarity * 100} color={TYPE_COLORS[primary_type]} />
  <Button onClick={handleSelect}>이 포켓몬으로 시작하기</Button>
</div>
```

CSS 애니메이션:
```css
@keyframes bounce-head {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-8px); }
}
.bounce-head { animation: bounce-head 2s ease-in-out infinite; }

.radial-glow {
  background: radial-gradient(
    circle at 50% 60%,
    rgba(255,255,255,0.3),
    transparent 70%
  );
}
```

상태:
- `loadingFromSession` | `noSession` | `ready` | `selecting` | `creating` | `createError`

구현 단계:
1. `PokemonCard` 컴포넌트 구현 (타입 색상, 다이아몬드 패턴, 바운스)
2. sessionStorage 로드 → Top3 카드 렌더링
3. 1위 카드 강조 스타일 (scale, BEST MATCH 뱃지)
4. 카드 선택 → 선택 강조 + 나머지 fade-out (0.4s transition)
5. 0.6s 후 `POST /api/v1/creatures` 호출
6. 성공 → `router.push(/generate/${creature_id})`
7. 실패 → 카드 선택 유지 + "다시 시도" Toast

완료 기준:
- 세션 유실 시 `/upload` 즉시 복귀
- 카드 데이터 누락 필드 있어도 렌더링 불깨짐
- 중복 클릭으로 duplicate 생성 요청 발생 안함

---

### 4.2 `/generate/[id]`

목표:
- 대기 경험과 생성 상태 추적을 동시에 제공

UI 구조:
- 풀스크린 (Header/MobileNav 없음)
- 배경: `#1D1F20`

```
상단 (fixed, opacity 0.8):
  <PocketmanLogo size="md" />

중앙 (절대 위치, 세로 중앙):
  <p className="status-text" style={{ color: '#fff', opacity: 0.5 }}>
    {statusMessages[currentStep]}
  </p>

하단:
  포켓몬 퍼레이드 애니메이션
```

**상태 텍스트 시퀀스:**
```typescript
const statusMessages = [
  { text: "나만의 크리처가 태어나고 있어요...",   delay: 0 },
  { text: "포켓몬의 특성을 융합하고 있어요...",   delay: 10000 },
  { text: "거의 다 됐어요! 조금만 기다려주세요",  delay: 25000 },
]
// useEffect에서 setTimeout으로 순차 전환
```

**포켓몬 퍼레이드 구현 (simeydotme CodePen ZGzrBQ 기반):**

```typescript
// useEffect에서 마운트 시 즉시 실행 (클릭 트리거 제거)
useEffect(() => {
  initParade()  // 원본의 document.body.onclick 제거, 직접 호출
  return () => cleanupParade()
}, [])
```

```css
/* 스프라이트 소스 */
.pokemon-sprite {
  background-image: url('https://assets.codepen.io/13471/pokemon-sprite.png');
  width: 80px;
  height: 80px;
  image-rendering: pixelated;
  animation: poke-walk steps(1) 0.4s infinite,
             poke-move linear {duration}s infinite;
}

@keyframes poke-walk {
  0%   { background-position-x: 0px; }
  50%  { background-position-x: -80px; }
  100% { background-position-x: 0px; }
}

@keyframes poke-move {
  0%   { transform: translateX(110vw); }
  100% { transform: translateX(-120px); }
}
```

**폴링 훅 (`useVeoPolling`):**

```typescript
// 생성 파이프라인 흐름:
// 1. POST /api/v1/creatures/{id}/generate → 응답에 veo_job.id 포함
// 2. GET /api/v1/veo-jobs/{job_id} → status 폴링
// 3. status === 'succeeded' → router.push('/result/{id}')

interface UseVeoPollingOptions {
  creatureId: string
  onSuccess: (creatureId: string) => void
  onError: (message: string) => void
}

// 폴링 설정: 3초 간격, 최대 25회 (75초)
// veo_job status: 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled'
```

상태:
- `init` | `triggering` | `polling` | `succeeded` | `failed` | `timeout`

구현 단계:
1. 페이지 마운트 시 퍼레이드 즉시 시작 (`useEffect`)
2. 상태 텍스트 타이머 시작 (0s/10s/25s)
3. `POST /api/v1/creatures/{id}/generate` 호출 (1회)
4. 응답의 `veo_job.id`로 폴링 시작
5. `status === 'succeeded'` → `router.push('/result/${creatureId}')`
6. `status === 'failed'` / 25회 초과 → 에러 처리

완료 기준:
- 탭 백그라운드 전환/복귀 시 폴링 비정상 중복 없음 (`useRef`로 인터벌 참조 관리)
- 타임아웃 시 명확한 안내 + [다시 시도] / [처음으로] CTA 제공

---

### 4.3 `/result/[id]`

목표:
- 생성 결과를 감정적으로 전달하고 공유 액션을 유도

UI 구조 (davidkpiano 카드, match 페이지와 동일 컴포넌트):

```
배경: 크리처 주 타입 색상 + 다이아몬드 패턴

좌측:
  - 크리처 이미지/영상 (video_url 있으면 video 태그, 없으면 img)
  - 자동재생 없음 → 클릭 시 재생 (video.play())
  - 라디얼 글로우
  - 🎉 canvas-confetti 파티클

우측 (Lato 폰트):
  - ◉ #{creature_number}  <InlineEditableName value={name} />
  - Type: <TypeBadge /> x N
  - 닮은 포켓몬: {pokemon_name} {(similarity*100).toFixed(1)}%
  - {story} (크리처 설명)
  - [📤 공유] [🌍 광장에 올리기]
  - [💾 저장] [🔄 다시 만들기]
```

**등장 애니메이션 시퀀스:**
```typescript
// useEffect로 순차 실행
const sequence = [
  { delay: 0,    action: () => setShowBackground(true) },
  { delay: 300,  action: () => setShowCard(true) },
  { delay: 800,  action: () => fireConfetti() },
  { delay: 1200, action: () => setShowMeta(true) },
  { delay: 1800, action: () => setShowButtons(true) },
]

// confetti 설정
confetti({
  particleCount: 100,
  spread: 70,
  colors: ['#f15946', '#009087', '#FFCE00'],
  origin: { y: 0.4 }
})
```

**인라인 이름 편집 (`InlineEditableName`):**
```typescript
// 클릭 → input 전환
// Enter 또는 ✅ → PATCH /api/v1/creatures/{id} { name }  (신규 추가 필요)
// Escape / blur → 원래 이름으로 복귀
// 실패 → Toast 에러 + 원래 이름 복원
```

**버튼 동작:**
| 버튼 | 로그인 | 비로그인 |
|------|--------|---------|
| 📤 공유 | Web Share API → fallback 링크 복사 | 동일 (공유는 인증 불필요) |
| 🌍 광장에 올리기 | PATCH /creatures/{id} { is_public: true } → /plaza | 로그인 유도 모달 |
| 💾 저장 | 이미지/GIF 다운로드 | 로그인 유도 모달 |
| 🔄 다시 만들기 | /upload 이동 | /upload 이동 |

상태:
- `loading` | `ready` | `editing` | `actionPending` | `error`

구현 단계:
1. `GET /api/v1/creatures/{id}` 데이터 로딩
2. 카드 등장 애니메이션 시퀀스 실행
3. 0.8s에 confetti 발화 (1회)
4. `InlineEditableName` 컴포넌트 구현 (편집/저장/취소)
5. 공유/광장/저장 버튼 연결
6. 비로그인 시 `AuthGateModal` 표시 + `?next=` 복귀 정책

완료 기준:
- 결과 데이터 일부 누락 시에도 핵심 액션 버튼 유지
- 컨페티가 0.8s 정확히 발화됨
- 이름 편집 실패 시 원래 이름 복원

---

### 4.4 `/login`

목표:
- 인증 성공 후 원래 맥락(`?next=`)으로 복귀

**데스크톱/태블릿 레이아웃 (Instagram 50/50 구조):**

```
┌──────────────────────┬──────────────────────┐
│   좌측 브랜딩 패널     │    우측 로그인 폼      │
│   (50%)              │    (50%)              │
│                       │                       │
│  PocketmanLogo        │  소셜 로그인 버튼들     │
│                       │  [Google로 계속하기]    │
│  포켓몬 3장 부채꼴     │  [Kakao로 계속하기]    │
│  - 피카츄 (-8deg)     │                       │
│  - 파이리 (+5deg)     │  ─── 또는 ───          │
│  - 뮤츠 (-3deg)       │                       │
│  각 포켓몬 눈 애니메이션│  이메일 input          │
│                       │  비밀번호 input        │
│  배경: beige→coral    │  [로그인]              │
│  오로라 그라데이션      │                       │
│                       │  비밀번호 찾기 | 회원가입│
└──────────────────────┴──────────────────────┘
```

**눈 애니메이션 CSS:**
```css
@keyframes eyes-look {
  0%, 45%  { transform: translateX(0); }
  50%, 65% { transform: translateX(2px); }
  70%, 85% { transform: translateX(-2px); }
  90%, 100%{ transform: translateX(0); }
}

@keyframes eye-blink {
  0%, 96%  { transform: scaleY(1); }
  97%, 99% { transform: scaleY(0.1); }
  100%     { transform: scaleY(1); }
}

/* 포켓몬별 delay */
.pikachu-eyes  { animation-delay: 0s; }
.charmander-eyes { animation-delay: 1.5s; }
.mewtwo-eyes   { animation-delay: 3s; }
```

**모바일 레이아웃 (Dribbble 레퍼런스 — Anas Tradi):**

```
┌──────────────────────┐
│   팔레트 타운 일러스트  │ 55%
│   (애니메이션)         │
│                       │
│  배경: #2DA2A0        │
│  - Professor Oak 연구소│
│  - 주인공 집           │
│  - 나무/도로/풀숲      │
│  - 피카츄              │
│                       │
│  애니메이션:           │
│  구름 이동 8s          │
│  Pidgey 비행 6s        │
│  피카츄 꼬리 0.5s      │
│  풀숲 흔들림 2s        │
├──────────────────────┤
│   로그인 폼 카드       │ 45%
│   (슬라이드업)         │
│   [Google로 계속하기]  │
│   [Kakao로 계속하기]   │
│   이메일/비밀번호 폼   │
└──────────────────────┘
```

```css
/* 팔레트 타운 색상 */
:root {
  --sky: #2DA2A0;
  --tree-dark: #1B584E;
  --tree-light: #4A992D;
  --roof: #C8A43E;
}

/* 구름 이동 */
@keyframes cloud-move { 0%{left:-200px} 100%{left:110vw} }
.cloud { animation: cloud-move 8s linear infinite; }

/* Pidgey 비행 */
@keyframes pidgey-fly {
  0%{transform: translate(0,0)} 50%{transform: translate(200px,-30px)} 100%{transform: translate(400px,0)}
}
.pidgey { animation: pidgey-fly 6s ease-in-out infinite; }

/* 피카츄 꼬리 */
@keyframes pikachu-tail { 0%,100%{rotate:-10deg} 50%{rotate:10deg} }
.pikachu-tail { animation: pikachu-tail 0.5s ease-in-out infinite; }

/* 폼 카드 슬라이드업 */
@keyframes slide-up { from{transform:translateY(100%)} to{transform:translateY(0)} }
.login-form-card { animation: slide-up 0.6s ease-out forwards; }
```

상태:
- `idle` | `loading` | `error` | `success`

구현 단계:
1. 뷰포트 크기 기반 레이아웃 분기 (lg 이상: 데스크톱, 미만: 모바일)
2. 모바일: 팔레트 타운 SVG/CSS 일러스트 + 5개 애니메이션 구현
3. 데스크톱: 포켓몬 3장 부채꼴 배치 + 눈 애니메이션 CSS
4. 소셜 버튼: NextAuth `signIn('google')`, `signIn('kakao')`
5. 이메일 폼: NextAuth `signIn('credentials', { email, password })`
6. 성공 시 `?next=` 파라미터 우선, 없으면 `/upload`

완료 기준:
- 로그인 상태에서 접근 시 `/upload` 즉시 우회
- 소셜 로그인 OAuth 취소 후 로그인 페이지 유지 (에러 표시)

---

### 4.5 `/signup`

목표:
- 신규 유저 가입 후 즉시 퍼널 복귀

UI 구조:
- `/login`과 동일 레이아웃 구조 (일관성)
- 우측/하단 폼만 회원가입 폼으로 교체

폼 필드:
- 이름 (2~20자)
- 이메일 (RFC 형식)
- 비밀번호 (8자 이상, 영문+숫자)
- 비밀번호 확인

**비밀번호 강도 인디케이터:**
```
약함 (숫자 또는 문자만): 빨간 바 1/3
보통 (영문+숫자 8자):   노란 바 2/3
강함 (12자 이상 혼합):  초록 바 3/3
```

상태:
- `idle` | `validating` | `submitting` | `duplicateEmail` | `success`

구현 단계:
1. 폼 필드/검증/강도 표시 구현
2. 중복 이메일 → 서버 409 → `{ success: false, error_code: "EMAIL_ALREADY_EXISTS" }` 인라인 에러
3. 가입 성공 시 자동 로그인 (`signIn('credentials')`)
4. `/upload` 또는 `?next=`로 이동

완료 기준:
- 비밀번호 검증 실패가 폼 UX를 방해하지 않음 (인라인 에러)
- 가입 즉시 자동 로그인 (별도 로그인 화면 없음)

---

## 5. 공통 컴포넌트/모듈 계획

신규 구현:
- `PokemonCard` (davidkpiano 풀 디자인 — match/result/creatures 공용)
- `TypeBadge` (18개 타입)
- `InlineEditableName` (result 페이지 이름 편집)
- `AuthGateModal` (비로그인 액션 차단 모달)
- `ProgressBar` (유사도 바)
- `PaletteAnimation` (모바일 로그인 일러스트)

신규 훅:
- `useVeoPolling(creatureId, options)` — veo-job 폴링
- `useAuthRedirect()` — next= 복귀 정책

신규 라이브러리:
- `canvas-confetti`
- `next-auth` (Auth.js v5)

---

## 6. 상태 전이 모델

Generate 전이:
```
init        → triggering (마운트)
triggering  → polling    (POST /generate 성공, veo_job_id 확보)
triggering  → failed     (POST /generate 실패)
polling     → succeeded  (veo_job.status === 'succeeded')
polling     → failed     (veo_job.status === 'failed'|'canceled')
polling     → timeout    (25회 초과)
succeeded   → (router.push /result/{id})
```

Auth gate 전이:
```
actionRequested + 비인증 → blocked(auth)
blocked(auth) + 로그인성공 → resume(action)
blocked(auth) + 취소      → ready
```

---

## 7. API 계약 (확정)

### POST `/api/v1/creatures` — 크리처 레코드 생성

요청:
```json
{
  "matched_pokemon_id": 25,
  "match_rank": 1,
  "similarity_score": 0.8923,
  "match_reasons": [{ "dimension": "visual", "label": "큰 눈", "user_value": 0.8, "pokemon_value": 0.75 }],
  "name": "임시이름"
}
```

성공 응답 (200):
```json
{
  "success": true,
  "data": {
    "id": "creature-uuid",
    "matched_pokemon_id": 25,
    "name": "임시이름",
    "is_public": false
  }
}
```

`name`은 `/generate` 단계에서 AI가 재생성하므로 임시값 허용.

---

### POST `/api/v1/creatures/{id}/generate` — 생성 파이프라인 트리거

요청:
```json
{
  "regenerate_name_story": true,
  "regenerate_image": true,
  "trigger_video": true
}
```

성공 응답 (200):
```json
{
  "success": true,
  "data": {
    "creature": { "id": "...", "name": "AI 생성 이름", "story": "...", "image_url": "..." },
    "veo_job": {
      "id": "veo-job-uuid",
      "status": "queued",
      "video_url": null
    }
  }
}
```

`veo_job`이 null인 경우: 영상 생성 실패/스킵 → `image_url`로 fallback.

---

### GET `/api/v1/veo-jobs/{job_id}` — 영상 생성 상태 폴링

성공 응답 (200):
```json
{
  "success": true,
  "data": {
    "id": "veo-job-uuid",
    "creature_id": "creature-uuid",
    "status": "succeeded",
    "video_url": "https://...",
    "error_message": null
  }
}
```

status 값: `queued` | `running` | `succeeded` | `failed` | `canceled`

폴링 종료 조건:
| status | 처리 |
|--------|------|
| `succeeded` | `video_url` 확보 → /result 이동 |
| `failed` / `canceled` | 에러 표시 (image_url로 fallback 가능) |
| 25회 초과 (75초) | timeout 에러 |

---

### GET `/api/v1/creatures/{id}` — 결과 상세 조회

성공 응답 (200):
```json
{
  "success": true,
  "data": {
    "id": "...",
    "matched_pokemon_id": 25,
    "match_rank": 1,
    "similarity_score": 0.8923,
    "match_reasons": [...],
    "name": "AI 생성 이름",
    "story": "크리처 설명 텍스트",
    "image_url": "https://...",
    "video_url": "https://...",
    "is_public": false,
    "created_at": "2026-03-12T00:00:00Z",
    "matched_pokemon_name_kr": "피카츄"
  }
}
```

---

### PATCH `/api/v1/creatures/{id}` — 이름/공개 수정 (신규 추가 필요)

> **백엔드 미구현 — F2 착수 전 백엔드에서 추가**

요청:
```json
{ "name": "새 이름" }
```
또는
```json
{ "is_public": true }
```

성공 응답 (200):
```json
{
  "success": true,
  "data": { "id": "...", "name": "새 이름", "is_public": true }
}
```

에러:
- `404 CREATURE_NOT_FOUND`

---

### Auth 엔드포인트 (신규 추가 필요)

> **백엔드 미구현 — F2 착수 전 백엔드에서 추가**

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/auth/register` | 이메일 회원가입 |
| POST | `/api/v1/auth/login` | 이메일 로그인 → JWT 발급 |
| POST | `/api/v1/auth/social` | OAuth 콜백 처리 |
| GET | `/api/v1/auth/me` | 현재 사용자 정보 |

`POST /api/v1/auth/register` 요청:
```json
{ "name": "홍길동", "email": "user@example.com", "password": "password123" }
```
성공 (201): `{ access_token, user: { id, name, email } }`
에러 (409): `{ error_code: "EMAIL_ALREADY_EXISTS" }`

`POST /api/v1/auth/login` 요청:
```json
{ "email": "user@example.com", "password": "password123" }
```
성공 (200): `{ access_token, user: { id, name, email } }`
에러 (401): `{ error_code: "INVALID_CREDENTIALS" }`

---

## 8. 예외/엣지케이스

1. 생성 트리거 성공 후 `veo_job`이 null → `image_url`로 fallback 처리 (영상 없이 결과 표시)
2. 폴링 중 네트워크 단절 → interval clear 후 페이지 복귀 시 재시작
3. `/result/[id]` 직접 URL 진입 → `GET /creatures/{id}` 조회 (세션 불필요)
4. 로그인 도중 OAuth 창 닫음 → NextAuth error callback → 로그인 페이지 유지 + "취소됨" Toast
5. Web Share API 미지원 (일부 Android) → 링크 복사 fallback
6. `veo_job.status === 'canceled'` → 영상 없이 image_url로 결과 표시 (에러 아님)
7. 이름 편집 중 새로고침 → 편집 취소, 원래 이름 유지

---

## 9. QA 체크포인트

Happy path:
1. `/match` 카드 선택 → `/generate/[id]` 진입 → 퍼레이드 즉시 시작
2. 폴링 완료 → `/result/[id]` 자동 이동
3. 컨페티 0.8s에 발화 (1회)
4. 이름 클릭 → 편집 → Enter → 저장 확인
5. 비로그인 [광장에 올리기] → 모달 → 로그인 → 원래 액션 실행
6. 모바일 로그인 → 팔레트 타운 애니메이션 (구름/Pidgey/피카츄) 확인
7. 데스크톱 로그인 → 포켓몬 눈 애니메이션 확인

Failure path:
1. 생성 실패(`veo_job.status === 'failed'`) → 에러 안내 + [다시 시도] 버튼
2. 폴링 타임아웃(75초) → "시간이 너무 걸려요" 안내 + [처음으로] 버튼
3. 로그인 실패 → "이메일 또는 비밀번호가 올바르지 않아요" 메시지
4. 이메일 중복 가입(409) → 인라인 에러 표시

Recovery path:
1. 생성 실패 후 [다시 시도] → 폴링 재시작
2. 로그인 완료 → 원래 액션 자동 재실행
3. 결과 페이지 재진입 → `GET /creatures/{id}` 재조회 정상

---

## 10. 후속 백로그

| 항목 | 미루는 이유 | 예상 Stage | 선행조건 |
|------|-----------|-----------|---------|
| 카카오 SDK 고급 공유 포맷 | OAuth 설정 복잡도 | F3 이후 | 카카오 앱 등록 |
| 결과 페이지 GIF 다운로드 | canvas 처리 복잡도 | F3 이후 | — |
| 인증 세션 갱신/장치 관리 | 보안 고도화 | F3 이후 | — |
| 모바일 로그인 애니메이션 픽셀아트 고도화 | 현재 CSS로 충분 | F3 이후 | — |
