"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import confetti from "canvas-confetti";
import { getCreatureDetail, patchCreature } from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import type { CreatureDetail } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Toast } from "@/components/ui/Toast";
import InlineEditableName from "@/components/features/result/InlineEditableName";
import AuthGateModal from "@/components/features/result/AuthGateModal";

type PageState = "loading" | "ready" | "error";
type ActionPending = "plaza" | "save" | null;

export default function ResultPage() {
  const params = useParams();
  const router = useRouter();
  const creatureId = params.id as string;

  const [creature, setCreature] = useState<CreatureDetail | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [pageState, setPageState] = useState<PageState>("loading");
  const [errorMsg, setErrorMsg] = useState("");

  // 등장 애니메이션 단계
  const [showBg, setShowBg] = useState(false);
  const [showCard, setShowCard] = useState(false);
  const [showMeta, setShowMeta] = useState(false);
  const [showButtons, setShowButtons] = useState(false);

  // 상호작용 상태
  const [actionPending, setActionPending] = useState<ActionPending>(null);
  const [authGateOpen, setAuthGateOpen] = useState(false);
  const [toastMsg, setToastMsg] = useState("");
  const [toastType, setToastType] = useState<"error" | "success" | "info">("info");
  const confettiFired = useRef(false);

  const showToast = useCallback((msg: string, type: "error" | "success" | "info" = "info") => {
    setToastMsg(msg);
    setToastType(type);
  }, []);

  // 데이터 로딩
  useEffect(() => {
    async function load() {
      try {
        const data = await getCreatureDetail(creatureId);
        setCreature(data);
        setPageState("ready");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "크리처를 불러올 수 없습니다.");
        setPageState("error");
      }
    }
    void load();
  }, [creatureId]);

  // 등장 애니메이션 시퀀스 (ready 후 실행)
  useEffect(() => {
    if (pageState !== "ready") return;

    const timers = [
      setTimeout(() => setShowBg(true), 0),
      setTimeout(() => setShowCard(true), 300),
      setTimeout(() => {
        if (!confettiFired.current) {
          confettiFired.current = true;
          confetti({
            particleCount: 100,
            spread: 70,
            colors: ["#f15946", "#009087", "#FFCE00"],
            origin: { y: 0.4 },
          });
        }
      }, 800),
      setTimeout(() => setShowMeta(true), 1200),
      setTimeout(() => setShowButtons(true), 1800),
    ];

    return () => timers.forEach(clearTimeout);
  }, [pageState]);

  // 버튼 액션
  async function handleShare() {
    if (!creature) return;
    if (!creature.is_public) {
      showToast("광장에 공개 후 공유할 수 있어요.", "info");
      return;
    }
    const url = `${window.location.origin}/result/${creatureId}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: creature.name, url });
      } catch { /* 취소 */ }
    } else {
      await navigator.clipboard.writeText(url);
      showToast("링크가 복사됐어요!", "success");
    }
  }

  async function handlePlaza() {
    if (!AuthStorage.isLoggedIn()) {
      setActionPending("plaza");
      setAuthGateOpen(true);
      return;
    }
    try {
      setActionPending("plaza");
      await patchCreature(creatureId, { is_public: true });
      setCreature((prev) => prev ? { ...prev, is_public: true } : prev);
      showToast("광장에 공개됐어요! 🎉", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "공개 전환에 실패했습니다.", "error");
    } finally {
      setActionPending(null);
    }
  }

  function handleSave() {
    if (!AuthStorage.isLoggedIn()) {
      setActionPending("save");
      setAuthGateOpen(true);
      return;
    }
    if (creature?.image_url) {
      window.open(creature.image_url, "_blank");
    } else {
      showToast("저장할 이미지가 없습니다.", "error");
    }
  }

  if (pageState === "loading") {
    return (
      <div className="flex min-h-[calc(100vh-72px)] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (pageState === "error" || !creature) {
    return (
      <div className="flex min-h-[calc(100vh-72px)] flex-col items-center justify-center gap-4 px-4 text-center">
        <p className="text-ink/60">{errorMsg || "크리처를 찾을 수 없습니다."}</p>
        <Button onClick={() => router.push("/upload")}>처음으로 돌아가기</Button>
      </div>
    );
  }

  // 타입 기반 배경 색상 (davidkpiano 카드 디자인)
  const TYPE_COLORS: Record<string, string> = {
    노말: "#A8A878", 불꽃: "#F08030", 물: "#6890F0", 풀: "#78C850",
    전기: "#F8D030", 얼음: "#98D8D8", 격투: "#C03028", 독: "#A040A0",
    땅: "#E0C068", 비행: "#A890F0", 에스퍼: "#F85888", 벌레: "#A8B820",
    바위: "#B8A038", 고스트: "#705898", 드래곤: "#7038F8", 악: "#705848",
    강철: "#B8B8D0", 페어리: "#EE99AC",
  };
  const bgColor = TYPE_COLORS[creature.primary_type ?? ""] ?? "#68A090";

  function toggleVideo() {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      void videoRef.current.play();
      setVideoPlaying(true);
    } else {
      videoRef.current.pause();
      setVideoPlaying(false);
    }
  }

  return (
    <div
      className="min-h-[calc(100vh-72px)] transition-colors duration-700"
      style={{ background: showBg ? bgColor : "var(--color-bg)" }}
    >
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-4 left-1/2 z-[300] -translate-x-1/2 w-[90vw] max-w-sm">
          <Toast message={toastMsg} type={toastType} onClose={() => setToastMsg("")} />
        </div>
      )}

      {/* AuthGate 모달 */}
      <AuthGateModal
        open={authGateOpen}
        onClose={() => { setAuthGateOpen(false); setActionPending(null); }}
        nextPath={`/result/${creatureId}`}
      />

      <div className="mx-auto max-w-4xl px-4 py-10">
        {/* 카드 */}
        <div
          className="overflow-hidden rounded-2xl shadow-deck transition-all duration-700"
          style={{
            opacity: showCard ? 1 : 0,
            transform: showCard ? "scale(1) translateY(0)" : "scale(0.92) translateY(16px)",
            backgroundImage: `
              repeating-linear-gradient(
                45deg,
                transparent, transparent 4px,
                rgba(0,0,0,0.08) 4px, rgba(0,0,0,0.08) 5px
              )
            `,
            backgroundColor: bgColor,
          }}
        >
          <div className="flex flex-col md:flex-row">
            {/* 좌측: 이미지/영상 */}
            <div className="relative flex w-full items-center justify-center p-8 md:w-2/5">
              <div
                className="absolute inset-0 pointer-events-none"
                style={{
                  background:
                    "radial-gradient(circle at 50% 60%, rgba(255,255,255,0.25), transparent 70%)",
                }}
              />
              {creature.video_url ? (
                /* click-to-play — ▶ 오버레이, 클릭 시 재생/일시정지 */
                <button
                  type="button"
                  aria-label={videoPlaying ? "영상 일시정지" : "영상 재생"}
                  className="relative z-10 cursor-pointer bg-transparent border-0 p-0"
                  onClick={toggleVideo}
                >
                  <video
                    ref={videoRef}
                    src={creature.video_url}
                    className="h-48 w-48 rounded-xl object-cover drop-shadow-xl md:h-56 md:w-56"
                    playsInline
                    loop
                    onPlay={() => setVideoPlaying(true)}
                    onPause={() => setVideoPlaying(false)}
                  />
                  {/* ▶ 아이콘 오버레이 — 재생 중에는 숨김 */}
                  {!videoPlaying && (
                    <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-black/30">
                      <span className="text-4xl text-white drop-shadow-lg">▶</span>
                    </div>
                  )}
                </button>
              ) : creature.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={creature.image_url}
                  alt={creature.name}
                  className="relative z-10 h-48 w-48 rounded-xl object-cover drop-shadow-xl md:h-56 md:w-56"
                />
              ) : (
                <div className="relative z-10 flex h-48 w-48 items-center justify-center rounded-xl bg-white/20 text-6xl md:h-56 md:w-56">
                  🥚
                </div>
              )}
            </div>

            {/* 우측: 정보 */}
            <div
              className="flex w-full flex-col justify-center gap-3 p-8 text-white md:w-3/5"
              style={{ fontFamily: "'Lato', sans-serif" }}
            >
              <p className="text-[11px] font-bold tracking-widest opacity-70">
                ◉ #{String(creature.matched_pokemon_id).padStart(3, "0")}
              </p>

              <InlineEditableName
                creatureId={creatureId}
                initialName={creature.name}
                onSaved={(n) => setCreature((prev) => prev ? { ...prev, name: n } : prev)}
              />

              <p className="text-xs opacity-60">
                닮은 포켓몬: {creature.matched_pokemon_name_kr || "-"}&nbsp;
                ({(creature.similarity_score * 100).toFixed(1)}%)
              </p>

              {creature.story && (
                <p
                  className="text-sm leading-relaxed mt-1 transition-opacity duration-700"
                  style={{ opacity: showMeta ? 0.8 : 0 }}
                >
                  {creature.story}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* 액션 버튼 */}
        <div
          className="mt-6 flex flex-wrap justify-center gap-3 transition-all duration-700"
          style={{
            opacity: showButtons ? 1 : 0,
            transform: showButtons ? "none" : "translateY(12px)",
          }}
        >
          <Button variant="secondary" onClick={() => void handleShare()}>
            📤 공유하기
          </Button>
          <Button
            variant={creature.is_public ? "ghost" : "primary"}
            disabled={creature.is_public || actionPending === "plaza"}
            onClick={() => void handlePlaza()}
          >
            {creature.is_public ? "🌍 광장 공개 중" : "🌍 광장에 올리기"}
          </Button>
          <Button variant="secondary" disabled={actionPending === "save"} onClick={handleSave}>
            💾 저장하기
          </Button>
          <Button variant="ghost" onClick={() => router.push("/upload")}>
            🔄 다시 만들기
          </Button>
        </div>
      </div>
    </div>
  );
}
