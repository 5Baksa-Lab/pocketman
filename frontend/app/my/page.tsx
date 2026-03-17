"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  deleteAccount,
  deleteCreature,
  getLikedCreatures,
  getMyCreatures,
  getMyProfile,
  updateProfile,
} from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import { MyCreatureItem, UserProfile } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Toast } from "@/components/ui/Toast";
import Modal from "@/components/ui/Modal";

type Tab = "my" | "liked";

// ── 다크모드 훅 ────────────────────────────────────────────────────────────────
function useDarkMode() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    const saved = localStorage.getItem("theme");
    if (saved) return saved === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  return { dark, setDark };
}

// ── 글자 크기 훅 ────────────────────────────────────────────────────────────────
const FONT_SIZES = [14, 16, 18] as const;
type FontSize = (typeof FONT_SIZES)[number];

function useFontSize() {
  const [size, setSize] = useState<FontSize>(() => {
    if (typeof window === "undefined") return 16;
    const saved = localStorage.getItem("font_size");
    return (saved ? Number(saved) : 16) as FontSize;
  });

  useEffect(() => {
    document.documentElement.style.fontSize = `${size}px`;
    localStorage.setItem("font_size", String(size));
  }, [size]);

  return { size, setSize };
}

function CreatureCard({
  item,
  onDelete,
  showDelete,
}: {
  item: MyCreatureItem;
  onDelete: (id: string) => void;
  showDelete: boolean;
}) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteCreature(item.id);
      onDelete(item.id);
    } catch {
      setDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <div className="group relative rounded-xl overflow-hidden bg-panel border border-ink/10 hover:border-point/40 transition">
      <Link href={`/creatures/${item.id}`}>
        <div className="aspect-square bg-panelSoft relative overflow-hidden">
          {item.image_url ? (
            <Image
              src={item.image_url}
              alt={item.name}
              fill
              className="object-cover group-hover:scale-105 transition duration-300"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-4xl opacity-30">
              ?
            </div>
          )}
          {!item.is_public && (
            <span className="absolute top-2 left-2 rounded-full bg-black/50 px-2 py-0.5 text-[10px] text-white font-semibold">
              비공개
            </span>
          )}
        </div>
        <div className="p-2.5">
          <p className="text-sm font-bold text-ink truncate">{item.name}</p>
          {item.matched_pokemon_name_kr && (
            <p className="text-[11px] text-ink/50 truncate">{item.matched_pokemon_name_kr}</p>
          )}
        </div>
      </Link>

      {showDelete && (
        <div className="absolute top-2 right-2">
          {confirming ? (
            <div className="flex gap-1">
              <button
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="rounded-full bg-danger text-white text-[10px] px-2 py-0.5 font-semibold hover:brightness-90 transition disabled:opacity-60"
              >
                {deleting ? "…" : "삭제"}
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="rounded-full bg-black/40 text-white text-[10px] px-2 py-0.5 font-semibold hover:bg-black/60 transition"
              >
                취소
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirming(true)}
              className="rounded-full bg-black/40 text-white text-[11px] px-2 py-0.5 font-semibold opacity-0 group-hover:opacity-100 hover:bg-danger/80 transition"
            >
              삭제
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function MyPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [tab, setTab] = useState<Tab>("my");
  const [myItems, setMyItems] = useState<MyCreatureItem[]>([]);
  const [likedItems, setLikedItems] = useState<MyCreatureItem[]>([]);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [loadingItems, setLoadingItems] = useState(false);
  const [toast, setToast] = useState("");
  const [toastType, setToastType] = useState<"error" | "success">("error");

  // 설정
  const { dark, setDark } = useDarkMode();
  const { size, setSize } = useFontSize();
  const darkDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fontDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 회원탈퇴 상태
  const [deleteStep, setDeleteStep] = useState<0 | 1 | 2>(0);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!AuthStorage.isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void loadProfile();
    void loadMyCreatures();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (tab === "liked" && likedItems.length === 0) {
      void loadLikedCreatures();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function loadProfile() {
    try {
      const p = await getMyProfile();
      setProfile(p);
    } catch {
      setToast("프로필을 불러오지 못했습니다.");
    } finally {
      setLoadingProfile(false);
    }
  }

  async function loadMyCreatures() {
    setLoadingItems(true);
    try {
      const res = await getMyCreatures();
      setMyItems(res.items);
    } catch {
      setToast("크리처 목록을 불러오지 못했습니다.");
    } finally {
      setLoadingItems(false);
    }
  }

  async function loadLikedCreatures() {
    setLoadingItems(true);
    try {
      const res = await getLikedCreatures();
      setLikedItems(res.items);
    } catch {
      setToast("좋아요한 크리처 목록을 불러오지 못했습니다.");
    } finally {
      setLoadingItems(false);
    }
  }

  function handleDelete(id: string) {
    setMyItems((prev) => prev.filter((x) => x.id !== id));
  }

  function handleLogout() {
    AuthStorage.clear();
    router.replace("/");
  }

  function handleDarkToggle(v: boolean) {
    setDark(v);
    if (darkDebounceRef.current) clearTimeout(darkDebounceRef.current);
    darkDebounceRef.current = setTimeout(() => {
      void updateProfile({ dark_mode: v }).catch(() => {
        setToast("다크 모드 설정 저장에 실패했습니다.");
        setToastType("error");
      });
    }, 500);
  }

  function handleFontSize(v: FontSize) {
    setSize(v);
    if (fontDebounceRef.current) clearTimeout(fontDebounceRef.current);
    fontDebounceRef.current = setTimeout(() => {
      void updateProfile({ font_size: v }).catch(() => {
        setToast("글자 크기 설정 저장에 실패했습니다.");
        setToastType("error");
      });
    }, 500);
  }

  async function handleDeleteAccount() {
    setDeleting(true);
    try {
      await deleteAccount(deletePassword);
      AuthStorage.clear();
      router.replace("/");
    } catch {
      setToast("탈퇴에 실패했습니다. 비밀번호를 확인해주세요.");
      setToastType("error");
      setDeleting(false);
    }
  }

  if (loadingProfile) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const displayItems = tab === "my" ? myItems : likedItems;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {toast && (
        <div className="mb-4">
          <Toast message={toast} type={toastType} onClose={() => setToast("")} />
        </div>
      )}

      {/* Profile Header */}
      <div className="mb-8 flex items-center gap-5">
        {/* Avatar */}
        <div className="relative h-20 w-20 shrink-0 rounded-full bg-panelSoft border-2 border-ink/10 overflow-hidden">
          {profile?.avatar_url ? (
            <Image src={profile.avatar_url} alt="avatar" fill className="object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-3xl">🥚</div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-black text-ink truncate">{profile?.nickname}</h1>
          {profile?.bio && (
            <p className="mt-0.5 text-sm text-ink/60 line-clamp-2">{profile.bio}</p>
          )}
          <div className="mt-1.5 flex gap-4 text-xs text-ink/50">
            <span>
              <strong className="text-ink/80">{profile?.creature_count ?? 0}</strong> 크리처
            </span>
            <span>
              <strong className="text-ink/80">{profile?.like_received_count ?? 0}</strong> 받은 좋아요
            </span>
          </div>
        </div>

        {/* Edit button */}
        <Link href="/my/edit">
          <Button variant="secondary" size="sm">
            프로필 편집
          </Button>
        </Link>
      </div>

      {/* Tab Bar */}
      <div className="mb-6 flex border-b border-ink/10">
        {(["my", "liked"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm font-semibold transition border-b-2 -mb-px ${
              tab === t
                ? "border-point text-point"
                : "border-transparent text-ink/50 hover:text-ink/80"
            }`}
          >
            {t === "my" ? `내 크리처 (${myItems.length})` : `좋아요한 크리처 (${likedItems.length})`}
          </button>
        ))}
      </div>

      {/* Grid */}
      {loadingItems ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : displayItems.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-ink/40">
          <span className="text-5xl">{tab === "my" ? "🥚" : "💔"}</span>
          <p className="text-sm">
            {tab === "my"
              ? "아직 만든 크리처가 없어요."
              : "좋아요한 크리처가 없어요."}
          </p>
          {tab === "my" && (
            <Link href="/upload">
              <Button size="sm">크리처 만들기</Button>
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {displayItems.map((item) => (
            <CreatureCard
              key={item.id}
              item={item}
              onDelete={handleDelete}
              showDelete={tab === "my"}
            />
          ))}
        </div>
      )}

      {/* 설정 섹션 — 다크모드 + 글자 크기 */}
      <div className="mt-10 rounded-2xl border border-ink/10 bg-panel overflow-hidden">
        <div className="px-5 py-3 border-b border-ink/10">
          <h2 className="text-sm font-bold text-ink/60 uppercase tracking-wide">화면 설정</h2>
        </div>

        {/* 다크 모드 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-ink/5">
          <div>
            <p className="text-sm font-medium text-ink">다크 모드</p>
            <p className="text-xs text-ink/50 mt-0.5">어두운 배경으로 전환합니다</p>
          </div>
          <button
            role="switch"
            aria-checked={dark}
            onClick={() => handleDarkToggle(!dark)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-300 ${
              dark ? "bg-point" : "bg-ink/20"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-300 ${
                dark ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {/* 글자 크기 */}
        <div className="px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-ink">글자 크기</p>
            <span className="text-xs text-ink/50">{size}px</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-ink/50">작게</span>
            <input
              type="range"
              min={0}
              max={2}
              step={1}
              value={FONT_SIZES.indexOf(size as FontSize)}
              onChange={(e) => handleFontSize(FONT_SIZES[Number(e.target.value)])}
              className="flex-1 accent-point"
            />
            <span className="text-sm text-ink/50">크게</span>
          </div>
          <div className="mt-2 text-sm text-ink/60" style={{ fontSize: `${size}px` }}>
            미리보기: 포켓몬을 찾아라!
          </div>
        </div>
      </div>

      {/* 계정 섹션 */}
      <div className="mt-4 rounded-2xl border border-ink/10 bg-panel overflow-hidden">
        <div className="px-5 py-3 border-b border-ink/10">
          <h2 className="text-sm font-bold text-ink/60 uppercase tracking-wide">계정 설정</h2>
        </div>

        <nav className="divide-y divide-ink/5">
          <Link
            href="/my/edit"
            className="flex items-center justify-between px-5 py-3.5 hover:bg-panelSoft transition"
          >
            <span className="text-sm font-medium text-ink">프로필 편집</span>
            <span className="text-ink/30 text-lg">›</span>
          </Link>
          <Link
            href="/my/password"
            className="flex items-center justify-between px-5 py-3.5 hover:bg-panelSoft transition"
          >
            <span className="text-sm font-medium text-ink">비밀번호 변경</span>
            <span className="text-ink/30 text-lg">›</span>
          </Link>
          <button
            onClick={handleLogout}
            className="flex w-full items-center justify-between px-5 py-3.5 hover:bg-panelSoft transition text-left"
          >
            <span className="text-sm font-medium text-warn">로그아웃</span>
            <span className="text-ink/30 text-lg">›</span>
          </button>
          <button
            onClick={() => setDeleteStep(1)}
            className="flex w-full items-center justify-between px-5 py-3.5 hover:bg-panelSoft transition text-left"
          >
            <span className="text-sm font-medium text-danger">회원 탈퇴</span>
            <span className="text-ink/30 text-lg">›</span>
          </button>
        </nav>
      </div>

      {/* 회원 탈퇴 1단계 모달 */}
      <Modal open={deleteStep === 1} onClose={() => setDeleteStep(0)}>
        <div className="p-6 max-w-sm">
          <h3 className="text-lg font-black text-ink mb-3">정말 탈퇴하시겠어요?</h3>
          <p className="text-sm text-ink/70 leading-relaxed mb-6">
            탈퇴 시 크리처·댓글·좋아요·계정 정보가 즉시 삭제됩니다.
            <br />
            <strong className="text-danger">복구가 불가능합니다.</strong>
          </p>
          <div className="flex gap-3">
            <Button variant="ghost" className="flex-1" onClick={() => setDeleteStep(0)}>취소</Button>
            <Button variant="primary" className="flex-1 bg-danger hover:brightness-90" onClick={() => setDeleteStep(2)}>
              다음
            </Button>
          </div>
        </div>
      </Modal>

      {/* 회원 탈퇴 2단계 모달 — 비밀번호 확인 */}
      <Modal open={deleteStep === 2} onClose={() => { setDeleteStep(0); setDeletePassword(""); }}>
        <div className="p-6 max-w-sm">
          <h3 className="text-lg font-black text-ink mb-2">비밀번호 확인</h3>
          <p className="text-sm text-ink/60 mb-5">탈퇴를 확인하려면 현재 비밀번호를 입력하세요.</p>
          <input
            type="password"
            value={deletePassword}
            onChange={(e) => setDeletePassword(e.target.value)}
            placeholder="비밀번호"
            className="w-full rounded-xl border border-ink/15 bg-base px-4 py-2.5 text-sm outline-none focus:border-danger focus:ring-2 focus:ring-danger/20 mb-4"
          />
          <div className="flex gap-3">
            <Button
              variant="ghost"
              className="flex-1"
              onClick={() => { setDeleteStep(0); setDeletePassword(""); }}
            >
              취소
            </Button>
            <Button
              className="flex-1 bg-danger hover:brightness-90"
              disabled={!deletePassword || deleting}
              onClick={() => void handleDeleteAccount()}
            >
              {deleting ? "탈퇴 중..." : "탈퇴하기"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
