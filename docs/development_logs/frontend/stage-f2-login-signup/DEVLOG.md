# Stage 개발일지

## 0) 기본 정보
- 파트: `frontend`
- Stage: `f2-login-signup`
- 작성자: `sups`
- 작성일: `2026-03-13`
- 관련 이슈/PR: N/A

## 1) Stage 목표/범위
- 목표: 이메일 로그인/가입 페이지 구현 + AuthGate 실 동작 연결
- 포함 범위:
  - `app/login/page.tsx` — 로그인 페이지 (Desktop 50/50 / Mobile 팔레트 타운)
  - `app/signup/page.tsx` — 가입 페이지 (비밀번호 강도 인디케이터)
  - `components/features/auth/PaletteTownScene.tsx` — CSS 팔레트 타운 일러스트 (모바일)
  - `components/features/auth/PokemonBrandPanel.tsx` — 포켓몬 3장 브랜딩 패널 (데스크톱)
  - `components/features/result/AuthGateModal.tsx` — "준비 중" 제거, 실 /login 이동
- 제외 범위:
  - 소셜 로그인 (F3)
  - 비밀번호 찾기 (F3)
  - 이메일 인증 (F3)

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: useSearchParams() → Suspense 래핑**
- Next.js 15 App Router 빌드 오류: useSearchParams는 Suspense 경계 필요
- 패턴: `export default function Page() { return <Suspense><Content /></Suspense> }`
- login, signup 양쪽 적용

**결정 2: 팔레트 타운 순수 CSS 구현 (이미지 파일 없음)**
- SVG/CSS div 조합으로 구름, 나무, 건물, 피카츄, Pidgey 구성
- 추가 이미지 파일 불필요 → 번들 영향 없음
- 기존 tailwind.config.ts `cloud-move`, `pidgey-fly`, `pikachu-tail` 애니메이션 재사용

**결정 3: 포켓몬 스프라이트 로컬 파일 참조**
- `/images/login-pikachu.png`, `/images/login-charmander.png`, `/images/login-mewtwo.png`
- 사용자가 `frontend/public/images/`에 수동 저장 필요
- serebii 출처: `https://www.serebii.net/pokemongo/pokemon/{번호}.png`

**결정 4: 이메일 중복(409) → 인라인 Toast 에러**
- `ApiError.code === "EMAIL_ALREADY_EXISTS"` 판별 후 "이미 사용 중인 이메일, 로그인해주세요" 안내
- 폼 UX 방해 없이 인라인 표시
- 주의: `err.message`가 아닌 `err.code` 필드로 판별 (ApiError 설계)

**결정 6: `?next=` 오픈 리다이렉트 방지 → getSafeNextPath()**
- `lib/utils.ts`에 `getSafeNextPath()` 함수 추가
- `/`로 시작하되 `//`로 시작하지 않는 내부 경로만 허용 (protocol-relative URL 차단)
- login, signup 양쪽 적용

**결정 5: 로그인 상태 접근 시 /upload 즉시 이동**
- `useEffect` 내 `AuthStorage.isLoggedIn()` 체크 → `router.replace("/upload")`

### 2.2 핵심 로직 설명

**login flow:**
1. 폼 submit → `login({ email, password })` API 호출
2. 성공 → `AuthStorage.saveToken()` + `AuthStorage.saveUser()` 저장
3. `?next=` 파라미터 우선, 없으면 `/upload` 이동

**signup flow:**
1. 비밀번호 강도 실시간 계산 (약/보통/강)
2. 비밀번호 확인 불일치 시 submit 비활성화
3. `register({ nickname, email, password })` 호출
4. 성공 → 자동 로그인 (서버가 토큰 반환) → `/upload` 또는 `?next=` 이동
5. 409 → 이메일 중복 안내 Toast

### 2.3 변경/신규 파일 목록

- `frontend/app/login/page.tsx`: 신규
- `frontend/app/signup/page.tsx`: 신규
- `frontend/components/features/auth/PaletteTownScene.tsx`: 신규
- `frontend/components/features/auth/PokemonBrandPanel.tsx`: 신규
- `frontend/components/features/result/AuthGateModal.tsx`: "준비 중" 제거, 실 동작 복원
- `frontend/lib/utils.ts`: 신규 (`getSafeNextPath()` — 오픈 리다이렉트 방지)

## 3) 테스트/검증

### 3.1 빌드 테스트

```bash
npm run build
# ✓ Compiled successfully
# /login ○ (Static), /signup ○ (Static)
# BUILD_EXIT:0

npx next lint
# ✔ No ESLint warnings or errors
```

### 3.2 미검증 항목
- 실서버 회원가입/로그인 end-to-end (B-2 백엔드 연동)
- 포켓몬 스프라이트 로컬 파일 시각 확인 (사용자 수동 설치 필요)
- 팔레트 타운 CSS 애니메이션 모바일 브라우저 확인

## 4) 이슈/리스크

| 항목 | 내용 | 대응 |
|------|------|------|
| 포켓몬 스프라이트 미설치 | 데스크톱 브랜딩 패널 이미지 깨짐 | 사용자 수동 설치 (공지) |
| `?next=` 오픈 리다이렉트 | URL 파라미터 조작으로 임의 경로 이동 가능 | `getSafeNextPath()` 내부 경로 검증으로 해결 (완료) |
| 로그인 상태 새로고침 | sessionStorage 기반 — 탭 닫으면 초기화 | 설계 의도 (24h 세션) |

## 5) 다음 Stage 인수인계

- F2 전체 완료 → F3 착수 가능
- F3 우선 작업: `/creatures/[id]` 공개 상세 페이지, 광장 크리처 카드 개선
- 포켓몬 스프라이트 설치 안내:
  - `frontend/public/images/login-pikachu.png` ← serebii #025
  - `frontend/public/images/login-charmander.png` ← serebii #004
  - `frontend/public/images/login-mewtwo.png` ← serebii #150

## 6) AI 활용 기록

- 사용한 AI: Claude Sonnet 4.6 (Claude Code)
- 역할: 전체 코드 작성 (F2-E)
- 사람이 결정한 것: 로그인 기본 이동 경로(/upload), 스프라이트 로컬 저장

## 7) 완료 체크

- [x] app/login/page.tsx 신규 (Desktop 50/50 / Mobile 팔레트 타운)
- [x] app/signup/page.tsx 신규 (비밀번호 강도 인디케이터)
- [x] PaletteTownScene.tsx 신규 (CSS 일러스트, 애니메이션 3종)
- [x] PokemonBrandPanel.tsx 신규 (포켓몬 3장 부채꼴)
- [x] AuthGateModal.tsx — 실 /login?next= 동작 복원
- [x] useSearchParams Suspense 래핑 (Next.js 15 빌드 오류 수정)
- [x] npm run build 통과
- [x] ESLint 경고 없음
- [x] 개발일지 작성
- [x] 포켓몬 스프라이트 수동 설치 완료
- [x] 코드 리뷰 지적 사항 반영 (ApiError.code 판별, getSafeNextPath 추가)
- [ ] PM/리드 리뷰 완료
