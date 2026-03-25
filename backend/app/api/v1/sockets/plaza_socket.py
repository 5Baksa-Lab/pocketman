"""
Plaza Socket.io 서버 — /plaza 네임스페이스
멀티플레이어 이동, 채팅, DM 기능
"""
import logging

import socketio
from jose import JWTError, jwt

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY

_log = logging.getLogger(__name__)

# ── Socket.io 서버 (ASGI 호환) ─────────────────────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# ── 인메모리 상태 ──────────────────────────────────────────────────────────
# sid → { sid, user_id, nickname, image_url, x, y }
_players: dict[str, dict] = {}
# user_id → sid  (중복 접속 시 기존 세션 kick)
_user_sid: dict[str, str] = {}
# room_id → set of two sids
_dm_rooms: dict[str, set[str]] = {}
# sid → set of room_ids
_sid_rooms: dict[str, set[str]] = {}


def _verify_token(token: str) -> str:
    """JWT 검증 → user_id. 실패 시 ValueError."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise ValueError("sub 누락")
        return user_id
    except JWTError as exc:
        raise ValueError(f"JWT 오류: {exc}") from exc


def _dm_room_id(sid_a: str, sid_b: str) -> str:
    return "dm:" + ":".join(sorted([sid_a, sid_b]))


def _safe_float(value: object, default: float) -> float:
    """비정상 payload 방어 — float 변환 실패 시 default 반환."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


# ── /plaza 이벤트 ──────────────────────────────────────────────────────────

@sio.event(namespace="/plaza")
async def connect(sid: str, _environ: dict, auth: dict | None = None):
    token = (auth or {}).get("token", "")
    try:
        user_id = _verify_token(token)
    except ValueError:
        _log.warning("plaza connect 거부: 인증 실패 sid=%s", sid)
        return False  # 연결 거부

    # 중복 접속: 기존 세션 kick
    if user_id in _user_sid:
        old_sid = _user_sid[user_id]
        await sio.emit("kicked", {"reason": "다른 곳에서 접속했습니다."}, to=old_sid, namespace="/plaza")
        await sio.disconnect(old_sid, namespace="/plaza")

    _user_sid[user_id] = sid
    _sid_rooms[sid] = set()
    _log.info("plaza connect: sid=%s user_id=%.8s...", sid, user_id)


@sio.event(namespace="/plaza")
async def disconnect(sid: str):
    player = _players.pop(sid, None)
    if player:
        user_id = player["user_id"]
        _user_sid.pop(user_id, None)
        await sio.emit("player_left", {"sid": sid}, namespace="/plaza", skip_sid=sid)

    # DM 방 정리
    for room_id in list(_sid_rooms.get(sid, [])):
        if room_id in _dm_rooms:
            # 상대 sid의 _sid_rooms에서도 room_id 제거
            for peer_sid in list(_dm_rooms[room_id]):
                if peer_sid != sid:
                    _sid_rooms.get(peer_sid, set()).discard(room_id)
            _dm_rooms.pop(room_id, None)
            await sio.emit(
                "dm_closed",
                {"room_id": room_id, "reason": "상대가 나갔습니다."},
                room=room_id,
                namespace="/plaza",
            )

    _sid_rooms.pop(sid, None)
    _log.info("plaza disconnect: sid=%s", sid)


@sio.event(namespace="/plaza")
async def join(sid: str, data: dict):
    """입장 — 닉네임·이미지·초기 좌표 등록."""
    user_id = next((uid for uid, s in _user_sid.items() if s == sid), None)
    if not user_id:
        return

    nickname = str(data.get("nickname", "플레이어"))[:20]
    image_url = data.get("image_url") or None
    x = _safe_float(data.get("x"), 512.0)
    y = _safe_float(data.get("y"), 180.0)

    _players[sid] = {
        "sid": sid,
        "user_id": user_id,
        "nickname": nickname,
        "image_url": image_url,
        "x": x,
        "y": y,
    }

    # 기존 플레이어 목록 전달
    existing = [p for s, p in _players.items() if s != sid]
    await sio.emit(
        "plaza_state",
        {"players": existing, "count": len(_players)},
        to=sid,
        namespace="/plaza",
    )

    # 신규 플레이어 브로드캐스트
    await sio.emit("player_joined", _players[sid], namespace="/plaza", skip_sid=sid)
    _log.info("plaza join: sid=%s nickname=%s", sid, nickname)


