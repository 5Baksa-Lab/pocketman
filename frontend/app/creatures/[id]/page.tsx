"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  addLike,
  ApiError,
  createComment,
  deleteComment,
  deleteCreature,
  getCreatureDetail,
  listComments,
  patchCreature,
  removeLike,
} from "@/lib/api";
import { AuthStorage } from "@/lib/storage";
import { Comment, CommentListResponse, CreatureDetail } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Toast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Spinner";
import Modal from "@/components/ui/Modal";
import { TypeBadge } from "@/components/ui/Badge";
import InlineEditableName from "@/components/features/result/InlineEditableName";

type PageState = "loading" | "ready" | "notFound";

const TYPE_COLORS: Record<string, string> = {
  노말: "#A8A878", 불꽃: "#F08030", 물: "#6890F0", 풀: "#78C850",
  전기: "#F8D030", 얼음: "#98D8D8", 격투: "#C03028", 독: "#A040A0",
  땅: "#E0C068", 비행: "#A890F0", 에스퍼: "#F85888", 벌레: "#A8B820",
  바위: "#B8A038", 고스트: "#705898", 드래곤: "#7038F8", 악: "#705848",
  강철: "#B8B8D0", 페어리: "#EE99AC",
};

function ShareButton({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 rounded-lg border border-ink/15 px-3 py-1.5 text-xs text-ink/60 hover:bg-panel transition"
    >
      {copied ? "✅ 복사됨" : "📋 링크 복사"}
    </button>
  );
}

