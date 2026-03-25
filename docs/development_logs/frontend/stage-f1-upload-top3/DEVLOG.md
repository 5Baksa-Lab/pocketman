# Stage 개발일지 — Frontend F1

## 0) 기본 정보
- 파트: `frontend`
- Stage: `f1-upload-top3` (라우팅 스캐폴딩 + 랜딩/인트로/업로드)
- 작성자: `sups`
- 작성일: `2026-03-11`
- 관련 이슈/PR: N/A

---

## 1) Stage 목표/범위

**목표**:
- 기존 단일 파일(`app/page.tsx`) step 구조를 독립 페이지로 분리
- UI 레퍼런스 분석(X/Threads/Instagram) 기반 레이아웃 컴포넌트 구현
- 전체 라우팅 스캐폴딩 완성
- `/upload` → `/match` 실제 백엔드 연결 검증

**포함 범위**:
- `app/` 전체 라우팅 구조 (7개 라우트 신규 생성)
- `components/layout/` — Header, Sidebar, MobileNav
- `components/ui/` — Button, Badge, Spinner, Toast
- `lib/constants.ts`, `lib/storage.ts` 신규 추가
- `app/layout.tsx`, `tailwind.config.ts` 업데이트
- `app/page.tsx` 완전 교체 (랜딩 페이지)
- `.eslintrc.json` 신규 생성

---

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: 페이지 단위 라우팅 전환**
- 기존 `page.tsx` 단일 파일에 `useState<Step>` 스위치 → 각 단계를 독립 URL 페이지로 분리
- 이유: URL이 상태(새로고침 복구), SEO, 딥링크 공유 가능

**결정 2: 레이아웃 컴포넌트 분리 전략**
- Root layout: Header(항상) + MobileNav(lg 미만 하단 고정)
- Sidebar: 별도 컴포넌트로 준비, F3 plaza 개선 시 layout에 통합
- UI 레퍼런스 기반: Instagram 220px 사이드바 패턴 → Sidebar.tsx, Threads/Instagram 하단 탭바 → MobileNav.tsx

**결정 3: 업로드 페이지 실 백엔드 연결**
- `matchFace(file)` → 실 API 호출
- 결과를 `MatchResultStorage.save()` → sessionStorage 저장
- `/match`로 router.push

**결정 4: Next.js 15 async params**
- `generate/[id]`, `result/[id]`, `creatures/[id]` — `params: Promise<{id: string}>` + `await params` 패턴 적용

### 2.2 파일별 역할

| 파일 | 역할 |
|------|------|
| `lib/constants.ts` | MAX_FILE_SIZE, ACCEPTED_MIME_TYPES 등 상수 |
| `lib/storage.ts` | sessionStorage MatchResultStorage 헬퍼 |
| `components/ui/Button` | primary/secondary/ghost variant + sm/md/lg size |
| `components/ui/Badge` | 포켓몬 타입별 색상 배지 (18개 타입) |
| `components/ui/Spinner` | 로딩 인디케이터 |
| `components/ui/Toast` | error/success/info 토스트 |
| `components/layout/Header` | 스티키 헤더, 광장 링크, 새 크리처 CTA |
| `components/layout/Sidebar` | lg+ 좌측 네비 (F3 활용 예정) |
| `components/layout/MobileNav` | 하단 탭바 3개 (홈/광장/만들기), lg 이상 hidden |
| `app/page.tsx` | 2컬럼 Hero + Features 3열 + 샘플 크리처 |
| `app/intro/page.tsx` | 3단계 시퀀스 애니메이션, 자동 전진, 스킵 버튼 |
| `app/upload/page.tsx` | 드래그앤드롭 + 검증 + 실 API 연결 |
| `app/match/page.tsx` | sessionStorage 수신 확인 (F2에서 완성) |

### 2.3 변경 파일 목록

