# Stage 개발일지

## 0) 기본 정보
- 파트: `frontend`
- Stage: `f2-result-generation`
- 작성자: `sups`
- 작성일: `2026-03-13`
- 관련 이슈/PR: N/A

## 1) Stage 목표/범위
- 목표: `/match`, `/generate/[id]`, `/result/[id]` 3개 라우트 완성 + 공통 기반 정비
- 이번 Stage에서 포함한 범위:
  - **F2-A**: tailwind.config.ts 애니메이션 추가, lib 공통 파일 (types/constants/storage/api) 확장, ProgressBar/Modal 컴포넌트 신규
  - **F2-B**: `/match` 페이지 완성 + `PokemonCard` 컴포넌트 (davidkpiano 디자인)
  - **F2-C**: `/generate/[id]` 풀스크린 + `useVeoPolling` 훅 + 포켓몬 퍼레이드 애니메이션
  - **F2-D**: `/result/[id]` 완성 + `InlineEditableName`, `AuthGateModal` 컴포넌트 + canvas-confetti
- 제외한 범위:
  - `/login`, `/signup` 페이지 (F2-E, B-2 백엔드 구현 후 착수)
  - Auth 백엔드 (B-2 스테이지)
  - 광장 공개 소유권 검증 (F3)
  - GIF/Canvas 다운로드 (F3)

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: tailwind.config.ts — 11개 keyframe 일괄 추가**
- bounce-head, poke-walk, poke-move, fade-in, slide-up, card-reveal
- eyes-look, eye-blink, cloud-move, pidgey-fly, pikachu-tail
- 이유: login/generate/result 등 여러 페이지에서 재사용, CSS 모듈보다 Tailwind utility가 Next.js 빌드와 일관성 유지

**결정 2: PokemonCard — serebii 스프라이트**
- `https://www.serebii.net/pokemongo/pokemon/{id 3자리}.png` 사용
- `onError` 핸들러로 포켓볼 placeholder fallback
- 이유: 공식 포켓몬 GO 스프라이트, 1~386번 커버리지 보장

**결정 3: useVeoPolling — useCallback + mountedRef로 메모리 누수 방지**
- `mountedRef.current`로 언마운트 후 setState 방지
- `clearPolling()` useCallback로 stable reference 확보
- `veo_job.status === 'canceled'` → 에러 아닌 성공(fallback)으로 처리
- 이유: 폴링 중 탭 전환/언마운트 시 인터벌 중복 방지

**결정 4: generate 페이지 풀스크린 (z-[100])**
- `fixed inset-0 z-[100]` — Header(z-50), MobileNav보다 높은 레이어
- 이유: 생성 대기 중 UI 방해 요소 제거, 몰입감 제공

**결정 5: result 페이지 배경 색상 임시값**
- `matched_pokemon_id`로 타입 조회 API가 없으므로 `#68A090` 임시값 사용
- TODO 주석 명시 — F3에서 `pokemon_master` 타입 조회로 교체 예정

**결정 6: AuthStorage SSR 완전 안전화**
- `saveToken`, `saveUser`, `clear` 모두 `typeof window === "undefined"` 가드 추가
- 코드 리뷰 피드백 반영

**결정 7: Modal backdrop 클릭 닫기 수정**
- 기존: overlay ref 비교 (backdrop 자식 클릭 시 불일치)
- 수정: backdrop `<div>`에 `onClick={onClose}` 직접 연결
- 코드 리뷰 피드백 반영

### 2.2 핵심 로직 설명

**PokemonCard 선택 → 크리처 생성 흐름:**
1. 카드 클릭 → `selectedPokemon` 세팅 + 나머지 카드 `isFading=true` (opacity 0.35)
2. 600ms setTimeout 대기 (선택 애니메이션)
3. `isCreating.current = true` (중복 요청 차단)
4. `POST /creatures` 호출
5. 성공 → `router.push(/generate/${id})`
6. 실패 → `isCreating.current = false`, 선택 해제, Toast

**useVeoPolling:**
1. 마운트 즉시 `POST /creatures/{id}/generate` 트리거
2. 응답의 `veo_job.id`로 3초 간격 폴링 시작
3. `succeeded` → `onSuccess(creatureId)` → `/result/${id}` 이동
4. `failed`/`canceled` → `onSuccess(creatureId)` (image_url fallback)
5. 25회 초과 → `onError()` → 에러 UI (타임아웃)

**Result 페이지 등장 시퀀스 (ms):**
- 0: 배경 색상 전환 시작
- 300: 카드 scale+fade 등장
- 800: confetti 발화 (1회, ref로 중복 방지)
- 1200: story 텍스트 표시
- 1800: 액션 버튼 등장

### 2.3 변경/신규 파일 목록

**F2-A:**
- `frontend/tailwind.config.ts`: 11개 keyframe + animation 추가
- `frontend/lib/constants.ts`: SESSION_KEY_ACCESS_TOKEN, SESSION_KEY_AUTH_USER 추가
- `frontend/lib/types.ts`: AuthUser, AuthResponse, AuthRegisterPayload, AuthLoginPayload, CreaturePatchPayload 추가
- `frontend/lib/storage.ts`: AuthStorage 추가 + SSR 가드 전체 적용
- `frontend/lib/api.ts`: patchCreature(), register(), login(), getMe() 추가, withAuth 파라미터 추가
- `frontend/components/ui/ProgressBar.tsx`: 신규
- `frontend/components/ui/Modal.tsx`: 신규 (backdrop onClick, ESC 닫기, scroll lock)

