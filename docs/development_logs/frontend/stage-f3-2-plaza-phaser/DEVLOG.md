# Stage 개발일지

## 0) 기본 정보
- 파트: `frontend`
- Stage: `f3-2-plaza-phaser`
- 작성자: `Claude (PM + Tech Lead)`
- 작성일: `2026-03-13`
- 관련 이슈/PR: `N/A`

## 1) Stage 목표/범위
- 목표: `/plaza` 페이지를 Phaser.js 기반 2D 탑뷰 맵으로 교체 (단독 플레이어)
- 포함 범위:
  - `frontend/app/plaza/page.tsx` 전체 교체 (기존 피드 카드 → Phaser 맵)
  - `frontend/components/features/plaza/PhaserPlaza.tsx` 신규
  - Phaser.js 3 패키지 설치
  - BGM 토글 (HTML Audio, localStorage 저장)
  - 모바일 D-pad
  - 크리처 없는 유저 → `/upload` 리다이렉트
- 제외 범위:
  - F3-3: Socket.io 멀티플레이어 (다음 Stage)
  - 실제 BGM 오디오 파일 (서버 에셋 필요, `/public/bgm/plaza.mp3` 위치 예약)

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: Phaser.js dynamic import (SSR 방지)**
- Phaser는 `window`/`document`에 직접 의존 → Next.js SSR에서 실행 불가
- `dynamic(() => import(...), { ssr: false })`로 클라이언트 전용 로드
- `useEffect` 내에서도 `await import("phaser")`로 지연 로드

**결정 2: 플레이어 스프라이트 — 크리처 이미지 동적 로드**
- `playerCreature.image_url` → Phaser `this.load.image()` 로 런타임 로드
- 이미지 없거나 로드 실패 시: 보라색 원(폴백) 표시
- 원형 마스크: `createGeometryMask()` 적용

**결정 3: 크리처 없는 유저 → /upload 리다이렉트**
- 비로그인 또는 `getMyCreatures().items.length === 0` → `/upload`로 이동
- 기획서 Q2 답변: 관전 모드 없이 업로드 페이지로 바로 이동

**결정 4: D-pad ↔ Phaser 통신 방식**
- React ref(`dpadRef.current`)에 방향 상태 저장
- Phaser Scene의 `update()` 클로저에서 `dpad.current`를 직접 읽음
- 이벤트 전달 없이 매 프레임 폴링 → 지연 없는 반응

**결정 5: BGM**
- HTML `<audio>` 엘리먼트 + `useRef` 관리
- `localStorage("plaza_bgm")` 로 설정 영속
- 기본값: OFF (브라우저 자동재생 정책 준수)
- 실제 BGM 파일: `/public/bgm/plaza.mp3` 위치 예약, 파일 없으면 자동 무시

**결정 6: 분수 충돌 (AABB)**
- Physics 엔진 없이 수동 AABB 충돌 감지
- 대각 진입 시 수평/수직 분리 시도 (미끄러지듯 이동)
- Phaser.Scale.RESIZE로 창 크기 변화 대응

### 2.2 월드 구성

```
1024×1024 픽셀 월드 (32px 타일 그리드)

바닥: 체크무늬 (베이지 #f6f2e8 / 연한 틸 #d4edea)
중앙: 분수 (x:400~624, y:400~624) — 이동 불가
장식: 나무 12그루 — 3겹 원형 잎 픽셀아트
카메라: 플레이어 추적 (부드러운 lerp 0.08)
```

### 2.3 상태 전이

```
checking (입장 확인 중)
  ↓ 비로그인 또는 크리처 없음 → /upload
  ↓ 크리처 있음
ready (Phaser 맵 렌더링)
  ↓ 나가기 버튼
/ (메인)
```

### 2.4 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `frontend/app/plaza/page.tsx` | 전체 교체 | 피드 카드 → Phaser 맵 셸 |
| `frontend/components/features/plaza/PhaserPlaza.tsx` | 신규 | Phaser 게임 + React HUD |
| `frontend/package.json` | 의존성 추가 | `phaser@3` |
| `frontend/public/bgm/plaza.mp3` | 위치 예약 | 실제 파일 없음, 자동 무시 |

## 3) 테스트/검증

### 3.1 빌드 결과
```
✅ npm run build: 14 pages, 오류 없음
✅ npm run lint: 신규 파일 오류/경고 없음
   ⚠️ 기존 경고 1건 이월: app/creatures/[id]/page.tsx:274 no-img-element (F3-1 범위, 본 Stage 변경 없음)
```

### 3.2 수동 검증 항목 (로컬 실행 기준)
- [ ] 비로그인 상태로 /plaza 접근 → /upload 리다이렉트
- [ ] 크리처 없는 계정 → /upload 리다이렉트
- [ ] 크리처 있는 계정 → Phaser 맵 렌더링
- [ ] WASD/방향키 이동
- [ ] 분수 충돌 (통과 불가)
- [ ] 나무 주변 이동
- [ ] 카메라 플레이어 추적
- [ ] 모바일 D-pad 이동
- [ ] BGM 토글 (🔇/🔊)
- [ ] "나가기" → 메인 이동
- [ ] 창 크기 변경 시 맵 자동 리사이즈

## 4) 이슈/리스크

| 항목 | 심각도 | 상태 | 비고 |
|------|--------|------|------|
| BGM 파일 없음 | Low | 🟡 예약 | `/public/bgm/plaza.mp3` 추가 필요 |
| 나무 충돌 미구현 | Low | 🟡 미완 | 현재 장식용만 — F3-3에서 추가 |
| Phaser 번들 크기 | Low | 🟡 모니터링 | ~1.5MB → dynamic import로 초기 로드 지연 |
| 크리처 이미지 CORS | Medium | 🟡 미검증 | Railway S3 CORS 설정 필요할 수 있음 |

## 5) 다음 Stage 인수인계

- **다음 Stage**: `f3-3-plaza-multiplayer` — Socket.io 멀티플레이어 구현
  - 백엔드: WebSocket 엔드포인트 (`/plaza` 네임스페이스)
  - 타 플레이어 스프라이트 렌더링
  - 공개 채팅 말풍선 (3초 fadeOut)
  - DM 요청/수락/거절/채팅창
- BGM 파일: 저작권 무료 8bit 픽셀 BGM `/public/bgm/plaza.mp3` 추가 필요

## 5-1) 코드 리뷰 후 수정 이력

| 리뷰 항목 | 심각도 | 수정 내용 |
|-----------|--------|----------|
| 스폰 위치가 분수 내부 (512,512) | High | (512, 180)으로 이동 — 분수 영역 완전 외부 |
| await import unmount race | High | `isMounted` 플래그 추가 — import 완료 후 unmount 여부 체크, 즉시 destroy |
| API 실패 시 진입 정책 우회 | Medium | catch → ready 제거, /upload 리다이렉트로 통일 |
| D-pad touchcancel 누락 | Medium | 4방향 모두 `onTouchCancel` 핸들러 추가 |
| "크리처 보기" 잘못된 경로 | Medium | 버튼 제거 (F3-3에서 맵 내 탐색으로 구현 예정) |

## 6) AI 활용 기록

- Claude Sonnet 4.6 활용
- Phaser.js Scene 클래스 구조 설계
- D-pad ↔ Phaser 통신 패턴 (ref 폴링)
- AABB 충돌 감지 로직 (수평/수직 분리)
