# 페이지 설계: `/login` — 로그인

- 라우트: `/login`
- 상태: 설계 확정 (미구현)

---

## 역할

신규/기존 사용자 진입점. 인증 후 `?next=` 파라미터 경로 또는 `/upload`로 이동.

---

## 데스크톱/태블릿 레이아웃 (Instagram 로그인 구조)

좌우 50/50 분할.

### 좌측 — 브랜딩 패널

- Pocketman 로고 (PocketmanLogo 컴포넌트)
- 포켓몬 크리처 콜라주: 피카츄/파이리/뮤츠 카드 3장 부채꼴 배치
  - 각도: -8deg, +5deg, -3deg
  - 각 포켓몬 눈 애니메이션 적용 (개별 delay)
- 배경: beige → coral/teal 오로라 그라데이션

### 우측 — 로그인 폼

- 소셜 로그인 우선 노출 (Google → Kakao 순)
- 이메일/비밀번호 폼
- 비밀번호 찾기 / 회원가입 링크
- 배경: 흰색, 수직 중앙 정렬

---

## 모바일 레이아웃 (Dribbble 레퍼런스)

레퍼런스: https://dribbble.com/shots/6670990-Login-screen-animated-illustration (Anas Tradi)

### 상단 55% — 팔레트 타운 일러스트 애니메이션

배경 색상: `#2DA2A0` → `#009087` (틸 계열)

구성 요소:
- Professor Oak 연구소 (우측 중앙)
- 주인공 집 (좌측)
- 나무 + 도로 + 풀숲
- 피카츄 (연구소 앞)

애니메이션:
| 요소 | 종류 | 주기 |
|------|------|------|
| 구름 | 좌→우 이동 | 8s |
| Pidgey | 비행 패스 | 6s |
| 피카츄 꼬리 | 흔들림 | 0.5s |
| 풀숲 | 흔들림 | 2s |

색상 팔레트:
- 하늘: `#2DA2A0`
- 나무: `#1B584E`, `#4A992D`
- 지붕: `#C8A43E`

### 하단 45% — 로그인 폼

- 흰 카드 슬라이드업 애니메이션
- 소셜 로그인 버튼 (Google, Kakao)
- 이메일/비밀번호 폼

---

## 눈 애니메이션 CSS

```css
@keyframes eyes-look {
  0%, 45%  { transform: translateX(0); }
  50%, 65% { transform: translateX(2px); }
  70%, 85% { transform: translateX(-2px); }
  90%, 100%{ transform: translateX(0); }
}

@keyframes eye-blink {
  0%, 96%  { transform: scaleY(1); }
  97%, 99% { transform: scaleY(0.1); }
  100%     { transform: scaleY(1); }
}
```

각 포켓몬별 delay: 피카츄 0s / 파이리 1.5s / 뮤츠 3s

---

## 인증 기술 스택

- **NextAuth.js (Auth.js v5)**
- `session: { strategy: "jwt" }`
- Provider: Google, Kakao, Credentials(이메일)
- Access Token: 15분 / Refresh Token: 7일 (httpOnly cookie)
- Route 보호: `middleware.ts`

---

## 리다이렉트 정책

- 로그인 성공 → `?next=` 파라미터 경로 우선, 없으면 `/upload`
- 이미 로그인 상태로 접근 → `/upload` 리다이렉트