**신규 생성 (16개)**:
- `lib/constants.ts`, `lib/storage.ts`
- `components/ui/Button.tsx`, `Badge.tsx`, `Spinner.tsx`, `Toast.tsx`
- `components/layout/Header.tsx`, `Sidebar.tsx`, `MobileNav.tsx`
- `app/intro/page.tsx`, `app/upload/page.tsx`, `app/match/page.tsx`
- `app/generate/[id]/page.tsx`, `app/result/[id]/page.tsx`, `app/creatures/[id]/page.tsx`
- `.eslintrc.json`

**수정 (3개)**:
- `app/layout.tsx` — Header + MobileNav 통합
- `app/page.tsx` — 전체 교체 (랜딩 페이지)
- `tailwind.config.ts` — `components/**` content 경로 추가

---

## 3) 테스트/검증

**빌드 테스트** (`npm run build`):
```
✓ Compiled successfully
✓ Generating static pages (8/8)

Route (app)                Size    First Load JS
○ /                       2.46 kB     108 kB
○ /intro                  1.16 kB     103 kB
○ /match                  1.09 kB     103 kB
○ /upload                 3.36 kB     105 kB
○ /plaza                  2.65 kB     105 kB
ƒ /generate/[id]           130 B      102 kB
ƒ /result/[id]             130 B      102 kB
ƒ /creatures/[id]          130 B      102 kB
```

**ESLint**:
```
0 errors, 1 warning
  경고: plaza/page.tsx useEffect dependency (기존 코드, F3에서 처리)
```

**USE_MOCK_AI**: 업로드 페이지 실 백엔드 연결 검증 가능
- `cd backend && USE_MOCK_AI=true ../.venv/bin/uvicorn app.main:app --port 8000`
- `GET /health` 200 → `/upload`에서 이미지 업로드 → `/match`로 이동 확인

---

## 4) 이슈/리스크/미해결

| 항목 | 내용 | 처리 예정 |
|------|------|-----------|
| Sidebar 미활성화 | 생성됐으나 layout에 미포함 | F3 plaza 개선 시 통합 |
| 랜딩 샘플 크리처 silent fail | API 오류 시 섹션 미표시 | skeleton loader 추가 가능 |
| plaza/page.tsx dependency warning | 기존 코드 | F3 리팩토링 시 처리 |
| BGM 토글 미구현 | F1 범위 외 | F3 Header에 추가 |

---

## 5) 다음 Stage 인수인계 (F2)

- `/match`: PokemonCard 컴포넌트 구현 + 선택 후 `createCreature` → `generateCreature` API 호출
- `/generate/[id]`: `useVeoPolling` 훅 + GenerateSteps 컴포넌트
- `/result/[id]`: CreatureProfile + NameEditor + ShareButtons
- 재사용 가능 컴포넌트: `components/ui/` 전체

---

## 6) AI 활용 기록

- 사용한 AI: Claude Sonnet 4.6 (Claude Code)
- 역할: 전체 코드 작성 (F1 스캐폴딩)
- 사람이 결정한 것: 완전 교체 승인, 실 백엔드 연결 방침, 브랜치 정책

---

## 7) 완료 체크

- [x] 전체 라우팅 구조 생성 (7개 라우트)
- [x] Header, Sidebar, MobileNav 컴포넌트
- [x] Button, Badge, Spinner, Toast UI 컴포넌트
- [x] lib/constants.ts, lib/storage.ts
- [x] 랜딩 페이지 (2컬럼 Hero + Features + 샘플)
- [x] 인트로 페이지 (3단계 시퀀스 애니메이션)
- [x] 업로드 페이지 (드래그앤드롭 + 검증 + 실 API 연결)
- [x] 빌드 테스트 통과 (8개 라우트 오류 없음)
- [x] ESLint 0 errors
- [x] DoD: `/` → `/intro` → `/upload` 전환 구조 완성
- [x] DoD: 업로드 후 sessionStorage 저장 + `/match` 이동 구조 완성
- [ ] PM/리드 리뷰 완료
