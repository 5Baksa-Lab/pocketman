"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, changePassword } from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";

type Strength = "weak" | "fair" | "strong";

function getStrength(pw: string): Strength {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 2) return "weak";
  if (score <= 3) return "fair";
  return "strong";
}

const strengthLabel: Record<Strength, string> = {
  weak: "약함",
  fair: "보통",
  strong: "강함",
};
const strengthColor: Record<Strength, string> = {
  weak: "bg-danger",
  fair: "bg-warn",
  strong: "bg-ok",
};
const strengthWidth: Record<Strength, string> = {
  weak: "w-1/3",
  fair: "w-2/3",
  strong: "w-full",
};

export default function PasswordPage() {
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" }>({
    msg: "",
    type: "success",
  });

  const strength = next ? getStrength(next) : null;
  const mismatch = confirm && next !== confirm;
  const canSubmit =
    current.trim() &&
    next.trim().length >= 8 &&
    next === confirm &&
    strength !== "weak";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setSaving(true);
    try {
      await changePassword({ current_password: current, new_password: next });
      setToast({ msg: "비밀번호가 변경되었습니다. 다시 로그인해주세요.", type: "success" });
      setTimeout(() => {
        AuthStorage.clear();
        router.replace("/login");
      }, 1800);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "비밀번호 변경에 실패했습니다.";
      setToast({ msg, type: "error" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <button
        onClick={() => router.back()}
        className="mb-6 flex items-center gap-1.5 text-sm text-ink/50 hover:text-ink/80 transition"
      >
        ← 뒤로
      </button>

      <h1 className="mb-2 text-2xl font-black text-ink">비밀번호 변경</h1>
      <p className="mb-7 text-sm text-ink/50">변경 후 자동 로그아웃됩니다.</p>

      {toast.msg && (
        <div className="mb-5">
          <Toast
            message={toast.msg}
            type={toast.type}
            onClose={() => setToast((p) => ({ ...p, msg: "" }))}
          />
        </div>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-5">
        {/* Current password */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-semibold text-ink/70">현재 비밀번호</label>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
            autoComplete="current-password"
            className="rounded-xl border border-ink/15 bg-panel px-4 py-2.5 text-sm text-ink outline-none focus:border-point focus:ring-2 focus:ring-point/20 transition"
            placeholder="••••••••"
          />
        </div>

        {/* New password */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-semibold text-ink/70">새 비밀번호</label>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            className="rounded-xl border border-ink/15 bg-panel px-4 py-2.5 text-sm text-ink outline-none focus:border-point focus:ring-2 focus:ring-point/20 transition"
            placeholder="8자 이상"
          />
          {/* Strength bar */}
          {strength && (
            <div className="flex flex-col gap-1">
              <div className="h-1.5 rounded-full bg-ink/10 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${strengthColor[strength]} ${strengthWidth[strength]}`}
                />
              </div>
              <p
                className={`text-xs font-semibold ${
                  strength === "weak"
                    ? "text-danger"
                    : strength === "fair"
                    ? "text-warn"
                    : "text-ok"
                }`}
              >
                강도: {strengthLabel[strength]}
              </p>
            </div>
          )}
        </div>

        {/* Confirm password */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-semibold text-ink/70">새 비밀번호 확인</label>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            autoComplete="new-password"
            className={`rounded-xl border px-4 py-2.5 text-sm text-ink outline-none transition bg-panel ${
              mismatch
                ? "border-danger focus:border-danger focus:ring-2 focus:ring-danger/20"
                : "border-ink/15 focus:border-point focus:ring-2 focus:ring-point/20"
            }`}
            placeholder="••••••••"
          />
          {mismatch && <p className="text-xs text-danger">비밀번호가 일치하지 않습니다.</p>}
        </div>

        <Button
          type="submit"
          size="lg"
          disabled={saving || !canSubmit}
          className="mt-2 w-full"
        >
          {saving ? "변경 중…" : "비밀번호 변경"}
        </Button>
      </form>
    </div>
  );
}
