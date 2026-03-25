# 백엔드 기능 설계: 광장 WebSocket (Plaza)

- 작성일: 2026-03-12
- 상태: 설계 확정 (F3에서 구현 예정)
- 관련 프론트엔드: `/plaza`

---

## 개요

포켓몬 Platinum Wi-Fi 광장 스타일 실시간 멀티플레이어 서버.
socket.io 기반 WebSocket. 위치 동기화 + 공개 채팅 + 1:1 비밀 채팅.

---

## 기술 스택

- 라이브러리: `socket.io` (Python: `python-socketio` + `uvicorn`)
- 기존 FastAPI 앱에 ASGI 마운트 방식으로 통합
- 별도 포트 불필요 (동일 포트, 경로 `/socket.io`)

---

## 인증

- 연결 시 `auth: { token: "JWT" }` 전달
- 서버에서 JWT 검증 → `user_id` 추출
- 크리처 없는 유저: 연결은 허용, 이동 불가 (관전 모드)

---

## 네임스페이스

- `/plaza`: 광장 전용 네임스페이스

---

## 이벤트 목록

### 클라이언트 → 서버

| 이벤트 | 데이터 | 설명 |
|--------|--------|------|
| `join` | `{ creature_id, x, y }` | 광장 입장 |
| `move` | `{ x, y }` | 위치 이동 |
| `chat` | `{ message }` | 공개 채팅 (최대 20자) |
| `dm_request` | `{ target_user_id }` | DM 요청 |
| `dm_accept` | `{ requester_user_id }` | DM 수락 |
| `dm_reject` | `{ requester_user_id }` | DM 거절 |
| `dm_message` | `{ room_id, message }` | DM 메시지 전송 |
| `dm_close` | `{ room_id }` | DM 종료 |
| `leave` | (없음) | 광장 퇴장 |

### 서버 → 클라이언트

| 이벤트 | 데이터 | 설명 |
|--------|--------|------|
| `welcome` | `{ players: [...] }` | 입장 시 현재 유저 목록 |
| `player_join` | `{ user_id, creature_id, nickname, x, y }` | 새 유저 입장 |
| `player_move` | `{ user_id, x, y }` | 유저 이동 |
| `player_leave` | `{ user_id }` | 유저 퇴장 |
| `chat_broadcast` | `{ user_id, message }` | 공개 채팅 broadcast |
| `dm_incoming` | `{ requester_user_id, nickname }` | DM 요청 수신 |
| `dm_started` | `{ room_id, partner: { user_id, nickname } }` | DM 수락됨 |
| `dm_rejected` | `{ target_user_id }` | DM 거절됨 |
| `dm_receive` | `{ room_id, from_user_id, message }` | DM 메시지 수신 |
| `dm_closed` | `{ room_id }` | 상대방이 DM 종료 |
| `error` | `{ code, message }` | 에러 |

---

## 서버 메모리 상태 구조

```python
# 광장 접속자 (user_id → 상태)
players: dict[str, PlayerState] = {}

@dataclass
class PlayerState:
    user_id: str
    socket_id: str
    creature_id: str
    nickname: str
    x: int
    y: int

# DM 방 (room_id → 두 참여자)
dm_rooms: dict[str, tuple[str, str]] = {}
```

---

## 맵 좌표 유효성 검사

- 이동 불가 타일 목록은 서버에서도 검증 (클라이언트 조작 방지)
- 맵 범위: `0 ≤ x ≤ 1023`, `0 ≤ y ≤ 1023`
- 이동 불가 타일: 분수 중앙 (400~624), 나무 좌표 목록 (서버 설정 파일로 관리)

---

## 채팅 정책

- 최대 20자 (서버에서도 검증, 초과 시 자르기)
- 도배 방지: 동일 유저 1초 이내 재전송 무시 (rate limit)

---

## DM 정책

- 히스토리 미저장 (MVP): 메모리에서만 중계
- 최대 동시 DM 방: 유저당 1개
- 상대방 오프라인 시 DM 요청 → `error` 이벤트 반환

---

## 온라인 상태 API

광장 접속 여부를 REST API로도 조회 가능 (creatures 상세 페이지의 "광장에서 찾기" 버튼용).

### GET `/plaza/online`

**Response 200**:
```json
{
  "online_users": ["user_uuid_1", "user_uuid_2"]
}
```

### GET `/plaza/online/{user_id}`

**Response 200**:
```json
{ "is_online": true, "x": 512, "y": 480 }
```

---

## FastAPI 통합 방식

```python
# app/main.py
import socketio
from fastapi import FastAPI

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# 실행: uvicorn app.main:socket_app
```