function CommentSection({
  creatureId,
  isLoggedIn,
  onAuthRequired,
}: {
  creatureId: string;
  isLoggedIn: boolean;
  onAuthRequired: () => void;
}) {
  const [commentData, setCommentData] = useState<CommentListResponse | null>(null);
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    listComments(creatureId).then(setCommentData).catch(() => {});
  }, [creatureId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isLoggedIn) { onAuthRequired(); return; }
    if (!input.trim() || submitting) return;
    setSubmitting(true);
    try {
      const comment = await createComment(creatureId, input.trim());
      setCommentData(prev =>
        prev
          ? { ...prev, items: [comment, ...prev.items], total: prev.total + 1 }
          : { items: [comment], total: 1, page: 1 }
      );
      setInput("");
    } catch {
      setToast("댓글 작성에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(commentId: string) {
    try {
      await deleteComment(creatureId, commentId);
      setCommentData(prev =>
        prev
          ? { ...prev, items: prev.items.filter(c => c.id !== commentId), total: prev.total - 1 }
          : prev
      );
    } catch {
      setToast("댓글 삭제에 실패했습니다.");
    }
  }

  return (
    <div className="mt-8 border-t border-ink/10 pt-6">
      <h3 className="mb-4 text-sm font-semibold text-ink">
        댓글 {commentData ? commentData.total : ""}
      </h3>

      {toast && <Toast message={toast} type="error" onClose={() => setToast("")} />}

      <form onSubmit={(e) => void handleSubmit(e)} className="mb-5 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={() => { if (!isLoggedIn) onAuthRequired(); }}
          maxLength={100}
          placeholder={isLoggedIn ? "댓글을 입력하세요 (최대 100자)" : "댓글을 남기려면 로그인하세요"}
          className="flex-1 rounded-xl border border-ink/15 bg-base px-4 py-2 text-sm outline-none focus:border-point focus:ring-2 focus:ring-point/20"
        />
        <Button type="submit" disabled={submitting || !input.trim()} className="shrink-0 text-sm">
          {submitting ? "..." : "작성"}
        </Button>
      </form>

      {commentData === null ? (
        <div className="flex justify-center py-4"><Spinner /></div>
      ) : commentData.items.length === 0 ? (
        <p className="text-center text-sm text-ink/40 py-4">아직 댓글이 없어요. 첫 댓글을 남겨보세요!</p>
      ) : (
        <ul className="space-y-3">
          {commentData.items.map((c: Comment) => (
            <li key={c.id} className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-point/20 text-xs font-bold text-point">
                {c.author.nickname[0]}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2">
                  <span className="text-xs font-semibold text-ink">{c.author.nickname}</span>
                  <span className="text-[10px] text-ink/40">
                    {new Date(c.created_at).toLocaleDateString("ko-KR")}
                  </span>
                </div>
                <p className="mt-0.5 text-sm text-ink/80 break-words">{c.content}</p>
              </div>
              {c.is_mine && (
                <button
                  onClick={() => void handleDelete(c.id)}
                  className="shrink-0 text-xs text-ink/30 hover:text-danger transition"
                >
                  삭제
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function CreatureDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [state, setState] = useState<PageState>("loading");
  const [creature, setCreature] = useState<CreatureDetail | null>(null);
  const [toast, setToast] = useState("");
  const [toastType, setToastType] = useState<"error" | "success">("error");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const currentUser = AuthStorage.loadUser();
  const isLoggedIn = !!currentUser;
  const isOwner = !!(creature && currentUser && creature.owner?.id === currentUser.id);
  const shareUrl = typeof window !== "undefined" ? window.location.href : "";

  useEffect(() => {
    if (!id) return;
    getCreatureDetail(id)
      .then((data) => { setCreature(data); setState("ready"); })
      .catch((err) => {
        setState(err instanceof ApiError && err.status === 404 ? "notFound" : "notFound");
      });
  }, [id]);

  async function handleLike() {
    if (!isLoggedIn) { setShowAuthModal(true); return; }
    if (!creature) return;
    try {
      const res = creature.is_liked
        ? await removeLike(creature.id)
        : await addLike(creature.id);
      setCreature(prev => prev ? { ...prev, like_count: res.like_count, is_liked: !prev.is_liked } : prev);
    } catch {
      showToast("좋아요 처리에 실패했습니다.", "error");
    }
  }

  async function handleTogglePublic() {
    if (!creature) return;
    try {
      const updated = await patchCreature(creature.id, { is_public: !creature.is_public });
      setCreature(prev => prev ? { ...prev, is_public: updated.is_public } : prev);
      showToast(updated.is_public ? "공개로 전환됐어요." : "비공개로 전환됐어요.", "success");
    } catch {
      showToast("전환에 실패했습니다.", "error");
    }
  }

  async function handleDelete() {
    if (!creature) return;
    setDeleting(true);
    try {
      await deleteCreature(creature.id);
      router.replace("/my");
    } catch {
      showToast("삭제에 실패했습니다.", "error");
      setDeleting(false);
      setShowDeleteModal(false);
    }
  }

  function handleNameSave(newName: string) {
    setCreature(prev => prev ? { ...prev, name: newName } : prev);
  }

  function showToast(msg: string, type: "error" | "success") {
    setToast(msg);
    setToastType(type);
  }

  function toggleVideo() {
    if (!videoRef.current) return;
    videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause();
  }

  if (state === "loading") {
    return (
      <div className="flex min-h-[calc(100vh-72px)] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (state === "notFound" || !creature) {
    return (
      <div className="flex min-h-[calc(100vh-72px)] flex-col items-center justify-center gap-4 text-center px-4">
        <div className="text-5xl">🔍</div>
        <h1 className="text-xl font-black text-ink">크리처를 찾을 수 없어요</h1>
        <p className="text-sm text-ink/60">비공개이거나 삭제된 크리처입니다.</p>
        <Button onClick={() => router.push("/plaza")} variant="secondary">광장으로 돌아가기</Button>
      </div>
    );
  }

  const bgColor = TYPE_COLORS[creature.primary_type ?? ""] ?? "#A8A878";

  const cardContent = (
    <div className="w-full rounded-2xl overflow-hidden shadow-deck">
      {/* 카드 상단: 타입 색상 배경 + 이미지/영상 */}
      <div
        className="relative flex items-center justify-center p-8 min-h-[280px]"
        style={{
          background: `${bgColor}22`,
          backgroundImage: `repeating-linear-gradient(45deg, ${bgColor}11 0, ${bgColor}11 1px, transparent 0, transparent 50%)`,
          backgroundSize: "12px 12px",
        }}
      >
        {creature.video_url ? (
          <div className="relative cursor-pointer" onClick={toggleVideo}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {creature.image_url && (
              <img
                src={creature.image_url}
                alt={creature.name}
                className="h-48 w-48 rounded-xl object-cover"
              />
            )}
            <video
              ref={videoRef}
              src={creature.video_url}
              loop
              playsInline
              className="absolute inset-0 h-full w-full rounded-xl object-cover opacity-0 hover:opacity-100 transition-opacity"
            />
            <div className="absolute bottom-2 right-2 flex h-7 w-7 items-center justify-center rounded-full bg-black/50 text-white text-xs">
              ▶
            </div>
          </div>
        ) : creature.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={creature.image_url}
            alt={creature.name}
            className="h-48 w-48 rounded-xl object-cover"
          />
        ) : (
          <div className="flex h-48 w-48 items-center justify-center rounded-xl bg-white/30 text-5xl">🐾</div>
        )}
      </div>

      {/* 카드 하단: 정보 */}
      <div className="bg-base p-6">
        {/* 이름 */}
        <div className="mb-1 flex items-center gap-2">
          {isOwner ? (
            <InlineEditableName
              creatureId={creature.id}
              initialName={creature.name}
              onSaved={handleNameSave}
            />
          ) : (
            <h1 className="text-2xl font-black text-ink">{creature.name}</h1>
          )}
        </div>

        {/* 타입 배지 */}
        <div className="mb-3 flex gap-1.5">
          {creature.primary_type && <TypeBadge type={creature.primary_type} />}
          {creature.secondary_type && <TypeBadge type={creature.secondary_type} />}
        </div>

        {/* 소유자 + 유사도 */}
        <p className="mb-1 text-xs text-ink/50">
          {creature.owner ? `by @${creature.owner.nickname}` : "by 익명"}
          {" · "}
          {creature.matched_pokemon_name_kr} 닮음 {Math.round(creature.similarity_score * 100)}%
        </p>
        <p className="mb-1 text-xs text-ink/40">
          {new Date(creature.created_at).toLocaleDateString("ko-KR")}
        </p>

        {/* 스토리 */}
        {creature.story && (
          <p className="mt-3 text-sm leading-relaxed text-ink/70">{creature.story}</p>
        )}

        {/* 버튼 그룹 */}
        <div className="mt-5 flex flex-wrap gap-2">
          {isOwner ? (
            <>
              <button
                onClick={handleTogglePublic}
                className="rounded-lg border border-ink/15 px-3 py-1.5 text-xs text-ink/60 hover:bg-panel transition"
              >
                {creature.is_public ? "🌍 공개" : "🔒 비공개"}
              </button>
              <ShareButton url={shareUrl} />
              <button
                onClick={() => setShowDeleteModal(true)}
                className="rounded-lg border border-danger/30 px-3 py-1.5 text-xs text-danger hover:bg-danger/10 transition"
              >
                🗑 삭제
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => void handleLike()}
                className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition ${
                  creature.is_liked
                    ? "border-danger/40 bg-danger/10 text-danger"
                    : "border-ink/15 text-ink/60 hover:bg-panel"
                }`}
              >
                ❤️ {creature.like_count}
              </button>
              <ShareButton url={shareUrl} />
              <button
                disabled
                className="rounded-lg border border-ink/10 px-3 py-1.5 text-xs text-ink/30 cursor-not-allowed"
                title="광장에서 찾기 기능은 F3-3에서 지원됩니다"
              >
                🗺 광장에서 찾기
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {toast && (
        <Toast message={toast} type={toastType} onClose={() => setToast("")} />
      )}

      {cardContent}

      <CommentSection
        creatureId={creature.id}
        isLoggedIn={isLoggedIn}
        onAuthRequired={() => setShowAuthModal(true)}
      />

      {/* 삭제 확인 모달 */}
      <Modal open={showDeleteModal} onClose={() => setShowDeleteModal(false)}>
        <div className="flex flex-col gap-5 p-6 text-center">
          <div className="text-4xl">🗑</div>
          <div>
            <h2 className="text-lg font-black text-ink">크리처를 삭제할까요?</h2>
            <p className="mt-1.5 text-sm text-ink/60">삭제 후에는 복구할 수 없습니다.</p>
          </div>
          <div className="flex flex-col gap-2">
            <Button
              className="w-full"
              disabled={deleting}
              onClick={() => void handleDelete()}
              style={{ backgroundColor: "#c13515" }}
            >
              {deleting ? "삭제 중..." : "삭제하기"}
            </Button>
            <Button variant="secondary" className="w-full" onClick={() => setShowDeleteModal(false)}>
              취소
            </Button>
          </div>
        </div>
      </Modal>

      {/* 로그인 유도 모달 */}
      <Modal open={showAuthModal} onClose={() => setShowAuthModal(false)}>
        <div className="flex flex-col gap-5 p-6 text-center">
          <div className="text-4xl">🔒</div>
          <div>
            <h2 className="text-lg font-black text-ink">로그인이 필요해요</h2>
            <p className="mt-1.5 text-sm text-ink/60">좋아요와 댓글은 로그인 후 이용할 수 있어요.</p>
          </div>
          <div className="flex flex-col gap-2">
            <Button className="w-full" onClick={() => router.push(`/login?next=/creatures/${creature.id}`)}>
              로그인하기
            </Button>
            <Button variant="secondary" className="w-full" onClick={() => router.push(`/signup?next=/creatures/${creature.id}`)}>
              회원가입하기
            </Button>
          </div>
          <button onClick={() => setShowAuthModal(false)} className="text-xs text-ink/40 hover:text-ink/70 transition">
            나중에 할게요
          </button>
        </div>
      </Modal>
    </div>
  );
}
