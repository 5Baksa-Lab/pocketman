"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { MyCreatureItem, PlazaPlayer } from "@/lib/types";
import { type PlazaSceneAPI, usePlazaSocket } from "@/hooks/usePlazaSocket";
import DMPanel from "./DMPanel";

// ── 월드 상수 ────────────────────────────────────────────────────────────────
const WORLD_W = 1024;
const WORLD_H = 1024;
const TILE = 32;
const PLAYER_SPEED = 180; // px/s
const PLAYER_RADIUS = 24;
const MOVE_THROTTLE_MS = 100; // 소켓 위치 전송 주기

// 분수 (충돌 영역)
const FOUNTAIN = { x: 400, y: 400, w: 224, h: 224 };

// 나무 위치
const TREES: { x: number; y: number }[] = [
  { x: 80, y: 80 }, { x: 944, y: 80 }, { x: 80, y: 944 }, { x: 944, y: 944 },
  { x: 200, y: 150 }, { x: 820, y: 150 }, { x: 150, y: 820 }, { x: 850, y: 820 },
  { x: 320, y: 80 }, { x: 700, y: 80 }, { x: 80, y: 350 }, { x: 944, y: 600 },
];

// ── D-pad 방향 ref 타입 ───────────────────────────────────────────────────────
interface DpadState {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
}

interface Props {
  playerCreature: MyCreatureItem | null;
  bgmEnabled: boolean;
  onBgmToggle: (v: boolean) => void;
  onExit: () => void;
}

