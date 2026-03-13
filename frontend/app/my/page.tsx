"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  ApiError,
  deleteCreature,
  getLikedCreatures,
  getMyCreatures,
  getMyProfile,
} from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import { MyCreatureItem, UserProfile } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Toast } from "@/components/ui/Toast";

type Tab = "my" | "liked";

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
          <Toast message={toast} onClose={() => setToast("")} />
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

      {/* Settings Section */}
      <div className="mt-12 rounded-2xl border border-ink/10 bg-panel overflow-hidden">
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
        </nav>
      </div>
    </div>
  );
}
