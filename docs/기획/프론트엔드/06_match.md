# 페이지 설계: `/match` — 매칭 결과

- 라우트: `/match`
- 상태: 설계 확정 (F2에서 구현 예정)

---

## 역할

얼굴 분석 결과 TOP-3 포켓몬 표시 → 하나 선택 → 크리처 생성 시작.

---

## 데이터 소스

- `sessionStorage` (`MatchResultStorage.load()`)
- sessionStorage 없으면 → `/upload` 리다이렉트

---

## 포켓몬 이미지

`https://www.serebii.net/pokemongo/pokemon/{id}.png` (Pokemon GO 3D 아트, 1세대~3세대)

---

## 카드 디자인

레퍼런스: davidkpiano CodePen `NreaMB` (Eevee Pokedex Card)

```
배경: 포켓몬 타입별 색상 + 다이아몬드 패턴
     repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(0,0,0,0.1) 4px, rgba(0,0,0,0.1) 5px)

좌측 패널:
  - Pokemon GO 3D 아트 이미지
  - 라디얼 글로우 효과
  - head 바운스 애니메이션 (무한 반복)

우측 패널 (Lato 폰트):
  - ◉ #{번호}  {이름} (자간 넓게, letter-spacing: 0.2em)
  - Type: {타입 배지}
  - 유사도: {score}%
  - {포켓몬 카테고리명} (예: "전기 생쥐 포켓몬")
  - {PokeAPI 설명 텍스트}
  - 유사도 프로그레스바 (타입 색상)
  - [이 포켓몬으로 시작하기] 버튼
```

---

## 타입별 배경 색상

| 타입 | 색상 |
|------|------|
| 불꽃 | `#c97c4a` |
| 물 | `#5b8fc9` |
| 전기 | `#c9a93b` |
| 풀 | `#6aab4f` |
| 에스퍼 | `#9b8ec4` |
| 노말 | `#a0a0a0` |
| 독 | `#9b5fc9` |
| 얼음 | `#7ac9c9` |
| 격투 | `#c94a4a` |
| 비행 | `#7a9bc9` |
| 땅 | `#c9a96e` |
| 바위 | `#8a7f5c` |
| 벌레 | `#7aab4f` |
| 고스트 | `#5c4a7a` |
| 드래곤 | `#5c7ac9` |
| 강철 | `#8a9bab` |
| 악 | `#4a3a5c` |
| 페어리 | `#c97aab` |

---

## TOP-3 배치

- 가로 3열 카드 배치 (데스크톱)
- 모바일: 세로 스크롤
- **1위 카드**: 중앙 배치 + `scale(1.05)` + "BEST MATCH" 뱃지

---

## 선택 인터랙션

```
카드 [이 포켓몬으로 시작하기] 클릭
  → 선택 카드: scale-up 애니메이션
  → 나머지 카드: opacity → 0 (fade-out)
  → 0.6초 후: POST /creatures { pokemon_id } → { creature_id }
  → router.push(`/generate/${creature_id}`)
```

---

## API 연동

- `POST /creatures` → `{ pokemon_id: number }` → `{ id: string, status: "pending" }`
