"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ApiError, checkNickname, getMyCreatures, getMyProfile, updateProfile } from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import { MyCreatureItem, UserProfile, UserUpdatePayload } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Spinner";

type NicknameStatus = "idle" | "checking" | "ok" | "taken" | "error";

// ── Preview Card ─────────────────────────────────────────────────────────────

function ProfilePreviewCard({
  name,
  bio,
  imageUrl,
}: {
  name: string;
  bio: string;
  imageUrl: string | null;
}) {
  return (
    <div className="rounded-2xl shadow-deck overflow-hidden">
      <div
        className="flex min-h-[160px]"
        style={{
          backgroundColor: "#68A090",
          backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(0,0,0,0.08) 4px, rgba(0,0,0,0.08) 5px)`,
        }}
      >
        <div className="relative flex w-2/5 items-center justify-center p-4">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                "radial-gradient(circle at 50% 60%, rgba(255,255,255,0.25), transparent 70%)",
            }}
          />
          {imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl}
              alt={name}
              className="relative z-10 h-20 w-20 rounded-full object-cover drop-shadow-lg ring-2 ring-white/60"
            />
          ) : (
            <div className="relative z-10 h-20 w-20 rounded-full bg-white/20 flex items-center justify-center text-3xl">
              🥚
            </div>
          )}
        </div>
        <div
          className="flex w-3/5 flex-col justify-center gap-1.5 p-4 text-white"
          style={{ fontFamily: "'Lato', sans-serif" }}
        >
          <p className="text-xs font-bold tracking-widest opacity-70">MY CREATURE</p>
          <h2 className="text-lg font-black leading-tight truncate">{name || "닉네임"}</h2>
          {bio && <p className="text-xs opacity-70 line-clamp-2">{bio}</p>}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

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

  // Creature selection
  const [creatures, setCreatures] = useState<MyCreatureItem[]>([]);
  const [selectedCreatureId, setSelectedCreatureId] = useState<string | null>(null);

  // Preview state (synced with form inputs)
  const [previewName, setPreviewName] = useState("");
  const [previewBio, setPreviewBio] = useState("");

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
      const [p, creatureRes] = await Promise.all([getMyProfile(), getMyCreatures()]);
      setProfile(p);
      setNickname(p.nickname);
      setPreviewName(p.nickname);
      setBio(p.bio ?? "");
      setPreviewBio(p.bio ?? "");
      setCreatures(creatureRes.items);
      setSelectedCreatureId(p.avatar_creature_id ?? null);
    } catch {
      setToast({ msg: "프로필을 불러오지 못했습니다.", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  function handleNicknameChange(val: string) {
    setNickname(val);
    setPreviewName(val);
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

    const payload: UserUpdatePayload = {};
    if (trimNick && trimNick !== profile?.nickname) payload.name = trimNick;
    if (trimBio !== (profile?.bio ?? "")) payload.bio = trimBio;

    // avatar_creature_id 변경 감지 — null도 "clear" 신호로 전송
    const originalCreatureId = profile?.avatar_creature_id ?? null;
    if (selectedCreatureId !== originalCreatureId) {
      payload.avatar_creature_id = selectedCreatureId;
    }

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

  // 선택된 크리처의 image_url을 미리보기에 반영
  const selectedCreature = creatures.find((c) => c.id === selectedCreatureId) ?? null;

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

      {/* Preview Card */}
      <div className="mb-6">
        <ProfilePreviewCard
          name={previewName}
          bio={previewBio}
          imageUrl={selectedCreature?.image_url ?? null}
        />
      </div>

      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-5">
        {/* Avatar Creature Selector */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-semibold text-ink/70">대표 크리처</label>
          {creatures.length === 0 ? (
            <div className="rounded-xl border border-ink/15 bg-panel/50 p-4 text-center">
              <p className="text-sm text-ink/50">크리처를 먼저 만들어주세요</p>
              <Link
                href="/upload"
                className="mt-1 inline-block text-xs font-semibold text-point hover:underline"
              >
                크리처 만들러 가기 →
              </Link>
            </div>
          ) : (
            <div className="flex gap-2.5 overflow-x-auto pb-1">
              {/* 없음 버튼 */}
              <button
                type="button"
                onClick={() => setSelectedCreatureId(null)}
                className={`flex-shrink-0 flex flex-col items-center gap-1 rounded-xl border-2 p-2 transition
                  ${selectedCreatureId === null ? "border-point bg-point/10" : "border-ink/15 hover:border-ink/30"}`}
              >
                <div className="h-12 w-12 rounded-full bg-ink/10 flex items-center justify-center text-xl">
                  🥚
                </div>
                <span className="text-[10px] text-ink/50 w-14 text-center">없음</span>
              </button>
              {creatures.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelectedCreatureId(c.id)}
                  className={`flex-shrink-0 flex flex-col items-center gap-1 rounded-xl border-2 p-2 transition
                    ${selectedCreatureId === c.id ? "border-point bg-point/10" : "border-ink/15 hover:border-ink/30"}`}
                >
                  {c.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={c.image_url}
                      alt={c.name}
                      className="h-12 w-12 rounded-full object-cover"
                    />
                  ) : (
                    <div className="h-12 w-12 rounded-full bg-ink/10 flex items-center justify-center text-xl">
                      🥚
                    </div>
                  )}
                  <span className="text-[10px] text-ink/60 w-14 text-center truncate">
                    {c.name}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

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
            onChange={(e) => {
              setBio(e.target.value);
              setPreviewBio(e.target.value);
            }}
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
      await deleteAccount(password);
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
          disabled={!password || deleting}
          className="flex-1 rounded-xl bg-danger py-2.5 text-sm font-bold text-white hover:brightness-90 disabled:opacity-60 transition"
        >
          {deleting ? "삭제 중…" : "계정 영구 삭제"}
        </button>
        <button
          onClick={() => {
            setOpen(false);
            setError("");
          }}
          className="flex-1 rounded-xl border border-ink/15 py-2.5 text-sm font-semibold text-ink/60 hover:bg-panelSoft transition"
        >
          취소
        </button>
      </div>
    </div>
  );
}
