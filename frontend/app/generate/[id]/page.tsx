"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useVeoPolling } from "@/hooks/useVeoPolling";
import { Button } from "@/components/ui/Button";

// 상태 텍스트 시퀀스 (지연 ms)
const STATUS_MESSAGES = [
  { text: "나만의 크리처가 태어나고 있어요...", delay: 0 },
  { text: "포켓몬의 특성을 융합하고 있어요...", delay: 10000 },
  { text: "거의 다 됐어요! 조금만 기다려주세요", delay: 25000 },
];

// 퍼레이드 포켓몬 (simeydotme ZGzrBQ 기반)
// 스프라이트 시트: /images/pokemon-sprite.png (96열×96행 스프라이트)
const PARADE_COUNT = 8;
const PARADE_POKEMONS = Array.from({ length: PARADE_COUNT }, (_, i) => ({
  key: i,
  // 각 캐릭터의 스프라이트 시트 Y 오프셋 (px)
  // 0, 96, 192, 288, 384, 480, 576, 672 ...
  yOffset: (i % 10) * -96,
  duration: 4 + Math.random() * 4,      // 4~8초
  delay: i * -0.8,                       // 엇갈린 시작
  top: 55 + Math.random() * 30,          // 화면 하단 55~85% 위치
}));

export default function GeneratePage() {
  const params = useParams();
  const router = useRouter();
  const creatureId = params.id as string;

  const [statusIdx, setStatusIdx] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const timerRefs = useRef<ReturnType<typeof setTimeout>[]>([]);

  const handleSuccess = useCallback(
    (id: string) => {
      router.push(`/result/${id}`);
    },
    [router]
  );

  const handleError = useCallback((message: string) => {
    setIsError(true);
    setErrorMessage(message);
  }, []);

  const { pollingState } = useVeoPolling({
    creatureId,
    onSuccess: handleSuccess,
    onError: handleError,
  });

  // 상태 텍스트 타이머 (0s / 10s / 25s)
  useEffect(() => {
    STATUS_MESSAGES.forEach((msg, idx) => {
      if (idx === 0) return;
      const t = setTimeout(() => setStatusIdx(idx), msg.delay);
      timerRefs.current.push(t);
    });
    // cleanup 시점에 ref.current가 바뀔 수 있으므로 캡처
    const timers = timerRefs.current;
    return () => {
      timers.forEach(clearTimeout);
    };
  }, []);

  const currentStatusText =
    pollingState === "timeout"
      ? "영상 생성이 오래 걸리고 있어요..."
      : STATUS_MESSAGES[statusIdx].text;

  return (
    /* 풀스크린 오버레이 — Header/MobileNav 위에 표시 */
    <div className="fixed inset-0 z-[100] flex flex-col overflow-hidden"
         style={{ backgroundColor: "#1D1F20" }}>

      {/* 상단 로고 (opacity 0.8) */}
      <div className="relative z-10 flex items-center justify-center pt-8 opacity-80">
        <span className="text-lg font-black tracking-widest text-white">POCKETMAN</span>
      </div>

      {/* 중앙 상태 텍스트 */}
      <div className="flex flex-1 items-center justify-center px-8 text-center">
        {isError ? (
          <div className="flex flex-col items-center gap-6">
            <p className="text-base text-white/60 leading-relaxed max-w-xs">{errorMessage}</p>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => router.push("/upload")}
                className="border-white/30 text-white/70 hover:bg-white/10"
              >
                처음으로
              </Button>
              <Button
                onClick={() => {
                  setIsError(false);
                  setErrorMessage("");
                  router.push(`/result/${creatureId}`);
                }}
              >
                결과 보기
              </Button>
            </div>
          </div>
        ) : (
          <p
            className="text-base transition-opacity duration-700"
            style={{ color: "rgba(255,255,255,0.5)" }}
            key={statusIdx}
          >
            {currentStatusText}
          </p>
        )}
      </div>

      {/* 하단 퍼레이드 */}
      <ParadeSection />
    </div>
  );
}

function ParadeSection() {
  return (
    <div className="relative h-48 w-full overflow-hidden" aria-hidden="true">
      {PARADE_POKEMONS.map((p) => (
        <div
          key={p.key}
          className="absolute"
          style={{
            top: `${p.top}%`,
            width: 80,
            height: 80,
            backgroundImage: "url('/pokemon-sprite.png')",
            backgroundPosition: `0px ${p.yOffset}px`,
            backgroundSize: "160px auto",
            imageRendering: "pixelated",
            animation: `poke-walk 0.6s steps(2) infinite, poke-move ${p.duration}s linear ${p.delay}s infinite`,
          }}
        />
      ))}
    </div>
  );
}
