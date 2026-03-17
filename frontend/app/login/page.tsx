"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { login } from "@/lib/api";
import { getSafeNextPath } from "@/lib/utils";
import { AuthStorage } from "@/lib/storage";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";
import PaletteTownScene from "@/components/features/auth/PaletteTownScene";
import PokemonBrandPanel from "@/components/features/auth/PokemonBrandPanel";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}

type FormState = "idle" | "loading" | "error";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = getSafeNextPath(searchParams.get("next"));

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  // 이미 로그인 상태면 /upload로 이동
  useEffect(() => {
    if (AuthStorage.isLoggedIn()) {
      router.replace("/upload");
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (formState === "loading") return;

    setFormState("loading");
    setErrorMsg("");

    try {
      const result = await login({ email, password });
      AuthStorage.saveToken(result.access_token);
      AuthStorage.saveUser(result.user);
      router.replace(nextPath);
    } catch (err) {
      setFormState("error");
      setErrorMsg(err instanceof Error ? err.message : "로그인에 실패했습니다.");
    }
  }

  const formContent = (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
      <div>
        <label className="mb-1 block text-xs font-semibold text-ink/70">이메일</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          placeholder="이메일을 입력하세요"
          className="w-full rounded-xl border border-ink/15 bg-base px-4 py-2.5 text-sm
                     outline-none focus:border-point focus:ring-2 focus:ring-point/20"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-semibold text-ink/70">비밀번호</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
          placeholder="비밀번호를 입력하세요"
          className="w-full rounded-xl border border-ink/15 bg-base px-4 py-2.5 text-sm
                     outline-none focus:border-point focus:ring-2 focus:ring-point/20"
        />
      </div>

      {errorMsg && (
        <Toast message={errorMsg} type="error" onClose={() => setErrorMsg("")} />
      )}

      <Button type="submit" className="w-full mt-1" disabled={formState === "loading"}>
        {formState === "loading" ? "로그인 중..." : "로그인"}
      </Button>

      <p className="text-center text-xs text-ink/50">
        계정이 없으신가요?{" "}
        <a
          href={`/signup${nextPath !== "/upload" ? `?next=${encodeURIComponent(nextPath)}` : ""}`}
          className="font-semibold text-point hover:underline"
        >
          회원가입
        </a>
      </p>
    </form>
  );

  return (
    <>
      {/* Desktop (lg+): 50/50 분할 */}
      <div className="hidden lg:flex min-h-[calc(100vh-72px)]">
        {/* 좌측 브랜딩 */}
        <div className="w-1/2">
          <PokemonBrandPanel />
        </div>

        {/* 우측 로그인 폼 */}
        <div className="flex w-1/2 items-center justify-center bg-base px-12">
          <div className="w-full max-w-sm">
            <h1 className="mb-1 text-2xl font-black text-ink">로그인</h1>
            <p className="mb-8 text-sm text-ink/50">포켓맨에 오신 것을 환영해요</p>
            {formContent}
          </div>
        </div>
      </div>

      {/* Mobile: 팔레트 타운 + 슬라이드업 카드 */}
      <div className="flex lg:hidden min-h-[calc(100vh-72px)] flex-col">
        {/* 상단 일러스트 (55%) */}
        <div className="flex-[55]">
          <PaletteTownScene />
        </div>

        {/* 하단 폼 카드 (45%) — 슬라이드업 */}
        <div className="flex-[45] animate-slide-up rounded-t-3xl bg-base px-6 py-8 shadow-deck">
          <h1 className="mb-1 text-xl font-black text-ink">로그인</h1>
          <p className="mb-6 text-sm text-ink/50">포켓맨에 오신 것을 환영해요</p>
          {formContent}
        </div>
      </div>
    </>
  );
}
