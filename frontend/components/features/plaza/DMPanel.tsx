"use client";

import { useEffect, useRef, useState } from "react";

import type { DMIncoming, DMRoom } from "@/lib/types";

interface Props {
  mySocketId: string | null;
  pendingDM: DMIncoming | null;
  dmRooms: DMRoom[];
  onAccept: (fromSid: string) => void;
  onReject: (fromSid: string) => void;
  onSendMessage: (roomId: string, message: string) => void;
  onClose: (roomId: string) => void;
}

export default function DMPanel({
  mySocketId,
  pendingDM,
  dmRooms,
  onAccept,
  onReject,
  onSendMessage,
  onClose,
}: Props) {
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const [inputText, setInputText] = useState("");
  const msgEndRef = useRef<HTMLDivElement>(null);

  const activeRoom = dmRooms.find((r) => r.room_id === activeRoomId) ?? dmRooms[0] ?? null;

  // 새 메시지 도착 시 하단 스크롤
  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeRoom?.messages.length]);

  // 새 DM 방이 생기면 자동 활성화
  useEffect(() => {
    if (dmRooms.length > 0 && !activeRoomId) {
      setActiveRoomId(dmRooms[0].room_id);
    }
  }, [dmRooms, activeRoomId]);

  const handleSend = () => {
    const msg = inputText.trim();
    if (!msg || !activeRoom) return;
    onSendMessage(activeRoom.room_id, msg);
    setInputText("");
  };

  const handleCloseRoom = (roomId: string) => {
    onClose(roomId);
    if (activeRoomId === roomId) {
      const remaining = dmRooms.filter((r) => r.room_id !== roomId);
      setActiveRoomId(remaining[0]?.room_id ?? null);
    }
  };

  // 아무것도 없으면 렌더 생략
  if (!pendingDM && dmRooms.length === 0) return null;

  return (
    <div className="pointer-events-auto absolute bottom-6 right-6 z-30 flex flex-col gap-2">
      {/* ── DM 요청 알림 ── */}
      {pendingDM && (
        <div className="flex items-center gap-3 rounded-2xl bg-white/95 px-4 py-3 shadow-xl backdrop-blur-sm">
          <div className="flex-1">
            <p className="text-xs text-gray-500">DM 요청</p>
            <p className="font-bold text-gray-900">{pendingDM.from_nickname}</p>
          </div>
          <button
            type="button"
            onClick={() => onAccept(pendingDM.from_sid)}
            className="rounded-full bg-point px-3 py-1.5 text-sm font-semibold text-white transition hover:opacity-90"
          >
            수락
          </button>
          <button
            type="button"
            onClick={() => onReject(pendingDM.from_sid)}
            className="rounded-full bg-gray-200 px-3 py-1.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-300"
          >
            거절
          </button>
        </div>
      )}

      {/* ── DM 채팅창 ── */}
      {dmRooms.length > 0 && (
        <div className="flex w-72 flex-col rounded-2xl bg-white/95 shadow-xl backdrop-blur-sm overflow-hidden">
          {/* 탭 헤더 */}
          {dmRooms.length > 1 && (
            <div className="flex overflow-x-auto border-b border-gray-100">
              {dmRooms.map((r) => (
                <button
                  key={r.room_id}
                  type="button"
                  onClick={() => setActiveRoomId(r.room_id)}
                  className={`flex-shrink-0 px-3 py-2 text-xs font-semibold transition ${
                    activeRoomId === r.room_id
                      ? "border-b-2 border-point text-point"
                      : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  {r.peer_nickname}
                </button>
              ))}
            </div>
          )}

          {activeRoom && (
            <>
              {/* 채팅 헤더 */}
              <div className="flex items-center justify-between border-b border-gray-100 px-3 py-2">
                <span className="text-sm font-bold text-gray-900">
                  {activeRoom.peer_nickname}
                </span>
                <button
                  type="button"
                  onClick={() => handleCloseRoom(activeRoom.room_id)}
                  className="text-gray-400 transition hover:text-gray-700"
                  title="채팅 종료"
                >
                  ✕
                </button>
              </div>

              {/* 메시지 목록 */}
              <div className="flex max-h-48 flex-col gap-1.5 overflow-y-auto p-3">
                {activeRoom.messages.length === 0 && (
                  <p className="text-center text-xs text-gray-400">
                    대화를 시작해보세요
                  </p>
                )}
                {activeRoom.messages.map((msg, i) => {
                  const isMine = msg.from_sid === mySocketId;
                  return (
                    <div
                      key={i}
                      className={`flex ${isMine ? "justify-end" : "justify-start"}`}
                    >
                      <span
                        className={`max-w-[80%] rounded-2xl px-3 py-1.5 text-sm ${
                          isMine
                            ? "bg-point text-white"
                            : "bg-gray-100 text-gray-900"
                        }`}
                      >
                        {msg.message}
                      </span>
                    </div>
                  );
                })}
                <div ref={msgEndRef} />
              </div>

              {/* 입력창 */}
              <div className="flex gap-1.5 border-t border-gray-100 p-2">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.nativeEvent.isComposing) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="메시지 입력..."
                  maxLength={500}
                  className="min-w-0 flex-1 rounded-full bg-gray-100 px-3 py-1.5 text-sm outline-none"
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!inputText.trim()}
                  className="rounded-full bg-point px-3 py-1.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-40"
                >
                  전송
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
