# Stage 개발일지

## 0) 기본 정보
- 파트: `frontend` + `backend`
- Stage: `f3-3-plaza-multiplayer`
- 작성자: `Claude (PM + Tech Lead)`
- 작성일: `2026-03-13`
- 관련 이슈/PR: `N/A`

## 1) Stage 목표/범위
- 목표: `/plaza` 광장에 Socket.io 기반 멀티플레이어 구현
- 포함 범위:
  - `backend/app/api/v1/sockets/plaza_socket.py` 신규 — `/plaza` 네임스페이스
  - `backend/app/main.py` 업데이트 — `combined_app = socketio.ASGIApp(sio, ...)`
  - `backend/requirements.txt` — `python-socketio==5.11.4` 추가
  - `frontend/lib/types.ts` — PlazaPlayer, DMIncoming, DMMessage, DMRoom 타입 추가
  - `frontend/hooks/usePlazaSocket.ts` 신규 — 소켓 연결·이벤트 처리 훅
  - `frontend/components/features/plaza/DMPanel.tsx` 신규 — DM 요청/채팅 패널
  - `frontend/components/features/plaza/PhaserPlaza.tsx` 업데이트 — 멀티플레이어 통합
- 제외 범위:
  - 채팅 메시지 서버 영속 (세션 종료 시 소멸, 인메모리)
  - Redis pub/sub (단일 서버 로컬 환경 기준)

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: Socket.io ASGIApp 래핑**
- `socketio.ASGIApp(sio, other_asgi_app=app)` → FastAPI 위에 Socket.io 레이어 추가
- HTTP 요청은 FastAPI로 pass-through, WebSocket은 Socket.io 처리
- 진입점 변경: `uvicorn app.main:combined_app`

**결정 2: /plaza 네임스페이스**
- 광장 전용 네임스페이스로 격리
- JWT 검증: `connect` 이벤트의 `auth` 파라미터에서 `token` 추출 → jose 직접 검증 (DB 조회 없음)
- 중복 접속 방지: `user_id → sid` 역방향 맵 (`_user_sid`) + 기존 세션 kick

**결정 3: 인메모리 상태 구조**
```
_players:   sid → { sid, user_id, nickname, image_url, x, y }
_user_sid:  user_id → sid
_dm_rooms:  room_id → {sid_a, sid_b}
_sid_rooms: sid → set[room_id]
```
- disconnect 시 관련 DM 방 전부 정리 + 상대에게 `dm_closed` 이벤트 발송

**결정 4: 다른 플레이어 스프라이트 — 씬 내부 동적 로드**
- `addOtherPlayerSprite()`: 이미지 URL이 있으면 Phaser `load.image()` 후 `once("complete")` 콜백에서 그래픽 추가
- 로드 실패/URL 없음: 청록색 원 폴백

**결정 5: plaza_state 버퍼 패턴**
- `plaza_state` 이벤트가 Phaser 씬 초기화 전 도착할 수 있음 (비동기 import ~500ms)
- `pendingPlayersRef`에 버퍼 → 씬 `create()` 완료 후 일괄 처리

**결정 6: 이동 소켓 전송 스로틀 (100ms)**
- Phaser update()는 60fps → 소켓 전송은 ~10fps로 제한
- `moveAccMs` 누적 후 100ms 초과 시 emit, 이동 멈추면 초기화

**결정 7: 말풍선 위치 갱신**
- 말풍선 텍스트는 씬에 독립 오브젝트로 존재 (컨테이너 자식 아님)
- update()에서 플레이어/타 플레이어 위치 추적하여 말풍선 위치 갱신

**결정 8: DM 요청 — 다른 플레이어 클릭**
- `container.setInteractive({ cursor: "pointer" })` + `pointerdown` 이벤트
- `dmRequestCbRef.current?.(sid)` → React의 `sendDMRequest`로 포워드

### 2.2 이벤트 흐름

```
[연결] connect → join → plaza_state (기존 플레이어) + player_joined (타인에게)
[이동] move → player_moved (브로드캐스트)
[채팅] chat → chat_bubble (브로드캐스트)
[DM 요청] dm_request → dm_incoming (대상)
[DM 수락] dm_accept → dm_started (양측) + socketio room 생성
[DM 거절] dm_reject → dm_rejected (요청자)
[DM 메시지] dm_message → dm_message (room 내 브로드캐스트)
[DM 종료] dm_close → dm_closed (room 내) + room 해제
[중복 접속] connect → kicked (기존 sid) + disconnect
[나가기] disconnect → player_left (브로드캐스트) + DM 방 정리
```

### 2.3 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/app/api/v1/sockets/__init__.py` | 신규 | 패키지 초기화 |
| `backend/app/api/v1/sockets/plaza_socket.py` | 신규 | Socket.io /plaza 네임스페이스 |
| `backend/app/main.py` | 업데이트 | socketio import + combined_app 추가 |
| `backend/requirements.txt` | 의존성 추가 | `python-socketio==5.11.4` |
| `frontend/lib/types.ts` | 업데이트 | PlazaPlayer, DMIncoming, DMMessage, DMRoom 타입 |
| `frontend/hooks/usePlazaSocket.ts` | 신규 | 소켓 연결·이벤트 처리 훅 |
| `frontend/components/features/plaza/DMPanel.tsx` | 신규 | DM 요청 알림 + 채팅 패널 |
| `frontend/components/features/plaza/PhaserPlaza.tsx` | 업데이트 | 멀티플레이어 + 채팅 + DM 통합 |