**F2-B:**
- `frontend/components/features/match/PokemonCard.tsx`: 신규 (davidkpiano 카드)
- `frontend/app/match/page.tsx`: 전면 재작성

**F2-C:**
- `frontend/hooks/useVeoPolling.ts`: 신규
- `frontend/app/generate/[id]/page.tsx`: 전면 재작성 (풀스크린 + 퍼레이드)

**F2-D:**
- `frontend/components/features/result/InlineEditableName.tsx`: 신규
- `frontend/components/features/result/AuthGateModal.tsx`: 신규
- `frontend/app/result/[id]/page.tsx`: 전면 재작성

**버그 수정 (코드 리뷰 1차):**
- `frontend/app/plaza/page.tsx`: loadInitial useEffect 내부 인라인 (lint 경고 제거)

**버그 수정 (코드 리뷰 2차):**
- `frontend/app/generate/[id]/page.tsx`: 스프라이트 경로 `/images/pokemon-sprite.png` → `/pokemon-sprite.png`
- `frontend/app/generate/[id]/page.tsx`: timerRefs.current 캡처 변수로 cleanup 경고 제거
- `frontend/app/result/[id]/page.tsx`: 공유 URL `/creatures/{id}` → `/result/{id}` (F3 placeholder 우회)
- `frontend/components/features/result/AuthGateModal.tsx`: dead link 제거, "준비 중" Toast로 교체
- `frontend/hooks/useVeoPolling.ts`: `inFlightRef` 추가로 setInterval async 중복 요청 방지
- `frontend/components/features/match/PokemonCard.tsx`: eslint-disable img 추가
- `frontend/app/result/[id]/page.tsx`: eslint-disable img 추가

## 3) 테스트/검증

### 3.1 빌드 테스트

```bash
npx tsc --noEmit  # TSC_EXIT:0
npx next lint     # No ESLint warnings or errors (LINT_EXIT:0)
```

### 3.2 주요 검증 항목
- PokemonCard `onError` fallback: imgError state로 포켓볼 placeholder 전환
- useVeoPolling 중복 실행 방지: `mountedRef.current` + `inFlightRef.current`
- Modal backdrop 닫기: backdrop div에 직접 onClick 연결 확인
- SSR 안전성: AuthStorage 전 메서드 window 가드 확인
- TypeScript 전체 통과: TSC_EXIT:0

### 3.3 미검증 항목
- 실서버 연동 (USE_MOCK_AI 환경 미기동)
- 포켓몬 스프라이트 로딩 실패 시 fallback 시각 확인
- canvas-confetti 브라우저 렌더링 확인
- 퍼레이드 스프라이트 시트 실제 이미지 배치 (사용자 수동 설치 필요)

## 4) 이슈/리스크

| 항목 | 내용 | 대응 |
|------|------|------|
| 스프라이트 시트 미설치 | `/images/pokemon-sprite.png` 없으면 퍼레이드 빈 공간 | 사용자가 `frontend/public/images/`에 수동 저장 필요 |
| Auth API 404 위험 | login/signup 미구현 상태에서 `/auth/*` 호출 불가 | B-2 완료 전 login/signup 페이지 미접근, 주석 명시 |
| result 배경 임시색 | `#68A090` 고정값 사용 | F3에서 matched_pokemon 타입 기반 교체 |
| AuthGate 후 액션 자동 재실행 | 로그인 완료 후 `actionPending`으로 복귀 미구현 | F2-E (login) 구현 시 `?next=` 파라미터로 처리 예정 |

## 5) 다음 Stage 인수인계

- 다음 작업:
  1. **B-2**: Auth 백엔드 (POST /auth/register, /login, GET /auth/me + users 테이블 migration)
  2. **F2-E**: `/login`, `/signup` 페이지 (데스크톱 포켓몬 눈 애니메이션, 모바일 팔레트 타운)
- 주의할 점:
  - 스프라이트 시트: `https://assets.codepen.io/13471/pokemon-sprite.png` 다운로드 → `frontend/public/images/pokemon-sprite.png`
  - B-2 완료 전 AuthStorage.isLoggedIn()은 항상 false 반환 → 광장/저장 버튼 클릭 시 AuthGateModal 표시됨

## 6) AI 활용 기록

- 사용한 AI: Claude Sonnet 4.6 (Claude Code)
- 역할: 전체 코드 작성 (F2-A~D)
- 사람이 결정한 것: Auth 포함 여부 (Option B), 애니메이션 방식 (Tailwind), 스프라이트 로컬 저장

## 7) 완료 체크

- [x] tailwind.config.ts 11개 keyframe/animation 추가
- [x] lib/constants.ts, types.ts, storage.ts, api.ts — auth 타입/함수 추가
- [x] ProgressBar.tsx, Modal.tsx 신규 생성
- [x] PokemonCard.tsx 신규 생성 (davidkpiano 디자인)
- [x] /match 페이지 완성 (선택 → 생성 → generate 이동)
- [x] useVeoPolling.ts 신규 생성
- [x] /generate/[id] 풀스크린 + 퍼레이드 구현
- [x] InlineEditableName.tsx, AuthGateModal.tsx 신규 생성
- [x] /result/[id] 완성 (confetti, 이름편집, 공유/광장/저장 버튼)
- [x] 코드 리뷰 피드백 반영 (Modal, AuthStorage, plaza lint)
- [x] TypeScript 빌드 테스트 통과 (exit 0)
- [x] 개발일지 업데이트
- [ ] 스프라이트 시트 수동 설치 (사용자 액션 필요)
- [ ] B-2 백엔드 구현 (Auth 엔드포인트)
- [ ] F2-E 로그인/가입 페이지
- [ ] PM/리드 리뷰 완료
