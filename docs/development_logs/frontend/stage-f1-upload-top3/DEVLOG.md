# Stage 개발일지

## 0) 기본 정보
- 파트: `frontend`
- Stage: `f1-upload-top3`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 이미지 업로드 → `/api/v1/match` 호출 → Top-3 포켓몬 카드 렌더링 → 선택 상태 관리
  - Backend Mock/Real API 연동 가능한 API 클라이언트 완성
- 이번 Stage에서 포함한 범위:
  - `frontend/app/page.tsx` — 업로드 + Top-3 선택 UX (step: "upload", "select")
  - `frontend/lib/api.ts` — API 클라이언트
  - `frontend/lib/types.ts` — TypeScript 인터페이스
  - `frontend/app/layout.tsx`, `tailwind.config.ts`, `package.json`

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **Step 상태 머신**: `type Step = "upload" | "select" | "generating" | "result"`
- 결정 2: **`lib/api.ts` 단일 게이트웨이** — ApiError + Envelope 파싱 일원화
- 결정 3: **프론트 사전 검증** — MIME 타입 + 10MB 크기 제한 (서버 호출 전 거부)
- 결정 4: **`URL.createObjectURL` 로컬 미리보기** + cleanup

### 2.2 핵심 로직 설명
- `handleMatch()`: matchFace(imageFile) → MatchResponse → setMatchResult
- 에러 분기: FACE_NOT_DETECTED, MULTIPLE_FACES, LOW_QUALITY → 각각 다른 메시지
- Top-3 카드: 포켓몬 이름, 스프라이트, 유사도(%), 근거 문장 3개
- `lib/api.ts`: `request<T>()` 공통 함수, ApiError 클래스
- `matchFace(file)`: FormData `form.append("file", file)` → POST /match

### 2.3 변경 파일 목록
- `frontend/app/page.tsx` (518줄 — 업로드/선택 섹션)
- `frontend/lib/api.ts` (121줄), `frontend/lib/types.ts` (104줄)
- `frontend/app/layout.tsx`, `globals.css`, `tailwind.config.ts`, `package.json`

## 3) 테스트/검증
- `npm run lint` — next: command not found (node_modules 미설치)
- `lib/types.ts` ↔ 백엔드 `core/schemas.py` 필드 매칭 수동 확인

## 4) 이슈/리스크
- `page.tsx` 518줄 단일 컴포넌트 (15개+ useState) — 컴포넌트 분리 필요
- React Error Boundary 없음
- `skipLibCheck: true` (tsconfig) — 라이브러리 타입 오류 숨김

## 5) 다음 Stage 인수인계 (F2)
- 포켓몬 선택 후 생성 플로우로 전환 (`setStep("generating")`)
- `createCreature()`, `generateCreature()` API 연동
- Veo 폴링 로직 구현

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: 컴포넌트 비대화 리스크, Error Boundary 미구현 명시

## 7) 완료 체크
- [x] 이미지 업로드 + 사전 검증 완료
- [x] POST /match API 연동 완료
- [x] Top-3 카드 렌더링 + 선택 상태 관리 완료
- [x] API 클라이언트 + 에러 파싱 완료
- [x] TypeScript 인터페이스 완전 정의 완료
- [ ] 단위 테스트 없음
- [x] 개발일지 파일 생성: `docs/development_logs/frontend/stage-f1-upload-top3/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
