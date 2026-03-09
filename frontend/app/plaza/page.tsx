"use client";

import { useEffect, useMemo, useState } from "react";

import { createReaction, getReactionSummary, listPublicCreatures } from "@/lib/api";
import { Creature, ReactionSummary } from "@/lib/types";

const PAGE_SIZE = 12;
const REACTION_SET = ["🔥", "❤️", "👏", "😂"];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch {
    return iso;
  }
}

export default function PlazaPage() {
  const [focusId, setFocusId] = useState<string>("");

  const [items, setItems] = useState<Creature[]>([]);
  const [offset, setOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const [summaryMap, setSummaryMap] = useState<Record<string, ReactionSummary>>({});
  const [reactionBusyKey, setReactionBusyKey] = useState<string>("");

  const focusIndex = useMemo(
    () => items.findIndex((item) => item.id === focusId),
    [focusId, items]
  );

  const hydrateSummary = async (creatures: Creature[]) => {
    const summaries = await Promise.all(
      creatures.map(async (creature) => {
        try {
          const summary = await getReactionSummary(creature.id);
          return { id: creature.id, summary };
        } catch {
          return { id: creature.id, summary: { creature_id: creature.id, counts: [], total: 0 } };
        }
      })
    );

    setSummaryMap((prev) => {
      const next = { ...prev };
      for (const item of summaries) {
        next[item.id] = item.summary;
      }
      return next;
    });
  };

  const loadInitial = async () => {
    setLoading(true);
    setErrorMessage("");
    try {
      const result = await listPublicCreatures(PAGE_SIZE, 0);
      setItems(result.items);
      setOffset(result.items.length);
      setHasMore(result.items.length === PAGE_SIZE);
      await hydrateSummary(result.items);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "광장 피드 로딩에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    if (!hasMore || loading) {
      return;
    }

    setLoading(true);
    setErrorMessage("");
    try {
      const result = await listPublicCreatures(PAGE_SIZE, offset);
      setItems((prev) => [...prev, ...result.items]);
      setOffset((prev) => prev + result.items.length);
      setHasMore(result.items.length === PAGE_SIZE);
      await hydrateSummary(result.items);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "추가 피드 로딩에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleReaction = async (creatureId: string, emoji: string) => {
    const busyKey = `${creatureId}-${emoji}`;
    setReactionBusyKey(busyKey);
    try {
      await createReaction(creatureId, { emoji_type: emoji });
      const summary = await getReactionSummary(creatureId);
      setSummaryMap((prev) => ({ ...prev, [creatureId]: summary }));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "리액션 등록에 실패했습니다.");
    } finally {
      setReactionBusyKey("");
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setFocusId(params.get("focus") || "");
    void loadInitial();
  }, []);

  return (
    <section className="section-card p-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">포켓 도감 광장</h1>
          <p className="mt-1 text-sm text-ink/80">공개된 크리처를 확인하고 이모지 반응을 남겨보세요.</p>
        </div>
        {focusIndex >= 0 ? (
          <p className="rounded-full bg-point/15 px-3 py-1 text-xs font-semibold text-point">
            공유 링크로 이동한 항목: #{focusIndex + 1}
          </p>
        ) : null}
      </div>

      {errorMessage ? (
        <p className="mb-4 rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">{errorMessage}</p>
      ) : null}

      {items.length === 0 && !loading ? (
        <div className="rounded-xl border border-dashed border-ink/20 bg-panelSoft/40 p-8 text-center text-sm text-ink/70">
          아직 공개된 크리처가 없습니다.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => {
            const summary = summaryMap[item.id];
            const focused = focusId === item.id;

            return (
              <article
                key={item.id}
                className={`rounded-xl2 border p-4 transition ${
                  focused ? "border-point bg-point/10" : "border-ink/10 bg-white/80"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.image_url || "https://placehold.co/800x800/png?text=No+Image"}
                  alt={item.name}
                  className="h-52 w-full rounded-lg object-cover"
                />

                <div className="mt-3">
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-lg font-semibold">{item.name}</h2>
                    <span className="rounded-full bg-ink/10 px-2 py-1 text-[11px] font-medium text-ink/70">
                      {item.matched_pokemon_name_kr || `No.${item.matched_pokemon_id}`}
                    </span>
                  </div>

                  <p className="mt-2 line-clamp-3 text-sm text-ink/80">{item.story || "스토리 없음"}</p>
                  <p className="mt-2 text-[11px] text-ink/60">생성일: {formatDate(item.created_at)}</p>

                  {item.video_url ? (
                    <video className="mt-3 w-full rounded-lg" controls src={item.video_url} />
                  ) : null}
                </div>

                <div className="mt-4 border-t border-ink/10 pt-3">
                  <p className="text-xs text-ink/65">리액션 {summary?.total ?? 0}개</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {REACTION_SET.map((emoji) => {
                      const count = summary?.counts.find((entry) => entry.emoji_type === emoji)?.count || 0;
                      const busy = reactionBusyKey === `${item.id}-${emoji}`;
                      return (
                        <button
                          key={`${item.id}-${emoji}`}
                          type="button"
                          disabled={busy}
                          onClick={() => handleReaction(item.id, emoji)}
                          className="rounded-full border border-ink/20 bg-white px-3 py-1 text-sm transition hover:border-point"
                        >
                          {emoji} {count}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="mt-6 flex justify-center">
        <button
          type="button"
          onClick={loadMore}
          disabled={!hasMore || loading}
          className="rounded-full border border-ink/25 bg-panel px-5 py-2.5 text-sm font-semibold transition hover:border-point hover:text-point"
        >
          {loading ? "불러오는 중..." : hasMore ? "더 보기" : "마지막 페이지"}
        </button>
      </div>
    </section>
  );
}
