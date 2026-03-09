# Stage 개발일지

## 0) 기본 정보
- 파트: `frontend`
- Stage: `f3-share-feed`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 광장(Plaza) 공개 피드 페이지 + 이모지 리액션 UI
  - `?focus={creature_id}` 파라미터로 특정 크리처 하이라이트
- 이번 Stage에서 포함한 범위:
  - `frontend/app/plaza/page.tsx` 전체
  - `listPublicCreatures()`, `createReaction()`, `getReactionSummary()` API 연동
- 제외한 범위:
  - 카카오톡 SDK 연동 (미구현)
  - 무한스크롤 (LIMIT/OFFSET 방식)

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **`"use client"` 클라이언트 컴포넌트** (인터랙션 필요)
- 결정 2: **`hydrateSummary` 패턴** — 피드 로드 후 리액션 집계 지연 로드
- 결정 3: **focus 파라미터** → `scrollIntoView({ behavior: "smooth" })` + ring-2 하이라이트

### 2.2 핵심 로직 설명
- 피드 로드: `listPublicCreatures({ limit: 20, offset: 0 })`
- 리액션 집계 지연: `for...of items` → `getReactionSummary(id)` → `setReactionMap`
  - ⚠️ N+1 패턴: 크리처 20개 시 API 21회 호출
- 리액션 버튼: 6종 이모지, 낙관적 업데이트 후 createReaction() 호출
- focus: `useSearchParams().get("focus")` → `document.getElementById("creature-{id}").scrollIntoView()`

### 2.3 변경 파일 목록
- `frontend/app/plaza/page.tsx` (전체 신규)
- `frontend/lib/api.ts` (listPublicCreatures, createReaction, getReactionSummary 추가)
- `frontend/lib/types.ts` (CreatureListResponse, ReactionSummaryResponse 추가)
- `frontend/app/layout.tsx` (헤더에 /plaza 링크 추가)

## 3) 테스트/검증
- `useSearchParams()` Suspense 경계 필요 여부 확인 미완
- 낙관적 업데이트 실패 롤백 로직 검토 미완

## 4) 이슈/리스크
- **카카오톡 공유 미구현** (기획서 §9-1 필수 요구사항 미달 — 결정 필요)
- `hydrateSummary` N+1 API 호출 — 피드 규모 증가 시 병목
- `useSearchParams()` — Next.js 15에서 `<Suspense>` 래핑 필요 가능성
- 리액션 낙관적 업데이트 실패 시 롤백 없음

## 5) 다음 Stage 인수인계 (P3)
- 카카오톡 구현 여부 최종 결정 필요
- N+1 → `Promise.all` 병렬 호출 또는 Backend API 변경으로 개선
- E2E 시나리오 전체 흐름 검증

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: 카카오톡 미구현 리스크, Suspense 이슈 명시

## 7) 완료 체크
- [x] 광장 피드 페이지 구현 완료
- [x] 이모지 리액션 + 낙관적 업데이트 완료
- [x] focus 파라미터 하이라이트 완료
- [ ] 카카오톡 공유 미구현 (기획 요구사항 미달)
- [ ] hydrateSummary N+1 최적화 미완
- [x] 개발일지 파일 생성: `docs/development_logs/frontend/stage-f3-share-feed/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
