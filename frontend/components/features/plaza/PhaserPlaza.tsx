"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { MyCreatureItem, PlazaPlayer } from "@/lib/types";
import { type PlazaSceneAPI, usePlazaSocket } from "@/hooks/usePlazaSocket";
import DMPanel from "./DMPanel";

// ── 월드 상수 ────────────────────────────────────────────────────────────────
// 원본 맵 이미지: 480×480px → 2× 스케일 → 960×960 게임 월드
const IMG_SCALE = 2;
const WORLD_W = 480 * IMG_SCALE; // 960
const WORLD_H = 480 * IMG_SCALE; // 960

const PLAYER_SPEED = 150;
const PLAYER_RADIUS = 16;
const MOVE_THROTTLE_MS = 100;

// 스프라이트 시트 프레임 (Imagen 1024×1024, 3열×4행)
const SPRITE_FRAME_W = 341;
const SPRITE_FRAME_H = 256;
const SPRITE_DISPLAY = 40;

// ── 충돌 영역 (원본 이미지 픽셀 × IMG_SCALE) ─────────────────────────────────
// 원본에서 픽셀 위치를 측정해 ×2 적용
const COLLIDERS = [
  // 테두리 나무 (4면) — 플레이어가 맵 밖으로 나가지 못하게
  { x: 0,        y: 0,        w: WORLD_W,  h: 56  }, // 상단 나무
  { x: 0,        y: WORLD_H - 56, w: WORLD_W, h: 56 }, // 하단 나무
  { x: 0,        y: 56,       w: 56,       h: WORLD_H - 112 }, // 좌측 나무
  { x: WORLD_W - 56, y: 56,   w: 56,       h: WORLD_H - 112 }, // 우측 나무
  // 왼쪽 대형 수면 (원본 ~35,125 / 60×130 → ×2)
  { x: 56,       y: 248,      w: 128,      h: 268 },
  // 우상단 소형 수면 (원본 ~335,30 / 75×85 → ×2)
  { x: 660,      y: 56,       w: 152,      h: 170 },
  // 건물 A 상단 좌측 (원본 ~130,56 / 90×80 → ×2)
  { x: 256,      y: 56,       w: 180,      h: 156 },
  // 건물 B 상단 우측 (원본 ~265,50 / 120×115 → ×2)
  { x: 490,      y: 56,       w: 230,      h: 228 },
  // 포켓몬 센터 좌중앙 (원본 ~55,310 / 85×75 → ×2)
  { x: 96,       y: 408,      w: 170,      h: 152 },
  // 포켓몬 마트 우중앙 (원본 ~300,285 / 100×90 → ×2)
  { x: 472,      y: 342,      w: 200,      h: 182 },
  // 건물 C 하단 우측 (원본 ~270,365 / 130×90 → ×2)
  { x: 472,      y: 540,      w: 260,      h: 178 },
];

interface DpadState {
  up: boolean; down: boolean; left: boolean; right: boolean;
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

  const sceneRef = useRef<PlazaSceneAPI | null>(null);
  const pendingPlayersRef = useRef<PlazaPlayer[]>([]);
  const moveCbRef = useRef<((x: number, y: number) => void) | null>(null);
  const dmRequestCbRef = useRef<((targetSid: string) => void) | null>(null);

  const [chatInput, setChatInput] = useState("");

  const {
    onlineCount, mySocketId, pendingDM, dmRooms,
    sendMove, sendChat, sendDMRequest,
    sendDMAccept, sendDMReject, sendDMMessage, sendDMClose,
  } = usePlazaSocket({ playerCreature, sceneRef, pendingPlayersRef });

  useEffect(() => { moveCbRef.current = sendMove; }, [sendMove]);
  useEffect(() => { dmRequestCbRef.current = sendDMRequest; }, [sendDMRequest]);

  useEffect(() => {
    if (!bgmRef.current) return;
    bgmEnabled
      ? bgmRef.current.play().catch(() => {})
      : bgmRef.current.pause();
  }, [bgmEnabled]);

  // ── Phaser 초기화 ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    let mounted = true;

