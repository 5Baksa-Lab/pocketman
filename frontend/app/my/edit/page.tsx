"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, checkNickname, getMyProfile, updateProfile } from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import { UserProfile } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Spinner";

type NicknameStatus = "idle" | "checking" | "ok" | "taken" | "error";

export default function EditProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Form state
  const [nickname, setNickname] = useState("");
  const [bio, setBio] = useState("");
  const [nickStatus, setNickStatus] = useState<NicknameStatus>("idle");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" }>({
    msg: "",
    type: "success",
  });

  const nickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!AuthStorage.isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void loadProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadProfile() {
    try {
      const p = await getMyProfile();
      setProfile(p);
      setNickname(p.nickname);
      setBio(p.bio ?? "");
    } catch {
      setToast({ msg: "프로필을 불러오지 못했습니다.", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  function handleNicknameChange(val: string) {
    setNickname(val);
    if (nickTimerRef.current) clearTimeout(nickTimerRef.current);

    if (!val.trim() || val.trim() === profile?.nickname) {
      setNickStatus("idle");
      return;
    }

    setNickStatus("checking");
    nickTimerRef.current = setTimeout(async () => {
      try {
        const res = await checkNickname(val.trim());
        setNickStatus(res.available ? "ok" : "taken");
      } catch {
        setNickStatus("error");
      }
    }, 500);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (nickStatus === "taken") return;

    const trimNick = nickname.trim();
    const trimBio = bio.trim();

    const payload: Record<string, unknown> = {};
    if (trimNick && trimNick !== profile?.nickname) payload.nickname = trimNick;
    if (trimBio !== (profile?.bio ?? "")) payload.bio = trimBio;

    if (Object.keys(payload).length === 0) {
      setToast({ msg: "변경 사항이 없습니다.", type: "error" });
      return;
    }

    setSaving(true);
    try {
      await updateProfile(payload);
      setToast({ msg: "프로필이 저장되었습니다.", type: "success" });
      setTimeout(() => router.push("/my"), 1200);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "저장에 실패했습니다.";
      setToast({ msg, type: "error" });
    } finally {
      setSaving(false);
    }
  }

  const nickHint: Record<NicknameStatus, string> = {
    idle: "",
    checking: "확인 중…",
    ok: "사용 가능한 닉네임입니다.",
    taken: "이미 사용 중인 닉네임입니다.",
    error: "확인에 실패했습니다.",
  };
  const nickHintColor: Record<NicknameStatus, string> = {
    idle: "text-ink/40",
    checking: "text-ink/40",
    ok: "text-ok",
    taken: "text-danger",
    error: "text-warn",
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <button
        onClick={() => router.back()}
        className="mb-6 flex items-center gap-1.5 text-sm text-ink/50 hover:text-ink/80 transition"
      >
        ← 뒤로
      </button>

      <h1 className="mb-6 text-2xl font-black text-ink">프로필 편집</h1>

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
        {/* Nickname */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-semibold text-ink/70">닉네임</label>
          <input
            value={nickname}
            onChange={(e) => handleNicknameChange(e.target.value)}
            maxLength={20}
            required
            className="rounded-xl border border-ink/15 bg-panel px-4 py-2.5 text-sm text-ink outline-none focus:border-point focus:ring-2 focus:ring-point/20 transition"
            placeholder="닉네임"
          />
          {nickHint[nickStatus] && (
            <p className={`text-xs ${nickHintColor[nickStatus]}`}>{nickHint[nickStatus]}</p>
          )}
        </div>

        {/* Bio */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-semibold text-ink/70">
            한 줄 소개
            <span className="ml-1 font-normal text-ink/30">({bio.length}/100)</span>
          </label>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={100}
            rows={3}
            className="resize-none rounded-xl border border-ink/15 bg-panel px-4 py-2.5 text-sm text-ink outline-none focus:border-point focus:ring-2 focus:ring-point/20 transition"
            placeholder="나를 한 줄로 표현해보세요."
          />
        </div>

        <Button
          type="submit"
          size="lg"
          disabled={saving || nickStatus === "taken" || nickStatus === "checking"}
          className="mt-2 w-full"
        >
          {saving ? "저장 중…" : "저장하기"}
        </Button>
      </form>

      {/* Danger zone */}
      <div className="mt-12 rounded-2xl border border-danger/20 bg-danger/5 p-5">
        <h2 className="mb-1 text-sm font-bold text-danger">위험 구역</h2>
        <p className="mb-3 text-xs text-ink/50">
          계정을 삭제하면 모든 크리처와 데이터가 영구 삭제됩니다.
        </p>
        <DeleteAccountSection />
      </div>
    </div>
  );
}

function DeleteAccountSection() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  async function handleDelete() {
    setDeleting(true);
    setError("");
    try {
      const { deleteAccount } = await import("@/lib/api");
      await deleteAccount(password || undefined);
      AuthStorage.clear();
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-sm font-semibold text-danger hover:underline"
      >
        계정 삭제
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-ink/70">
        확인을 위해 현재 비밀번호를 입력하세요 (소셜 계정은 생략 가능).
      </p>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="현재 비밀번호"
        className="rounded-xl border border-danger/30 bg-white px-4 py-2.5 text-sm text-ink outline-none focus:border-danger focus:ring-2 focus:ring-danger/20 transition"
      />
      {error && <p className="text-xs text-danger">{error}</p>}
      <div className="flex gap-2">
        <button
          onClick={() => void handleDelete()}
          disabled={deleting}
          className="flex-1 rounded-xl bg-danger py-2.5 text-sm font-bold text-white hover:brightness-90 disabled:opacity-60 transition"
        >
          {deleting ? "삭제 중…" : "계정 영구 삭제"}
        </button>
        <button
          onClick={() => { setOpen(false); setError(""); }}
          className="flex-1 rounded-xl border border-ink/15 py-2.5 text-sm font-semibold text-ink/60 hover:bg-panelSoft transition"
        >
          취소
        </button>
      </div>
    </div>
  );
}
