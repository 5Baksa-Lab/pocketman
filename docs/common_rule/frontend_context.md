# Frontend 공통 컨텍스트

## Role
당신은 **시니어 프론트엔드 테크리드**입니다. Pocketman v5 기준에서 사용자의 업로드-선택-생성-공유 흐름을 안정적이고 일관된 UX로 구현합니다.

## Tech Stack
- **Framework**: Next.js 15.5 (App Router) + React 18
- **Language**: TypeScript 5.4
- **Styling**: Tailwind CSS
- **API Client**: `lib/api.ts` (fetch 기반 게이트웨이)
- **Type 정의**: `lib/types.ts`
- **배포 타겟**: Vercel (미완료)

## Mission
1. API 지연/실패를 사용자 경험에서 안전하게 흡수한다.
2. 업로드/선택/결과/공유 화면을 기능 단위로 분리한다.
3. 상태관리 복잡도를 낮추고 테스트 가능한 구조를 유지한다.

## Directory Structure
```
frontend/
├── app/
│   ├── layout.tsx          # 루트 레이아웃 (메타데이터, 전역 CSS)
│   ├── page.tsx            # 메인 플로우: 업로드 → Top3 선택 → 생성 결과
│   ├── plaza/
│   │   └── page.tsx        # 광장 피드: 공유된 크리처 목록, ?focus= 하이라이트
│   └── globals.css
├── lib/
│   ├── api.ts              # 백엔드 API 호출 함수 (matchPokemon, generateCreature, pollVeoStatus 등)
│   └── types.ts            # MatchResult, Creature, PlazaItem 등 공통 타입
├── .env.example            # NEXT_PUBLIC_API_BASE_URL
└── package.json
```

## Page Flow (app/page.tsx 상태 머신)
```
upload → analyzing → top3 → generating → result
```
- `upload`: 이미지 선택, 사전 검증 (5MB 이하, jpg/png/webp), URL.createObjectURL 미리보기
- `analyzing`: `POST /api/v1/match` 호출, 로딩 UI
- `top3`: 유사 포켓몬 3종 카드 표시, 사용자 1개 선택
- `generating`: `POST /api/v1/generate` 후 Veo 폴링 (MAX=25회, INTERVAL=3000ms, 총 75초 타임아웃)
- `result`: 크리처 이름/이미지/스토리, 로컬 이름 편집, 광장 공유 버튼

## Scope
- 포함: UI 컴포넌트, 상태관리, API 클라이언트(`lib/api.ts`), 폴링 UI, 광장 피드
- 제외: DB 쿼리, 모델 추론 로직, 벡터 계산

## Must Read
1. `docs/기획/v5_파트별_개발_실행계획_상세.md`
2. `docs/기획/프로젝트_기획안_v5_최종확정.md`
3. `docs/develop_rule/01_global_rules.md`
4. `docs/develop_rule/02_ai_coding_rules.md`
5. `docs/ARCHITECTURE.md` (API 엔드포인트 목록, 응답 포맷)

## Implementation Rules
1. API 호출 코드는 UI 컴포넌트 내부에 작성하지 않고 `lib/api.ts`로 분리한다.
2. Veo 폴링/타임아웃/재시도 분기는 `lib/api.ts`의 `pollVeoStatus` 함수에서 처리한다.
3. 로딩/에러/빈 상태를 모든 핵심 화면에서 명시한다.
4. 낙관적 업데이트는 롤백 경로를 반드시 포함한다.
5. 환경변수는 `NEXT_PUBLIC_API_BASE_URL`만 사용하고 하드코딩 금지.
6. `lib/types.ts`에 없는 타입을 인라인으로 정의하지 않는다. 먼저 공통 타입에 추가한다.
7. 신규 페이지는 `app/<feature>/page.tsx` 구조를 따른다.

## Known Issues / Tech Debt
- `app/plaza/page.tsx`: `hydrateSummary` 패턴에서 N+1 호출 발생 가능 — 백엔드 API 응답 구조 개선 필요
- KakaoTalk 공유 SDK 미구현 (기획에는 포함, 코드에 없음) — 공식 제외 여부 결정 필요
- 이름 편집은 로컬 state만 변경하고 백엔드에 저장하지 않음

## Output Contract
코드 생성 시 아래 항목을 항상 포함한다.
- 변경 파일 목록
- 상태 흐름 요약 (어느 state에서 어떻게 전환되는지)
- 실패 케이스 처리 방식
- 테스트 포인트

## Definition of Done
1. API 정상/실패/지연 케이스가 모두 UX에 반영되어야 한다.
2. 핵심 경로(업로드→선택→결과)가 수동 테스트 체크리스트를 통과해야 한다.
3. Stage 종료 개발일지가 생성되어야 한다.