    const initGame = async () => {
      const Phaser = (await import("phaser")).default;
      if (!mounted) return;

      const creatureSpriteUrl = playerCreature?.sprite_url ?? null;
      const creatureImageUrl = playerCreature?.image_url ?? null;
      const creatureName = playerCreature?.name ?? "나";
      const dpad = dpadRef;

      const otherPlayers = new Map<string, Phaser.GameObjects.Container>();
      const bubbleTimers = new Map<string, Phaser.Time.TimerEvent>();
      const bubbleTexts = new Map<string | null, Phaser.GameObjects.Text>();

      class PlazaScene extends Phaser.Scene {
        private player!: Phaser.GameObjects.Container;
        private playerSprite: Phaser.GameObjects.Sprite | null = null;
        private lastDir = "down";
        private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
        private wasd!: {
          up: Phaser.Input.Keyboard.Key; down: Phaser.Input.Keyboard.Key;
          left: Phaser.Input.Keyboard.Key; right: Phaser.Input.Keyboard.Key;
        };
        private moveAccMs = 0;

        constructor() { super({ key: "PlazaScene" }); }

        preload() {
          // 맵 이미지 로드
          this.load.image("plaza_map", "/images/plaza-map.jpg");
          // 플레이어 스프라이트
          if (creatureSpriteUrl) {
            this.load.spritesheet("creature_sprite", creatureSpriteUrl, {
              frameWidth: SPRITE_FRAME_W,
              frameHeight: SPRITE_FRAME_H,
            });
          } else if (creatureImageUrl) {
            this.load.image("creature", creatureImageUrl);
          }
        }

        create() {
          // ── 맵 배경 이미지 (원본 480×480 → 960×960으로 스케일) ──
          const mapImg = this.add.image(0, 0, "plaza_map");
          mapImg.setOrigin(0, 0);
          mapImg.setDisplaySize(WORLD_W, WORLD_H);
          mapImg.setDepth(0);

          // ── 애니메이션 설정 ──
          this.setupAnimations();

          // ── 플레이어 생성 ──
          this.createPlayer();
          this.setupCamera();
          this.setupInput();

          // ── 씬 API 노출 ──
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
            showChatBubble: (sid, message) => { this.showBubble(sid, message); },
          };

          for (const p of pendingPlayersRef.current) {
            this.addOtherPlayerSprite(p.sid, p.nickname, p.image_url, p.x, p.y);
          }
          pendingPlayersRef.current = [];
        }

        private setupAnimations() {
          if (!this.textures.exists("creature_sprite")) return;
          ["down", "left", "right", "up"].forEach((dir, i) => {
            this.anims.create({
              key: `walk_${dir}`,
              frames: this.anims.generateFrameNumbers("creature_sprite", {
                start: i * 3, end: i * 3 + 2,
              }),
              frameRate: 8,
              repeat: -1,
            });
          });
        }

        private createPlayer() {
          // 경로 위 시작 위치 (맵 중앙 경로 상단부)
          this.player = this.add.container(380, 260);
          this.player.setDepth(10);

          if (this.textures.exists("creature_sprite")) {
            const sprite = this.add.sprite(0, 0, "creature_sprite", 1);
            sprite.setDisplaySize(SPRITE_DISPLAY, SPRITE_DISPLAY);
            this.playerSprite = sprite;
            this.player.add(sprite);
            sprite.play("walk_down");
          } else if (this.textures.exists("creature")) {
            const mask = this.add.graphics();
            mask.fillStyle(0xffffff, 1);
            mask.fillCircle(0, 0, PLAYER_RADIUS);
            const geoMask = mask.createGeometryMask();
            const img = this.add.image(0, 0, "creature");
            img.setDisplaySize(PLAYER_RADIUS * 2, PLAYER_RADIUS * 2);
            img.setMask(geoMask);
            const border = this.add.arc(0, 0, PLAYER_RADIUS, 0, 360, false);
            border.setStrokeStyle(3, 0x1a1a2e, 1);
            border.setFillStyle(0, 0);
            this.player.add([img, border]);
          } else {
            const circle = this.add.arc(0, 0, PLAYER_RADIUS, 0, 360, false, 0x7c6af0);
            circle.setStrokeStyle(3, 0x1a1a2e, 1);
            this.player.add(circle);
          }

          const topOffset = this.playerSprite ? SPRITE_DISPLAY / 2 : PLAYER_RADIUS;
          const tag = this.add.text(0, -topOffset - 10, creatureName, {
            fontSize: "10px", color: "#1a1a2e",
            backgroundColor: "#ffffffdd", padding: { x: 4, y: 2 },
          }).setOrigin(0.5, 1);
          this.player.add(tag);
        }

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
          const tag = this.add.text(0, -PLAYER_RADIUS - 10, name, {
            fontSize: "10px", color: "#1a1a2e",
            backgroundColor: "#ffffffdd", padding: { x: 4, y: 2 },
          }).setOrigin(0.5, 1);
          container.add(tag);
        }

        private addOtherPlayerSprite(
          sid: string, nickname: string, imageUrl: string | null, x: number, y: number,
        ) {
          const textureKey = `other_${sid}`;
          const container = this.add.container(x, y);
          container.setDepth(9);
          const doAdd = () => {
            this.addPlayerGraphics(container, imageUrl, nickname, textureKey, false);
            container.setSize(PLAYER_RADIUS * 2, PLAYER_RADIUS * 2);
            container.setInteractive({ cursor: "pointer" });
            container.on("pointerdown", () => dmRequestCbRef.current?.(sid));
            otherPlayers.set(sid, container);
          };
          if (imageUrl && !this.textures.exists(textureKey)) {
            this.load.image(textureKey, imageUrl);
            this.load.once(`filecomplete-image-${textureKey}`, doAdd);
            this.load.start();
          } else {
            doAdd();
          }
        }

