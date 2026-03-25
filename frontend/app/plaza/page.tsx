"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getMyCreatures } from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import type { MyCreatureItem } from "@/lib/types";

// Phaser는 SSR 불가 → 클라이언트 전용 동적 import
const PhaserPlaza = dynamic(
  () => import("@/components/features/plaza/PhaserPlaza"),
  {
    ssr: false,
    loading: () => <PlazaLoadingScreen message="광장을 불러오는 중..." />,
  }
);

function PlazaLoadingScreen({ message }: { message: string }) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#e8f4f0]">
      <div className="mb-6 text-5xl">🏞️</div>
      <p className="text-lg font-semibold text-ink/80">{message}</p>
      <div className="mt-4 flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-bounce rounded-full bg-point"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}

type Status = "checking" | "ready" | "redirecting";

export default function PlazaPage() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("checking");
  const [playerCreature, setPlayerCreature] = useState<MyCreatureItem | null>(null);
  const [bgmEnabled, setBgmEnabled] = useState(false);

  useEffect(() => {
    // BGM 설정 복원
    const savedBgm = typeof window !== "undefined" ? localStorage.getItem("plaza_bgm") : null;
    setBgmEnabled(savedBgm === "on");

    const checkAndLoad = async () => {
      // 비로그인 → /upload
      if (!AuthStorage.isLoggedIn()) {
        setStatus("redirecting");
        router.push("/upload");
        return;
      }

      try {
        const result = await getMyCreatures();

        // 크리처 없음 → /upload
        if (result.items.length === 0) {
          setStatus("redirecting");
          router.push("/upload");
          return;
        }

        // 공개 크리처 우선, 없으면 첫 번째 크리처
        const creature =
          result.items.find((c) => c.is_public) ?? result.items[0];
        setPlayerCreature(creature);
        setStatus("ready");
      } catch {
        // API 오류 → 크리처 확인 불가 → /upload로 이동
        setStatus("redirecting");
        router.push("/upload");
      }
    };

    void checkAndLoad();
  }, [router]);

  const handleBgmToggle = (v: boolean) => {
    setBgmEnabled(v);
    localStorage.setItem("plaza_bgm", v ? "on" : "off");
  };

  const handleExit = () => {
    router.push("/");
  };

  if (status === "checking") {
    return <PlazaLoadingScreen message="입장 확인 중..." />;
  }

  if (status === "redirecting") {
    return <PlazaLoadingScreen message="크리처 생성 페이지로 이동 중..." />;
  }

  return (
    // 전체 화면 오버레이 (Header/MobileNav 위에 렌더링)
    <div className="fixed inset-0 z-50">
      <PhaserPlaza
        playerCreature={playerCreature}
        bgmEnabled={bgmEnabled}
        onBgmToggle={handleBgmToggle}
        onExit={handleExit}
      />
    </div>
  );
}
