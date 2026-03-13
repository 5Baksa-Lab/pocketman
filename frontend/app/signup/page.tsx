"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, register } from "@/lib/api";
import { getSafeNextPath } from "@/lib/utils";
import { AuthStorage } from "@/lib/storage";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";
import ProgressBar from "@/components/ui/ProgressBar";
import PaletteTownScene from "@/components/features/auth/PaletteTownScene";
import PokemonBrandPanel from "@/components/features/auth/PokemonBrandPanel";

export default function SignupPage() {
  return (
    <Suspense>
      <SignupContent />
    </Suspense>
  );
}

type FormState = "idle" | "submitting" | "duplicateEmail" | "error";

function getPasswordStrength(pw: string): { label: string; value: number; colorClass: string } {
  if (pw.length === 0) return { label: "", value: 0, colorClass: "bg-danger" };
  const hasLetter = /[a-zA-Z]/.test(pw);
  const hasNumber = /[0-9]/.test(pw);
  const isLong = pw.length >= 12;

  if (isLong && hasLetter && hasNumber) {
    return { label: "강함", value: 1, colorClass: "bg-ok" };
  }
  if (pw.length >= 8 && hasLetter && hasNumber) {
    return { label: "보통", value: 0.66, colorClass: "bg-warn" };
  }
  return { label: "약함", value: 0.33, colorClass: "bg-danger" };
}

function SignupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = getSafeNextPath(searchParams.get("next"));

  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const pwStrength = getPasswordStrength(password);
  const pwMismatch = confirmPassword.length > 0 && password !== confirmPassword;

  // 이미 로그인 상태면 /upload로 이동
  useEffect(() => {
    if (AuthStorage.isLoggedIn()) {
      router.replace("/upload");
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (formState === "submitting") return;
    if (pwMismatch) {
      setErrorMsg("비밀번호가 일치하지 않아요.");
      return;
    }

    setFormState("submitting");
    setErrorMsg("");

    try {
      const result = await register({ nickname, email, password });
      AuthStorage.saveToken(result.access_token);
      AuthStorage.saveUser(result.user);
      router.replace(nextPath);
    } catch (err) {
      const isConflict = err instanceof ApiError && err.code === "EMAIL_ALREADY_EXISTS";
      if (isConflict) {
        setFormState("duplicateEmail");
        setErrorMsg("이미 사용 중인 이메일이에요. 로그인해주세요.");
      } else {
        setFormState("error");
        setErrorMsg(err instanceof Error ? err.message : "회원가입에 실패했습니다.");
      }
    }
  }

  const formContent = (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-3.5">
      <div>
        <label className="mb-1 block text-xs font-semibold text-ink/70">닉네임</label>
        <input
          type="text"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          required
          minLength={2}
          maxLength={50}
          placeholder="2~50자"
          className="w-full rounded-xl border border-ink/15 bg-base px-4 py-2.5 text-sm
                     outline-none focus:border-point focus:ring-2 focus:ring-point/20"
        />
      </div>
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
          minLength={8}
          autoComplete="new-password"
          placeholder="8자 이상"
          className="w-full rounded-xl border border-ink/15 bg-base px-4 py-2.5 text-sm
                     outline-none focus:border-point focus:ring-2 focus:ring-point/20"
        />
        {password.length > 0 && (
          <div className="mt-1.5 flex items-center gap-2">
            <ProgressBar value={pwStrength.value} colorClass={pwStrength.colorClass} className="flex-1" />
            <span className="text-[10px] font-semibold text-ink/50 w-6">{pwStrength.label}</span>
          </div>
        )}
      </div>
      <div>
        <label className="mb-1 block text-xs font-semibold text-ink/70">비밀번호 확인</label>
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          autoComplete="new-password"
          placeholder="비밀번호를 다시 입력하세요"
          className={`w-full rounded-xl border px-4 py-2.5 text-sm outline-none
                      focus:ring-2 bg-base
                      ${pwMismatch
                        ? "border-danger focus:border-danger focus:ring-danger/20"
                        : "border-ink/15 focus:border-point focus:ring-point/20"
                      }`}
        />
        {pwMismatch && (
          <p className="mt-1 text-[11px] text-danger">비밀번호가 일치하지 않아요.</p>
        )}
      </div>

      {errorMsg && (
        <Toast
          message={errorMsg}
          type={formState === "duplicateEmail" ? "info" : "error"}
          onClose={() => setErrorMsg("")}
        />
      )}

      <Button
        type="submit"
        className="w-full mt-1"
        disabled={formState === "submitting" || pwMismatch}
      >
        {formState === "submitting" ? "가입 중..." : "회원가입"}
      </Button>

      <p className="text-center text-xs text-ink/50">
        이미 계정이 있으신가요?{" "}
        <a
          href={`/login${nextPath !== "/upload" ? `?next=${encodeURIComponent(nextPath)}` : ""}`}
          className="font-semibold text-point hover:underline"
        >
          로그인
        </a>
      </p>
    </form>
  );

  return (
    <>
      {/* Desktop (lg+): 50/50 분할 */}
      <div className="hidden lg:flex min-h-[calc(100vh-72px)]">
        <div className="w-1/2">
          <PokemonBrandPanel />
        </div>
        <div className="flex w-1/2 items-center justify-center bg-base px-12">
          <div className="w-full max-w-sm">
            <h1 className="mb-1 text-2xl font-black text-ink">회원가입</h1>
            <p className="mb-8 text-sm text-ink/50">나만의 크리처를 저장하고 공유해보세요</p>
            {formContent}
          </div>
        </div>
      </div>

      {/* Mobile: 팔레트 타운 + 슬라이드업 카드 */}
      <div className="flex lg:hidden min-h-[calc(100vh-72px)] flex-col">
        <div className="flex-[45]">
          <PaletteTownScene />
        </div>
        <div className="flex-[55] animate-slide-up rounded-t-3xl bg-base px-6 py-8 shadow-deck overflow-y-auto">
          <h1 className="mb-1 text-xl font-black text-ink">회원가입</h1>
          <p className="mb-6 text-sm text-ink/50">나만의 크리처를 저장하고 공유해보세요</p>
          {formContent}
        </div>
      </div>
    </>
  );
}