        private showBubble(sid: string | null, message: string) {
          bubbleTexts.get(sid)?.destroy();
          bubbleTimers.get(sid ?? "local")?.remove();

          const target = sid ? otherPlayers.get(sid) : this.player;
          if (!target) return;

          const bubble = this.add.text(
            target.x, target.y - PLAYER_RADIUS - 30, message, {
              fontSize: "12px", color: "#1a1a2e",
              backgroundColor: "#ffffffee", padding: { x: 7, y: 3 },
            }
          ).setOrigin(0.5, 1).setDepth(20);
          bubbleTexts.set(sid, bubble);
          bubbleTimers.set(sid ?? "local", this.time.delayedCall(3000, () => {
            bubble.destroy();
            bubbleTexts.delete(sid);
            bubbleTimers.delete(sid ?? "local");
          }));
        }

        private setupCamera() {
          this.cameras.main.setBounds(0, 0, WORLD_W, WORLD_H);
          this.cameras.main.startFollow(this.player, true, 0.1, 0.1);
          this.cameras.main.setZoom(1.5); // 픽셀아트 선명하게 확대
        }

        private setupInput() {
          this.cameras.main.roundPixels = true; // 픽셀 선명도
          this.cursors = this.input.keyboard!.createCursorKeys();
          this.wasd = {
            up:    this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.W),
            down:  this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.S),
            left:  this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.A),
            right: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.D),
          };
        }

        update(_time: number, delta: number) {
          const dt = delta / 1000;
          const d = dpad.current;

          let vx = 0, vy = 0;
          if (this.cursors.left.isDown  || this.wasd.left.isDown  || d.left)  vx = -PLAYER_SPEED;
          else if (this.cursors.right.isDown || this.wasd.right.isDown || d.right) vx = PLAYER_SPEED;
          if (this.cursors.up.isDown    || this.wasd.up.isDown    || d.up)    vy = -PLAYER_SPEED;
          else if (this.cursors.down.isDown  || this.wasd.down.isDown  || d.down)  vy = PLAYER_SPEED;

          if (vx !== 0 && vy !== 0) { vx *= 0.707; vy *= 0.707; }

          let nx = this.player.x + vx * dt;
          let ny = this.player.y + vy * dt;

          // 충돌 해결 (모든 충돌 영역 확인)
          const hw = PLAYER_RADIUS;
          for (const col of COLLIDERS) {
            const overlapX = nx + hw > col.x && nx - hw < col.x + col.w;
            const overlapY = ny + hw > col.y && ny - hw < col.y + col.h;
            if (overlapX && overlapY) {
              // X축 이동만 적용했을 때 충돌 여부
              const testX = this.player.x + vx * dt;
              const testXOverlapX = testX + hw > col.x && testX - hw < col.x + col.w;
              const testXOverlapY = this.player.y + hw > col.y && this.player.y - hw < col.y + col.h;
              if (testXOverlapX && testXOverlapY) nx = this.player.x;

              // Y축 이동만 적용했을 때 충돌 여부
              const testY = this.player.y + vy * dt;
              const testYOverlapX = this.player.x + hw > col.x && this.player.x - hw < col.x + col.w;
              const testYOverlapY = testY + hw > col.y && testY - hw < col.y + col.h;
              if (testYOverlapX && testYOverlapY) ny = this.player.y;
            }
          }

          // 월드 경계
          nx = Phaser.Math.Clamp(nx, hw, WORLD_W - hw);
          ny = Phaser.Math.Clamp(ny, hw, WORLD_H - hw);
          this.player.setPosition(nx, ny);

          // 스프라이트 방향 애니메이션
          if (this.playerSprite) {
            if (vx !== 0 || vy !== 0) {
              let dir = this.lastDir;
              if (Math.abs(vx) >= Math.abs(vy)) dir = vx < 0 ? "left" : "right";
              else dir = vy < 0 ? "up" : "down";
              if (dir !== this.lastDir || !this.playerSprite.anims.isPlaying) {
                this.playerSprite.play(`walk_${dir}`, true);
                this.lastDir = dir;
              }
            } else {
              this.playerSprite.anims.stop();
              const neutral: Record<string, number> = { down: 1, left: 4, right: 7, up: 10 };
              this.playerSprite.setFrame(neutral[this.lastDir] ?? 1);
            }
          }

          // 말풍선 위치 갱신
          bubbleTexts.get(null)?.setPosition(this.player.x, this.player.y - PLAYER_RADIUS - 30);
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
        width: window.innerWidth,
        height: window.innerHeight,
        backgroundColor: "#000000",
        scene: [PlazaScene],
        scale: {
          mode: Phaser.Scale.RESIZE,
          autoCenter: Phaser.Scale.CENTER_BOTH,
        },
        // 픽셀아트 선명도 설정
        render: {
          pixelArt: true,
          antialias: false,
        },
        input: { keyboard: true },
      });

      if (!mounted) { game.destroy(true); return; }
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

  const setDpad = useCallback((key: keyof DpadState, value: boolean) => {
    dpadRef.current[key] = value;
  }, []);

  const handleChatSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const msg = chatInput.trim();
    if (!msg) return;
    sendChat(msg);
    sceneRef.current?.showChatBubble(null, msg);
    setChatInput("");
  }, [chatInput, sendChat]);

  return (
    <div className="relative w-full h-screen overflow-hidden bg-black">
      <audio ref={bgmRef} src="/bgm/plaza.mp3" loop preload="none" />
      <div ref={containerRef} className="absolute inset-0" />

      {/* 상단 HUD */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20">
        <div className="pointer-events-auto flex items-center justify-between bg-black/50 px-4 py-3 backdrop-blur-sm">
          <button type="button" onClick={onExit}
            className="flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-white/30">
            ← 나가기
          </button>
          <div className="flex flex-col items-center">
            <span className="text-sm font-bold text-white drop-shadow">포켓 광장</span>
            <span className="text-xs text-white/70">{onlineCount}명 접속 중</span>
          </div>
          <button type="button" onClick={() => onBgmToggle(!bgmEnabled)}
            className="rounded-full bg-white/20 px-3 py-1.5 text-sm text-white transition hover:bg-white/30"
            title={bgmEnabled ? "BGM 끄기" : "BGM 켜기"}>
            {bgmEnabled ? "🔊" : "🔇"}
          </button>
        </div>
      </div>

      {/* 채팅 입력 */}
      <form onSubmit={handleChatSubmit}
        className="pointer-events-auto absolute bottom-6 left-1/2 z-20 -translate-x-1/2 flex gap-2">
        <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)}
          placeholder="채팅 (Enter)" maxLength={100}
          className="w-52 rounded-full bg-black/50 px-4 py-2 text-sm text-white placeholder-white/50 outline-none backdrop-blur-sm focus:bg-black/70" />
        <button type="submit" disabled={!chatInput.trim()}
          className="rounded-full bg-white/20 px-3 py-2 text-sm text-white backdrop-blur-sm transition hover:bg-white/30 disabled:opacity-40">
          전송
        </button>
      </form>

      {/* 모바일 D-pad */}
      <div className="pointer-events-none absolute bottom-20 left-6 z-20 lg:hidden">
        <div className="pointer-events-auto relative h-[120px] w-[120px] select-none">
          {(["up","down","left","right"] as const).map((dir) => {
            const pos: Record<string, string> = {
              up:    "absolute left-1/2 top-0 -translate-x-1/2",
              down:  "absolute bottom-0 left-1/2 -translate-x-1/2",
              left:  "absolute left-0 top-1/2 -translate-y-1/2",
              right: "absolute right-0 top-1/2 -translate-y-1/2",
            };
            const label: Record<string, string> = { up:"▲", down:"▼", left:"◀", right:"▶" };
            const pad: Record<string, string> = {
              up:"px-4 py-2.5", down:"px-4 py-2.5",
              left:"px-2.5 py-4", right:"px-2.5 py-4",
            };
            return (
              <button key={dir} type="button"
                className={`${pos[dir]} ${pad[dir]} rounded-lg bg-white/60 text-lg font-bold text-gray-700 shadow backdrop-blur-sm active:bg-white/90`}
                onTouchStart={() => setDpad(dir, true)} onTouchEnd={() => setDpad(dir, false)} onTouchCancel={() => setDpad(dir, false)}
                onMouseDown={() => setDpad(dir, true)} onMouseUp={() => setDpad(dir, false)} onMouseLeave={() => setDpad(dir, false)}>
                {label[dir]}
              </button>
            );
          })}
        </div>
      </div>

      {/* 키보드 안내 */}
      <div className="pointer-events-none absolute bottom-6 right-6 z-20 hidden lg:block">
        <div className="rounded-xl bg-black/40 px-4 py-3 text-xs text-white/80 backdrop-blur-sm">
          <p className="font-semibold text-white/90">이동: WASD / 방향키</p>
          <p className="mt-0.5 text-white/60">다른 플레이어 클릭 → DM 요청</p>
        </div>
      </div>

      <DMPanel
        mySocketId={mySocketId} pendingDM={pendingDM} dmRooms={dmRooms}
        onAccept={sendDMAccept} onReject={sendDMReject}
        onSendMessage={sendDMMessage} onClose={sendDMClose}
      />
    </div>
  );
}
