# 페이지 설계: `/generate/[id]` — 생성 대기

- 라우트: `/generate/[id]`
- 상태: 설계 확정 (F2에서 구현 예정)

---

## 역할

크리처 생성 중 대기 화면. 기다림을 흥미로운 경험으로 전환.

---

## 레이아웃

- 풀스크린 (Header 없음)
- 배경: `#1D1F20` (다크)

```
상단: Pocketman 로고 (opacity 0.8)
중앙: 생성 상태 텍스트 (흰색, opacity 0.5)
하단: 포켓몬 퍼레이드 애니메이션
```

---

## 포켓몬 퍼레이드 애니메이션

레퍼런스: simeydotme CodePen `ZGzrBQ`

스프라이트 소스: `https://assets.codepen.io/13471/pokemon-sprite.png`

원본 CodePen 주요 특징:
- `.pokonami` 컨테이너 (다크 배경)
- 각 포켓몬: `steps(1)` 2프레임 walk cycle
- `poke-move` keyframe: 오른쪽 끝에서 왼쪽 끝으로 이동

**원본 대비 변경사항**:
- `document.body.onclick` 트리거 제거 → `useEffect` 마운트 즉시 실행
- Pokemon 로고 이미지 → Pocketman 로고 컴포넌트로 교체
- "Click Anywhere to Begin" 텍스트 제거
- 배경 고정 (`#1D1F20`)

---

## 상태 텍스트 시퀀스

| 시간 | 텍스트 |
|------|--------|
| 0s~ | "나만의 크리처가 태어나고 있어요..." |
| 10s~ | "포켓몬의 특성을 융합하고 있어요..." |
| 25s~ | "거의 다 됐어요! 조금만 기다려주세요" |

---

## 폴링 로직 (`useVeoPolling`)

```
GET /creatures/{id}/status
  → { status: "pending" | "processing" | "done" | "failed" }

- 폴링 간격: 3초
- 최대 횟수: 25회 (75초)
- done → router.push(`/result/${id}`)
- failed → 에러 토스트 + "다시 시도하기" 버튼
- 타임아웃(25회 초과) → 에러 처리
```

퍼레이드 애니메이션과 폴링은 병렬 실행.

---

## API 연동

- `GET /creatures/{id}/status` → `{ status: string }`