export default function PhaserPlaza({ playerCreature, bgmEnabled, onBgmToggle, onExit }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<unknown>(null);
  const dpadRef = useRef<DpadState>({ up: false, down: false, left: false, right: false });
  const bgmRef = useRef<HTMLAudioElement | null>(null);

  // ── 소켓 연동용 refs ──────────────────────────────────────────────────────
  // Phaser 씬이 노출하는 API (create() 완료 후 set)
  const sceneRef = useRef<PlazaSceneAPI | null>(null);
  // plaza_state가 씬 초기화 전 도착할 때 버퍼
  const pendingPlayersRef = useRef<PlazaPlayer[]>([]);
  // 이동 소켓 전송 콜백 (씬 update()에서 호출)
  const moveCbRef = useRef<((x: number, y: number) => void) | null>(null);
  // DM 요청 콜백 (다른 플레이어 클릭 시)
  const dmRequestCbRef = useRef<((targetSid: string) => void) | null>(null);

  const [chatInput, setChatInput] = useState("");

  // ── 소켓 훅 ──────────────────────────────────────────────────────────────
  const {
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
  } = usePlazaSocket({ playerCreature, sceneRef, pendingPlayersRef });

  // moveCb / dmRequestCb 최신 함수 유지
  useEffect(() => {
    moveCbRef.current = sendMove;
  }, [sendMove]);

  useEffect(() => {
    dmRequestCbRef.current = sendDMRequest;
  }, [sendDMRequest]);

  // BGM 동기화
  useEffect(() => {
    if (!bgmRef.current) return;
    if (bgmEnabled) {
      bgmRef.current.play().catch(() => {/* autoplay blocked */});
    } else {
      bgmRef.current.pause();
    }
  }, [bgmEnabled]);

  // ── Phaser 초기화 ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    let mounted = true;

    const initGame = async () => {
      const Phaser = (await import("phaser")).default;
      if (!mounted) return;

      const creatureImageUrl = playerCreature?.image_url ?? null;
      const creatureName = playerCreature?.name ?? "나";
      const dpad = dpadRef;

      // 다른 플레이어 컨테이너 맵: sid → Container
      const otherPlayers = new Map<string, Phaser.GameObjects.Container>();
      // 타이머 핸들 맵: sid → Phaser.Time.TimerEvent (말풍선 제거용)
      const bubbleTimers = new Map<string, Phaser.Time.TimerEvent>();
      // 말풍선 텍스트 맵: sid|null → Text
      const bubbleTexts = new Map<string | null, Phaser.GameObjects.Text>();

      class PlazaScene extends Phaser.Scene {
        private player!: Phaser.GameObjects.Container;
        private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
        private wasd!: {
          up: Phaser.Input.Keyboard.Key;
          down: Phaser.Input.Keyboard.Key;
          left: Phaser.Input.Keyboard.Key;
          right: Phaser.Input.Keyboard.Key;
        };
        private moveAccMs = 0; // 이동 소켓 전송 누적 시간

        constructor() {
          super({ key: "PlazaScene" });
        }

        preload() {
          if (creatureImageUrl) {
            this.load.image("creature", creatureImageUrl);
          }
        }

        create() {
          this.drawMap();
          this.createPlayer();
          this.setupCamera();
          this.setupInput();

          // 씬 API 노출 (React 소켓 훅에서 사용)
          sceneRef.current = {
            addOtherPlayer: (sid, nickname, imageUrl, x, y) => {
              if (otherPlayers.has(sid)) return;
              this.addOtherPlayerSprite(sid, nickname, imageUrl, x, y);
            },
            removeOtherPlayer: (sid) => {
              const c = otherPlayers.get(sid);
              if (c) { c.destroy(); otherPlayers.delete(sid); }
            },
            updateOtherPlayerPos: (sid, x, y) => {
              const c = otherPlayers.get(sid);
              if (c) c.setPosition(x, y);
            },
            showChatBubble: (sid, message) => {
              this.showBubble(sid, message);
            },
          };

          // 씬 준비 후 버퍼된 플레이어 처리
          for (const p of pendingPlayersRef.current) {
            this.addOtherPlayerSprite(p.sid, p.nickname, p.image_url, p.x, p.y);
          }
          pendingPlayersRef.current = [];
        }

        private drawMap() {
          const floor = this.add.graphics();
          for (let row = 0; row < WORLD_H / TILE; row++) {
            for (let col = 0; col < WORLD_W / TILE; col++) {
              const color = (row + col) % 2 === 0 ? 0xf6f2e8 : 0xd4edea;
              floor.fillStyle(color, 1);
              floor.fillRect(col * TILE, row * TILE, TILE, TILE);
            }
          }

          const fountain = this.add.graphics();
          fountain.fillStyle(0xb0d8d8, 1);
          fountain.fillEllipse(
            FOUNTAIN.x + FOUNTAIN.w / 2,
            FOUNTAIN.y + FOUNTAIN.h / 2,
            FOUNTAIN.w,
            FOUNTAIN.h
          );
          fountain.fillStyle(0x4a9fa5, 1);
          fountain.fillCircle(FOUNTAIN.x + FOUNTAIN.w / 2, FOUNTAIN.y + FOUNTAIN.h / 2, 45);
          fountain.fillStyle(0x9ee5e5, 0.8);
          fountain.fillCircle(FOUNTAIN.x + FOUNTAIN.w / 2, FOUNTAIN.y + FOUNTAIN.h / 2, 28);
          fountain.lineStyle(3, 0x2a7a7a, 1);
          fountain.strokeEllipse(
            FOUNTAIN.x + FOUNTAIN.w / 2,
            FOUNTAIN.y + FOUNTAIN.h / 2,
            FOUNTAIN.w,
            FOUNTAIN.h
          );

          const trees = this.add.graphics();
          for (const t of TREES) {
            trees.fillStyle(0x000000, 0.1);
            trees.fillEllipse(t.x, t.y + 2, 36, 10);
            trees.fillStyle(0x8b6914, 1);
            trees.fillRect(t.x - 5, t.y - 5, 10, 22);
            trees.fillStyle(0x2d8a2d, 1);
            trees.fillCircle(t.x, t.y - 22, 22);
            trees.fillStyle(0x3aa53a, 1);
            trees.fillCircle(t.x - 11, t.y - 30, 15);
            trees.fillCircle(t.x + 11, t.y - 30, 15);
            trees.fillStyle(0x4dc44d, 1);
            trees.fillCircle(t.x, t.y - 38, 12);
          }
          trees.setDepth(5);
        }

        private createPlayer() {
          this.player = this.add.container(512, 180);
          this.player.setDepth(10);
          this.addPlayerGraphics(this.player, creatureImageUrl, creatureName, "creature", true);
        }

        /** 플레이어/타 플레이어 공용 스프라이트 생성 */
        private addPlayerGraphics(
          container: Phaser.GameObjects.Container,
          imageUrl: string | null,
          name: string,
          textureKey: string,
          isLocal: boolean,
        ) {
          const borderColor = isLocal ? 0x1a1a2e : 0x2a7a7a;

          if (imageUrl && this.textures.exists(textureKey)) {
            const mask = this.add.graphics();
            mask.fillStyle(0xffffff, 1);
            mask.fillCircle(0, 0, PLAYER_RADIUS);
            const geoMask = mask.createGeometryMask();

            const img = this.add.image(0, 0, textureKey);
            img.setDisplaySize(PLAYER_RADIUS * 2, PLAYER_RADIUS * 2);
            img.setMask(geoMask);

            const border = this.add.arc(0, 0, PLAYER_RADIUS, 0, 360, false);
            border.setStrokeStyle(3, borderColor, 1);
            border.setFillStyle(0, 0);
            container.add([img, border]);
          } else {
            const color = isLocal ? 0x7c6af0 : 0x4a9fa5;
            const circle = this.add.arc(0, 0, PLAYER_RADIUS, 0, 360, false, color);
            circle.setStrokeStyle(3, borderColor, 1);
            container.add(circle);
          }

          const tag = this.add
            .text(0, -PLAYER_RADIUS - 14, name, {
              fontSize: "12px",
              color: "#1a1a2e",
              backgroundColor: "#ffffffdd",
              padding: { x: 6, y: 3 },
            })
            .setOrigin(0.5, 1);
          container.add(tag);
        }

        /** 다른 플레이어 스프라이트 추가 */
        private addOtherPlayerSprite(
          sid: string,
          nickname: string,
          imageUrl: string | null,
          x: number,
          y: number,
        ) {
          const textureKey = `other_${sid}`;
          const container = this.add.container(x, y);
          container.setDepth(9);

          const doAdd = () => {
            this.addPlayerGraphics(container, imageUrl, nickname, textureKey, false);
            // 클릭 → DM 요청
            container.setSize(PLAYER_RADIUS * 2, PLAYER_RADIUS * 2);
            container.setInteractive({ cursor: "pointer" });
            container.on("pointerdown", () => {
              dmRequestCbRef.current?.(sid);
            });
            otherPlayers.set(sid, container);
          };

          if (imageUrl && !this.textures.exists(textureKey)) {
            this.load.image(textureKey, imageUrl);
            // 글로벌 complete 대신 파일 단위 이벤트 사용 → 다중 동시 로드 시 충돌 방지
            this.load.once(`filecomplete-image-${textureKey}`, doAdd);
            this.load.start();
          } else {
            doAdd();
          }
        }

        /** 말풍선 표시 (3초 후 사라짐) */
        private showBubble(sid: string | null, message: string) {
          // 기존 말풍선 제거
          const existing = bubbleTexts.get(sid);
          if (existing) existing.destroy();
          const existingTimer = bubbleTimers.get(sid ?? "local");
          if (existingTimer) existingTimer.remove();

          // 말풍선 텍스트 생성 (컨테이너 기준 상대 좌표)
          const target = sid ? otherPlayers.get(sid) : this.player;
          if (!target) return;

          const bubble = this.add.text(target.x, target.y - PLAYER_RADIUS - 30, message, {
            fontSize: "13px",
            color: "#1a1a2e",
            backgroundColor: "#ffffffee",
            padding: { x: 8, y: 4 },
          }).setOrigin(0.5, 1).setDepth(20);

          bubbleTexts.set(sid, bubble);

          // 3초 후 제거
          const timer = this.time.delayedCall(3000, () => {
            bubble.destroy();
            bubbleTexts.delete(sid);
            bubbleTimers.delete(sid ?? "local");
          });
          bubbleTimers.set(sid ?? "local", timer);
        }

        private setupCamera() {
          this.cameras.main.setBounds(0, 0, WORLD_W, WORLD_H);
          this.cameras.main.startFollow(this.player, true, 0.08, 0.08);
          this.cameras.main.setZoom(1);
        }

        private setupInput() {
          this.cursors = this.input.keyboard!.createCursorKeys();
          this.wasd = {
            up: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.W),
            down: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.S),
            left: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.A),
            right: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.D),
          };
        }

        update(_time: number, delta: number) {
          const dt = delta / 1000;
          const d = dpad.current;

          let vx = 0;
          let vy = 0;

          if (this.cursors.left.isDown || this.wasd.left.isDown || d.left) vx = -PLAYER_SPEED;
          else if (this.cursors.right.isDown || this.wasd.right.isDown || d.right) vx = PLAYER_SPEED;

          if (this.cursors.up.isDown || this.wasd.up.isDown || d.up) vy = -PLAYER_SPEED;
          else if (this.cursors.down.isDown || this.wasd.down.isDown || d.down) vy = PLAYER_SPEED;

          if (vx !== 0 && vy !== 0) {
            vx *= 0.707;
            vy *= 0.707;
          }

          const nx = Phaser.Math.Clamp(this.player.x + vx * dt, PLAYER_RADIUS, WORLD_W - PLAYER_RADIUS);
          const ny = Phaser.Math.Clamp(this.player.y + vy * dt, PLAYER_RADIUS, WORLD_H - PLAYER_RADIUS);

          // 분수 충돌 (AABB)
          const inFountainX = nx + PLAYER_RADIUS > FOUNTAIN.x && nx - PLAYER_RADIUS < FOUNTAIN.x + FOUNTAIN.w;
          const inFountainY = ny + PLAYER_RADIUS > FOUNTAIN.y && ny - PLAYER_RADIUS < FOUNTAIN.y + FOUNTAIN.h;

          if (inFountainX && inFountainY) {
            const hx = Phaser.Math.Clamp(this.player.x + vx * dt, PLAYER_RADIUS, WORLD_W - PLAYER_RADIUS);
            const hInY = this.player.y + PLAYER_RADIUS > FOUNTAIN.y && this.player.y - PLAYER_RADIUS < FOUNTAIN.y + FOUNTAIN.h;
            const hInX = hx + PLAYER_RADIUS > FOUNTAIN.x && hx - PLAYER_RADIUS < FOUNTAIN.x + FOUNTAIN.w;
            if (!(hInX && hInY)) {
              this.player.setX(hx);
            }
            const vy2 = Phaser.Math.Clamp(this.player.y + vy * dt, PLAYER_RADIUS, WORLD_H - PLAYER_RADIUS);
            const vInX = this.player.x + PLAYER_RADIUS > FOUNTAIN.x && this.player.x - PLAYER_RADIUS < FOUNTAIN.x + FOUNTAIN.w;
            const vInY = vy2 + PLAYER_RADIUS > FOUNTAIN.y && vy2 - PLAYER_RADIUS < FOUNTAIN.y + FOUNTAIN.h;
            if (!(vInX && vInY)) {
              this.player.setY(vy2);
            }
          } else {
            this.player.setPosition(nx, ny);
          }

          // 말풍선 위치 갱신 (플레이어 이동 추적)
          const myBubble = bubbleTexts.get(null);
          if (myBubble) {
            myBubble.setPosition(this.player.x, this.player.y - PLAYER_RADIUS - 30);
          }
          // 타 플레이어 말풍선 위치 갱신
          for (const [sid, bubble] of bubbleTexts.entries()) {
            if (sid === null) continue;
            const c = otherPlayers.get(sid);
            if (c) bubble.setPosition(c.x, c.y - PLAYER_RADIUS - 30);
          }

          // 이동 소켓 전송 (throttle)
          if (vx !== 0 || vy !== 0) {
            this.moveAccMs += delta;
            if (this.moveAccMs >= MOVE_THROTTLE_MS) {
              this.moveAccMs = 0;
              moveCbRef.current?.(this.player.x, this.player.y);
            }
          } else {
            this.moveAccMs = 0;
          }
        }
      }

      const game = new Phaser.Game({
        type: Phaser.AUTO,
        parent: container,
        width: container.clientWidth || window.innerWidth,
        height: container.clientHeight || window.innerHeight,
        backgroundColor: "#e8f4f0",
        scene: [PlazaScene],
        scale: {
          mode: Phaser.Scale.RESIZE,
          autoCenter: Phaser.Scale.CENTER_BOTH,
        },
        input: { keyboard: true },
      });

      if (!mounted) {
        game.destroy(true);
        return;
      }

      gameRef.current = game;
    };

    void initGame();

    return () => {
      mounted = false;
      sceneRef.current = null;
      if (gameRef.current) {
        (gameRef.current as { destroy: (v: boolean) => void }).destroy(true);
        gameRef.current = null;
      }
    };
  }, [playerCreature]);

  // D-pad 터치 핸들러
  const setDpad = useCallback((key: keyof DpadState, value: boolean) => {
    dpadRef.current[key] = value;
  }, []);

  // 채팅 전송
  const handleChatSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const msg = chatInput.trim();
      if (!msg) return;
      sendChat(msg);
      // 내 말풍선은 씬에서 직접 표시
      sceneRef.current?.showChatBubble(null, msg);
      setChatInput("");
    },
    [chatInput, sendChat],
  );

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#e8f4f0]">
      {/* BGM */}
      <audio ref={bgmRef} src="/bgm/plaza.mp3" loop preload="none" />

      {/* Phaser canvas */}
      <div ref={containerRef} className="absolute inset-0" />

      {/* ── 상단 HUD ── */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20">
        <div className="pointer-events-auto flex items-center justify-between bg-black/40 px-4 py-3 backdrop-blur-sm">
          <button
            type="button"
            onClick={onExit}
            className="flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-white/30"
          >
            ← 나가기
          </button>

          <div className="flex flex-col items-center">
            <span className="text-sm font-bold text-white drop-shadow">포켓 광장</span>
            <span className="text-xs text-white/70">{onlineCount}명 접속 중</span>
          </div>

          <button
            type="button"
            onClick={() => onBgmToggle(!bgmEnabled)}
            className="rounded-full bg-white/20 px-3 py-1.5 text-sm text-white transition hover:bg-white/30"
            title={bgmEnabled ? "BGM 끄기" : "BGM 켜기"}
          >
            {bgmEnabled ? "🔊" : "🔇"}
          </button>
        </div>
      </div>

      {/* ── 채팅 입력 (하단 중앙) ── */}
      <form
        onSubmit={handleChatSubmit}
        className="pointer-events-auto absolute bottom-6 left-1/2 z-20 -translate-x-1/2 flex gap-2"
      >
        <input
          type="text"
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder="채팅 (Enter)"
          maxLength={100}
          className="w-52 rounded-full bg-black/40 px-4 py-2 text-sm text-white placeholder-white/50 outline-none backdrop-blur-sm focus:bg-black/60"
        />
        <button
          type="submit"
          disabled={!chatInput.trim()}
          className="rounded-full bg-white/20 px-3 py-2 text-sm text-white backdrop-blur-sm transition hover:bg-white/30 disabled:opacity-40"
        >
          전송
        </button>
      </form>

      {/* ── 모바일 D-pad (lg 이상 숨김) ── */}
      <div className="pointer-events-none absolute bottom-20 left-6 z-20 lg:hidden">
        <div className="pointer-events-auto relative h-[120px] w-[120px] select-none">
          <button
            type="button"
            onTouchStart={() => setDpad("up", true)}
            onTouchEnd={() => setDpad("up", false)}
            onTouchCancel={() => setDpad("up", false)}
            onMouseDown={() => setDpad("up", true)}
            onMouseUp={() => setDpad("up", false)}
            onMouseLeave={() => setDpad("up", false)}
            className="absolute left-1/2 top-0 -translate-x-1/2 rounded-lg bg-white/60 px-4 py-2.5 text-lg font-bold text-gray-700 shadow backdrop-blur-sm active:bg-white/90"
          >▲</button>
          <button
            type="button"
            onTouchStart={() => setDpad("down", true)}
            onTouchEnd={() => setDpad("down", false)}
            onTouchCancel={() => setDpad("down", false)}
            onMouseDown={() => setDpad("down", true)}
            onMouseUp={() => setDpad("down", false)}
            onMouseLeave={() => setDpad("down", false)}
            className="absolute bottom-0 left-1/2 -translate-x-1/2 rounded-lg bg-white/60 px-4 py-2.5 text-lg font-bold text-gray-700 shadow backdrop-blur-sm active:bg-white/90"
          >▼</button>
          <button
            type="button"
            onTouchStart={() => setDpad("left", true)}
            onTouchEnd={() => setDpad("left", false)}
            onTouchCancel={() => setDpad("left", false)}
            onMouseDown={() => setDpad("left", true)}
            onMouseUp={() => setDpad("left", false)}
            onMouseLeave={() => setDpad("left", false)}
            className="absolute left-0 top-1/2 -translate-y-1/2 rounded-lg bg-white/60 px-2.5 py-4 text-lg font-bold text-gray-700 shadow backdrop-blur-sm active:bg-white/90"
          >◀</button>
          <button
            type="button"
            onTouchStart={() => setDpad("right", true)}
            onTouchEnd={() => setDpad("right", false)}
            onTouchCancel={() => setDpad("right", false)}
            onMouseDown={() => setDpad("right", true)}
            onMouseUp={() => setDpad("right", false)}
            onMouseLeave={() => setDpad("right", false)}
            className="absolute right-0 top-1/2 -translate-y-1/2 rounded-lg bg-white/60 px-2.5 py-4 text-lg font-bold text-gray-700 shadow backdrop-blur-sm active:bg-white/90"
          >▶</button>
        </div>
      </div>

      {/* ── 키보드 안내 (데스크톱) ── */}
      <div className="pointer-events-none absolute bottom-6 right-6 z-20 hidden lg:block">
        <div className="rounded-xl bg-black/30 px-4 py-3 text-xs text-white/80 backdrop-blur-sm">
          <p className="font-semibold text-white/90">이동: WASD / 방향키</p>
          <p className="mt-0.5 text-white/60">다른 플레이어 클릭 → DM 요청</p>
        </div>
      </div>

      {/* ── DM 패널 ── */}
      <DMPanel
        mySocketId={mySocketId}
        pendingDM={pendingDM}
        dmRooms={dmRooms}
        onAccept={sendDMAccept}
        onReject={sendDMReject}
        onSendMessage={sendDMMessage}
        onClose={sendDMClose}
      />
    </div>
  );
}
