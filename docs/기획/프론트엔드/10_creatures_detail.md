# 페이지 설계: `/creatures/[id]` — 크리처 상세

- 라우트: `/creatures/[id]`
- 상태: 설계 확정 (F3에서 구현 예정)

---

## 역할

광장 / 링크 / 공유 등에서 진입하는 공개 크리처 상세 페이지. SNS 게시물 상세 역할.

---

## 레이아웃

- davidkpiano 카드 디자인 (match / result 페이지와 동일 구조)
- 카드 하단: 댓글 섹션

---

## 카드 좌측

- 크리처 영상/이미지
- **클릭 시 재생** (자동재생 없음)
- 재생 중: video 태그 전체 표시

---

## 카드 우측 정보

```
◉ #{번호}  {크리처 이름}
Type: {타입 배지들}
by @{username}
{생성 날짜}

닮은 포켓몬: {포켓몬명} {유사도}%
{크리처 설명}

[버튼 - 내/타인 분기]
```

---

## 버튼 분기

| 상황 | 버튼 |
|------|------|
| 내 크리처 | [이름 편집] [공개/비공개 전환] [삭제] [공유] |
| 타인 크리처 | [❤️ 좋아요] [📤 공유] [광장에서 찾기] |

---

## 광장에서 찾기 버튼

| 소유자 상태 | 버튼 상태 |
|------------|----------|
| 광장 접속 중 | 활성화 → 클릭 시 `/plaza` + 해당 크리처 위치 포커스 |
| 오프라인 | 비활성화 (회색, cursor: not-allowed) |

소유자 온라인 여부: socket.io 연결 상태 실시간 확인 (또는 주기적 폴링).

---

## 댓글 섹션

- 정렬: 최신순
- 최대 글자 수: 100자
- 본인 댓글만 삭제 가능 (우클릭 또는 ... 메뉴)
- 비로그인: 댓글 입력창 탭 시 로그인 유도 모달

---

## 공개/비공개 전환 (내 크리처)

- 공개 🌍 / 비공개 🔒 토글
- `PATCH /creatures/{id}` → `{ is_public: boolean }`
- 비공개 시 타인 접근 → 404

---

## API 연동

- `GET /creatures/{id}` → 크리처 상세 + 소유자 정보 + 온라인 여부
- `POST /creatures/{id}/comments` → `{ content: string }`
- `DELETE /creatures/{id}/comments/{comment_id}`
- `POST /creatures/{id}/like`
- `DELETE /creatures/{id}/like`
- `PATCH /creatures/{id}` → `{ name?, is_public? }`
- `DELETE /creatures/{id}`
