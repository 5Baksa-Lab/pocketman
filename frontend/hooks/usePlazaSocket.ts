"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Socket } from "socket.io-client";

import { AuthStorage } from "@/lib/storage";
import type { DMIncoming, DMRoom, MyCreatureItem, PlazaPlayer } from "@/lib/types";

// ── PlazaSceneAPI — Phaser 씬이 노출하는 메서드 인터페이스 ──────────────────
export interface PlazaSceneAPI {
  addOtherPlayer: (
    sid: string,
    nickname: string,
    imageUrl: string | null,
    x: number,
    y: number,
  ) => void;
  removeOtherPlayer: (sid: string) => void;
  updateOtherPlayerPos: (sid: string, x: number, y: number) => void;
  showChatBubble: (sid: string | null, message: string) => void;
}

interface Options {
  playerCreature: MyCreatureItem | null;
  sceneRef: React.RefObject<PlazaSceneAPI | null>;
  /** 씬 초기화 전 도착한 초기 플레이어 목록 버퍼 */
  pendingPlayersRef: React.MutableRefObject<PlazaPlayer[]>;
}

interface UsePlazaSocketReturn {
  onlineCount: number;
  mySocketId: string | null;
  pendingDM: DMIncoming | null;
  dmRooms: DMRoom[];
  sendMove: (x: number, y: number) => void;
  sendChat: (message: string) => void;
  sendDMRequest: (targetSid: string) => void;
  sendDMAccept: (fromSid: string) => void;
  sendDMReject: (fromSid: string) => void;
  sendDMMessage: (roomId: string, message: string) => void;
  sendDMClose: (roomId: string) => void;
}

export function usePlazaSocket({
  playerCreature,
  sceneRef,
  pendingPlayersRef,
}: Options): UsePlazaSocketReturn {
  const socketRef = useRef<Socket | null>(null);

  const [onlineCount, setOnlineCount] = useState(1);
  const [mySocketId, setMySocketId] = useState<string | null>(null);
  const [pendingDM, setPendingDM] = useState<DMIncoming | null>(null);
  const [dmRooms, setDmRooms] = useState<DMRoom[]>([]);

  useEffect(() => {
    const token = AuthStorage.loadToken();
    if (!token || !playerCreature) return;

    // NEXT_PUBLIC_API_BASE_URL이 "…/api/v1" 형태이므로 해당 suffix 제거 후 소켓 베이스 URL 확보
    const SOCKET_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1")
      .replace(/\/api\/v1\/?$/, "")
      .replace(/\/$/, "");

    let mounted = true;
    let sock: Socket;

    const init = async () => {
      const { io } = await import("socket.io-client");
      // async import 이후 이미 언마운트됐으면 소켓 생성하지 않음
      if (!mounted) return;

      sock = io(`${SOCKET_BASE}/plaza`, {
        auth: { token },
        transports: ["websocket"],
      });
      socketRef.current = sock;

      sock.on("connect", () => {
        setMySocketId(sock.id ?? null);
        sock.emit("join", {
          nickname: playerCreature.name,
          image_url: playerCreature.image_url,
          x: 512,
          y: 180,
        });
      });

      sock.on("plaza_state", (data: { players: PlazaPlayer[]; count: number }) => {
        setOnlineCount(data.count);
        const scene = sceneRef.current;
        if (scene) {
          for (const p of data.players) {
            scene.addOtherPlayer(p.sid, p.nickname, p.image_url, p.x, p.y);
          }
        } else {
          // 씬 초기화 전 도착 → 버퍼
          pendingPlayersRef.current = data.players;
        }
      });

      sock.on("player_joined", (p: PlazaPlayer) => {
        setOnlineCount((n) => n + 1);
        const scene = sceneRef.current;
        if (scene) {
          scene.addOtherPlayer(p.sid, p.nickname, p.image_url, p.x, p.y);
        } else {
          // 씬 초기화 전 도착 → plaza_state 버퍼와 동일한 방식으로 버퍼링
          pendingPlayersRef.current = [...pendingPlayersRef.current, p];
        }
      });

      sock.on("player_left", (data: { sid: string }) => {
        setOnlineCount((n) => Math.max(1, n - 1));
        sceneRef.current?.removeOtherPlayer(data.sid);
      });

      sock.on("player_moved", (data: { sid: string; x: number; y: number }) => {
        sceneRef.current?.updateOtherPlayerPos(data.sid, data.x, data.y);
      });

      sock.on("chat_bubble", (data: { sid: string; message: string }) => {
        sceneRef.current?.showChatBubble(data.sid, data.message);
      });

      sock.on("dm_incoming", (data: DMIncoming) => {
        setPendingDM(data);
      });

      sock.on(
        "dm_started",
        (data: {
          room_id: string;
          peer_sid: string;
          peer_nickname: string;
          peer_image_url: string | null;
        }) => {
          setPendingDM(null);
          setDmRooms((prev) => {
            if (prev.some((r) => r.room_id === data.room_id)) return prev;
            return [...prev, { ...data, messages: [] }];
          });
        },
      );

      sock.on("dm_rejected", () => {
        setPendingDM(null);
      });

      sock.on(
        "dm_message",
        (data: { room_id: string; from_sid: string; message: string }) => {
          setDmRooms((prev) =>
            prev.map((r) =>
              r.room_id === data.room_id
                ? { ...r, messages: [...r.messages, data] }
                : r,
            ),
          );
        },
      );

      sock.on("dm_closed", (data: { room_id: string }) => {
        setDmRooms((prev) => prev.filter((r) => r.room_id !== data.room_id));
      });

      sock.on("kicked", () => {
        sock.disconnect();
      });
    };

    void init();

    return () => {
      mounted = false;
      sock?.disconnect();
      socketRef.current = null;
    };
    // playerCreature는 plaza 진입 시 한 번만 설정되므로 deps 추가 불필요
    // sceneRef/pendingPlayersRef는 stable ref — deps 제외
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMove = useCallback((x: number, y: number) => {
    socketRef.current?.emit("move", { x, y });
  }, []);

  const sendChat = useCallback((message: string) => {
    socketRef.current?.emit("chat", { message });
  }, []);

  const sendDMRequest = useCallback((targetSid: string) => {
    socketRef.current?.emit("dm_request", { target_sid: targetSid });
  }, []);

  const sendDMAccept = useCallback((fromSid: string) => {
    socketRef.current?.emit("dm_accept", { from_sid: fromSid });
  }, []);

  const sendDMReject = useCallback((fromSid: string) => {
    socketRef.current?.emit("dm_reject", { from_sid: fromSid });
  }, []);

  const sendDMMessage = useCallback((roomId: string, message: string) => {
    socketRef.current?.emit("dm_message", { room_id: roomId, message });
  }, []);

  const sendDMClose = useCallback((roomId: string) => {
    socketRef.current?.emit("dm_close", { room_id: roomId });
  }, []);

  return {
    onlineCount,
    mySocketId,
    pendingDM,
    dmRooms,
    sendMove,
    sendChat,
    sendDMRequest,
    sendDMAccept,
    sendDMReject,
    sendDMMessage,
    sendDMClose,
  };
}