@sio.event(namespace="/plaza")
async def move(sid: str, data: dict):
    """위치 업데이트 → 브로드캐스트."""
    if sid not in _players:
        return
    x = max(0.0, min(1024.0, _safe_float(data.get("x"), _players[sid]["x"])))
    y = max(0.0, min(1024.0, _safe_float(data.get("y"), _players[sid]["y"])))
    _players[sid]["x"] = x
    _players[sid]["y"] = y
    await sio.emit("player_moved", {"sid": sid, "x": x, "y": y}, namespace="/plaza", skip_sid=sid)


@sio.event(namespace="/plaza")
async def chat(sid: str, data: dict):
    """광장 채팅 말풍선 브로드캐스트."""
    if sid not in _players:
        return
    msg = str(data.get("message", ""))[:100].strip()
    if not msg:
        return
    await sio.emit("chat_bubble", {"sid": sid, "message": msg}, namespace="/plaza")


@sio.event(namespace="/plaza")
async def dm_request(sid: str, data: dict):
    """DM 요청 — 대상에게 알림."""
    target_sid = str(data.get("target_sid", ""))
    if target_sid not in _players or target_sid == sid or sid not in _players:
        return
    await sio.emit(
        "dm_incoming",
        {
            "from_sid": sid,
            "from_nickname": _players[sid]["nickname"],
            "from_image_url": _players[sid]["image_url"],
        },
        to=target_sid,
        namespace="/plaza",
    )


@sio.event(namespace="/plaza")
async def dm_accept(sid: str, data: dict):
    """DM 수락 — 양측에 room_id 전달."""
    requester_sid = str(data.get("from_sid", ""))
    if requester_sid not in _players or sid not in _players:
        return

    room_id = _dm_room_id(sid, requester_sid)
    _dm_rooms[room_id] = {sid, requester_sid}
    _sid_rooms.setdefault(sid, set()).add(room_id)
    _sid_rooms.setdefault(requester_sid, set()).add(room_id)

    await sio.enter_room(sid, room_id, namespace="/plaza")
    await sio.enter_room(requester_sid, room_id, namespace="/plaza")

    await sio.emit(
        "dm_started",
        {
            "room_id": room_id,
            "peer_sid": requester_sid,
            "peer_nickname": _players[requester_sid]["nickname"],
            "peer_image_url": _players[requester_sid]["image_url"],
        },
        to=sid,
        namespace="/plaza",
    )
    await sio.emit(
        "dm_started",
        {
            "room_id": room_id,
            "peer_sid": sid,
            "peer_nickname": _players[sid]["nickname"],
            "peer_image_url": _players[sid]["image_url"],
        },
        to=requester_sid,
        namespace="/plaza",
    )


@sio.event(namespace="/plaza")
async def dm_reject(sid: str, data: dict):
    """DM 거절."""
    requester_sid = str(data.get("from_sid", ""))
    if requester_sid not in _players:
        return
    await sio.emit("dm_rejected", {"by_sid": sid}, to=requester_sid, namespace="/plaza")


@sio.event(namespace="/plaza")
async def dm_message(sid: str, data: dict):
    """DM 메시지 전송."""
    room_id = str(data.get("room_id", ""))
    if room_id not in _dm_rooms or sid not in _dm_rooms[room_id]:
        return
    msg = str(data.get("message", ""))[:500].strip()
    if not msg:
        return
    await sio.emit(
        "dm_message",
        {"room_id": room_id, "from_sid": sid, "message": msg},
        room=room_id,
        namespace="/plaza",
    )


@sio.event(namespace="/plaza")
async def dm_close(sid: str, data: dict):
    """DM 방 종료."""
    room_id = str(data.get("room_id", ""))
    if room_id not in _dm_rooms:
        return
    await sio.emit(
        "dm_closed",
        {"room_id": room_id, "reason": "상대가 채팅을 종료했습니다."},
        room=room_id,
        namespace="/plaza",
    )
    for member_sid in list(_dm_rooms.get(room_id, [])):
        await sio.leave_room(member_sid, room_id, namespace="/plaza")
        _sid_rooms.get(member_sid, set()).discard(room_id)
    _dm_rooms.pop(room_id, None)
