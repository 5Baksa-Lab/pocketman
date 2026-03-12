# 페이지 설계: `/plaza` — 광장

- 라우트: `/plaza`
- 상태: 설계 확정 (F3에서 구현 예정)

---

## 역할

포켓몬 Platinum Wi-Fi 광장 스타일 실시간 인터랙티브 소셜 공간.
자신이 만든 크리처로 광장을 돌아다니며 타 유저 크리처를 구경하고 채팅.

---

## 기술 스택

| 항목 | 선택 |
|------|------|
| 렌더링 | Phaser.js (타일맵 + 스프라이트 + 카메라 내장) |
| 실시간 | socket.io (WebSocket) |
| 맵 크기 | 32×32 타일, 타일 1개 = 32px (1024×1024 월드) |
| 아트 스타일 | 픽셀아트 탑뷰 |

---

## 맵 구성

| 요소 | 내용 |
|------|------|
| 바닥 | 체크무늬 타일 (베이지/연한 틸) |
| 중앙 | 분수 (랜드마크, 이동 불가) |
| 장식 | 나무/덤불 (이동 불가 영역) |
| 건물 | 장식용 픽셀아트 |

---

## 크리처 스프라이트

```
원형 마스크 크리처 이미지 (32×32px 또는 48×48px)
+ 픽셀 테두리 2px
+ 닉네임 태그 (말풍선 스타일)
이동 애니메이션: 2프레임 bounce
정지 애니메이션: idle breathing (scale 1.0 → 1.03, 2s loop)
```

---

## HUD 구성

```
상단:
  [← 나가기] / 온라인 인원 수 / [🔇 BGM] / [채팅]

하단 좌: (모바일 전용)
  D-pad 방향키 (상/하/좌/우)

하단 우:
  온라인 유저 목록 (최근 5명)
```

---

## 타 플레이어 클릭

- 클릭 시 davidkpiano 카드 디자인 모달 팝업
- 해당 크리처 상세 정보 표시
- [크리처 상세 보기] → `/creatures/{id}`
- [비밀채팅] 버튼 (DM 요청)

---

## 공개 채팅 (말풍선)

```
[채팅] 버튼 클릭
  → 입력창 활성화
  → 모바일/태블릿: 키패드 올라옴
  → PC: 키보드 입력

입력 후 전송 (최대 20자)
  → socket.emit('chat', { message })
  → 크리처 머리 위 말풍선 표시 (3초 후 fadeOut)
  → 전체 유저에게 broadcast
```

말풍선 디자인: 흰 배경 + 2px 픽셀 테두리 + 아래 꼬리

---

## 비밀 채팅 (1:1 DM)

```
타 플레이어 카드 → [비밀채팅] 클릭
  → 상대방에게 수락 요청 팝업
  → 수락: 양쪽 채팅창 오픈 (화면 우하단 float)
  → 거절: 요청자에게 "거절됐어요" Toast

채팅창:
  - 최대 20자 제한
  - 닫기 → 대화 종료 (히스토리 미저장, MVP)
```

---

## 크리처 없는 신규 유저 처리

광장 진입 시 안내 모달:
```
"광장을 이용하려면 먼저 크리처를 만들어야 해요!"
[지금 크리처 만들러 가기] → /upload
[다음에 하기] → 관전 모드 (이동 불가, 둘러보기만 가능)
```

---

## BGM

- 기본: OFF (브라우저 자동재생 정책 준수)
- 우상단 🔇/🔊 토글
- 경쾌한 픽셀 BGM 루프 (저작권 무료 소스 사용)

---

## 멀티플레이어 단계별 계획

| 단계 | 내용 |
|------|------|
| F3 MVP | 내 크리처 이동 + 타 유저 위치 수신 + 클릭 상세 팝업 + 공개 채팅 + DM |
| F4 고도화 | 채팅 히스토리 저장 + 이모지 반응 + 방 분리(구역) + 유저 수 제한 |

---

## WebSocket 이벤트 (F3 MVP)

| 이벤트 | 방향 | 데이터 |
|--------|------|--------|
| `join` | client → server | `{ user_id, creature_id, x, y }` |
| `move` | client → server | `{ x, y }` |
| `players` | server → client | `[{ user_id, creature_id, x, y, nickname }]` |
| `player_join` | server → all | `{ user_id, creature_id, x, y, nickname }` |
| `player_move` | server → all | `{ user_id, x, y }` |
| `player_leave` | server → all | `{ user_id }` |
| `chat` | client → server | `{ message }` (최대 20자) |
| `chat_broadcast` | server → all | `{ user_id, message }` |
| `dm_request` | client → server | `{ target_user_id }` |
| `dm_accept` | client → server | `{ requester_user_id }` |
| `dm_message` | client → server | `{ room_id, message }` |
| `dm_receive` | server → client | `{ room_id, from_user_id, message }` |