## 3) 테스트/검증

### 3.1 빌드 결과
```
✅ BACKEND OK (from app.main import app, combined_app)
✅ npm run build: 14 pages, 오류 없음
✅ npm run lint: ESLint 오류 없음
   ⚠️ 기존 경고 1건 이월: app/creatures/[id]/page.tsx:274 no-img-element (본 Stage 변경 없음)
```

### 3.2 수동 검증 항목 (로컬 탭 2개 기준)

**서버 시작 명령:**
```bash
cd /Users/sups/Desktop/pocketman-dev-su/backend
USE_MOCK_AI=true ../.venv/bin/uvicorn app.main:combined_app --port 8000
```

- [ ] 탭 1 로그인 → `/plaza` 접속 → 맵 렌더링
- [ ] 탭 2 같은 계정 접속 → 탭 1 kicked 처리
- [ ] 탭 2 다른 계정 접속 → 탭 1에 타 플레이어 스프라이트 표시
- [ ] 탭 2 WASD 이동 → 탭 1에서 위치 실시간 갱신
- [ ] 탭 1 채팅 입력 → 양쪽 말풍선 3초 표시
- [ ] 탭 1에서 탭 2 플레이어 클릭 → DM 요청 → 탭 2 수락 → 채팅
- [ ] DM 거절 → 요청자에게 알림 없이 요청 취소
- [ ] DM 창 ✕ → 상대방 DM 창 닫힘
- [ ] 탭 2 브라우저 닫기 → 탭 1에서 플레이어 제거
- [ ] 접속 인원 수 HUD 정확 표시

## 4) 이슈/리스크

| 항목 | 심각도 | 상태 | 비고 |
|------|--------|------|------|
| 인메모리 상태 — 서버 재시작 시 초기화 | Medium | 🟡 허용 | 로컬/개발 환경 기준 |
| Redis pub/sub 미적용 | Medium | 🟡 미완 | 멀티 프로세스 배포 시 필요 |
| 말풍선 위치 — 카메라 스크롤 시 오프셋 | Low | 🟡 미완 | 카메라 좌표 변환 미적용 |
| 타 플레이어 이미지 CORS | Medium | 🟡 미검증 | Railway S3 CORS 설정 필요할 수 있음 |

## 5) 다음 Stage 인수인계

- **서버 시작**: `uvicorn app.main:combined_app` (기존 `app.main:app` 아님)
- **배포 시 고려**: Railway 환경에서 Socket.io 웹소켓 지원 확인 필요
- **미완성 항목**:
  - 말풍선 카메라 좌표 변환 (월드 → 스크린)
  - Redis pub/sub (멀티 인스턴스 배포)
  - BGM 파일: `/public/bgm/plaza.mp3` 추가 필요

## 5-1) 코드 리뷰 후 수정 이력

| 리뷰 항목 | 심각도 | 수정 내용 |
|-----------|--------|----------|
| 언마운트 레이스 — async import 후 소켓 생성 전 cleanup 실행 시 누수 | High | `mounted` 플래그 추가 — `await import()` 이후 `if (!mounted) return` 가드 |
| 소켓 URL — `NEXT_PUBLIC_API_BASE_URL`에 `/api/v1` 포함 시 `/api/v1/plaza`로 연결 오류 | High | `.replace(/\/api\/v1\/?$/, "")` 로 suffix 제거 후 소켓 베이스 URL 확보 |
| `player_joined` 버퍼 누락 — 씬 초기화 전 도착 시 드롭 | Medium | `sceneRef.current`가 null이면 `pendingPlayersRef`에 push |
| disconnect 시 상대 sid의 `_sid_rooms` 미정리 → stale state | Medium | peer_sid 루프에서 `_sid_rooms.get(peer_sid).discard(room_id)` 추가 |
| `load.once("complete")` 글로벌 이벤트 — 다중 로드 시 콜백 충돌 | Medium | `filecomplete-image-{textureKey}` 파일 단위 이벤트로 교체 |
| `float()` 예외 미처리 — 비정상 payload 시 핸들러 오류 | Low | `_safe_float()` 헬퍼 추가 — `TypeError`/`ValueError` 방어 |

## 6) AI 활용 기록

- Claude Sonnet 4.6 활용
- Socket.io AsyncServer ASGI 래핑 패턴
- `pendingPlayersRef` 버퍼 패턴 (Phaser 비동기 초기화 Race Condition 해결)
- Phaser 씬 내부 동적 이미지 로드 (`load.once("complete")`)
- always-fresh ref 패턴 (`dmRequestCbRef`, `moveCbRef`)
