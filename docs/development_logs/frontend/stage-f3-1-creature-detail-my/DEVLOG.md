# Stage 개발일지

## 0) 기본 정보
- 파트: `frontend`
- Stage: `f3-1-creature-detail-my`
- 작성자: `Claude (PM + Tech Lead)`
- 작성일: `2026-03-13`
- 관련 이슈/PR: `N/A`

## 1) Stage 목표/범위
- 목표:
  - `/creatures/[id]` — 크리처 상세 페이지 (소셜 기능 포함)
  - `/my` — 마이페이지 (내 크리처 / 좋아요 탭, 프로필, 설정)
  - `/my/edit` — 프로필 편집 (닉네임 중복 실시간 확인, 계정 삭제)
  - `/my/password` — 비밀번호 변경 (강도 측정기 포함)
- 포함 범위:
  - `app/creatures/[id]/page.tsx` 전체 재작성
  - `app/my/page.tsx` 신규
  - `app/my/edit/page.tsx` 신규
  - `app/my/password/page.tsx` 신규
- 제외 범위:
  - "광장에서 찾기" (F3-3 WebSocket 때 활성화)
  - 아바타 크리처 선택 UI (추후 구현)

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: `creatures/[id]` — owner vs non-owner 분기**
- `isOwner`: `creature.owner?.id === authUser?.id && creature.owner != null`
- owner: [이름 인라인 편집, 공개/비공개 토글, 링크복사, 삭제]
- non-owner: [좋아요 토글 + 카운트, 링크복사, 광장에서찾기(비활성)]
- 소유자 없는 크리처(anonymous): isOwner=false → non-owner UI 표시

**결정 2: "광장에서 찾기" 비활성 처리**
- F3-3 WebSocket 구현 전까지 `disabled` + `title` 속성으로 설명
- 버튼 자체는 렌더링하여 UI 완성도 유지

**결정 3: 댓글 섹션 auth gate**
- 비로그인 → 댓글 입력 클릭 시 로그인 필요 모달 표시
- 모달에서 `/login` 으로 이동 옵션 제공

**결정 4: 마이페이지 탭 구조**
- "내 크리처" / "좋아요한 크리처" 두 탭
- "좋아요" 탭은 첫 진입 시에만 API 호출 (lazy load)
- 내 크리처 카드: hover 시 "삭제" 버튼 노출, 2단계 확인 (확인/취소 버튼)

**결정 5: 닉네임 실시간 중복 확인**
- 500ms debounce 후 `checkNickname()` API 호출
- 현재 닉네임과 동일하면 API 호출 스킵 (불필요한 요청 방지)

**결정 6: 비밀번호 강도 측정**
- 길이(8/12자), 대문자, 숫자, 특수문자 5개 항목 점수 합산
- weak(≤2) / fair(≤3) / strong(≥4) → 색상 바로 시각화
- strong 미만이면 변경 버튼 비활성

### 2.2 핵심 로직 설명

**`/creatures/[id]` 로딩 흐름:**
1. `getCreatureDetail(id)` — optional auth (is_liked 포함)
2. `status: "loading" → "ready" | "notFound"` 상태 전환
3. 비공개 크리처 + 비소유자 → 404 반환됨 (서버에서 처리)

**좋아요 최적화 업데이트:**
```
setCreature(prev => prev && { ...prev, is_liked: !prev.is_liked,
  like_count: prev.like_count + (prev.is_liked ? -1 : 1) })
```
→ 서버 응답 전에 UI 선반영, 실패 시 롤백

**프로필 편집 저장 로직:**
- 변경된 필드만 `payload`에 포함 (닉네임, bio 각각 비교)
- 변경사항 없으면 API 호출 없이 "변경 사항이 없습니다." 토스트

**비밀번호 변경 후 처리:**
- 성공 시 1.8초 후 `AuthStorage.clear()` → `/login` 리다이렉트
- 변경된 토큰 무효화를 위해 강제 재로그인 유도

### 2.3 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `app/creatures/[id]/page.tsx` | 재작성 | 크리처 상세 페이지 전체 |
| `app/my/page.tsx` | 신규 | 마이페이지 메인 |
| `app/my/edit/page.tsx` | 신규 | 프로필 편집 |
| `app/my/password/page.tsx` | 신규 | 비밀번호 변경 |
| `components/ui/Badge.tsx` | 수정 없음 | `TypeBadge` 올바른 이름으로 참조 수정 |

## 3) 버그/이슈 기록

### 3.1 Badge import 오류
- **현상**: `Badge` named export 없음 — `TypeBadge` 사용해야 함
- **원인**: 이전 작업에서 Badge.tsx 실제 export 이름 확인 누락
- **해결**: `creatures/[id]/page.tsx` import를 `TypeBadge`로 수정

### 3.2 InlineEditableName prop 이름 오류
- **현상**: `onSave` prop 없음 — `onSaved` 사용해야 함
- **원인**: prop 이름 확인 누락
- **해결**: `onSave` → `onSaved` 수정

### 3.3 Toast className prop 없음
- **현상**: `Toast` 컴포넌트에 `className` prop 미지원
- **해결**: `<div className="..."><Toast .../></div>` 래퍼로 우회

## 4) 빌드 결과

```
✓ 프론트엔드 빌드 성공 (warnings only — img 태그 LCP 경고)
✓ 백엔드 컴파일 성공 (BACKEND OK)
```

## 5) 다음 단계

- DB 마이그레이션 실행 (002 ~ 005) — 운영자 액션 필요
- F3-2: Phaser.js 맵 + 단독 플레이어 이동 구현
- F3-3: Socket.io 멀티플레이어
