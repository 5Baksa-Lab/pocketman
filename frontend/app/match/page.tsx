"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { MatchResultStorage } from "@/lib/storage";
import type { MatchResponse, PokemonMatchResult } from "@/lib/types";
import { createCreature } from "@/lib/api";
import PokemonCard from "@/components/features/match/PokemonCard";
import { Toast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Spinner";

type PageState = "loadingFromSession" | "noSession" | "ready" | "selecting" | "creating" | "createError";

export default function MatchPage() {
  const router = useRouter();
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [pageState, setPageState] = useState<PageState>("loadingFromSession");
  const [selectedPokemon, setSelectedPokemon] = useState<PokemonMatchResult | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const isCreating = useRef(false); // 중복 생성 요청 방지

  useEffect(() => {
    const data = MatchResultStorage.load();
    if (!data) {
      setPageState("noSession");
      router.replace("/upload");
      return;
    }
    setMatchResult(data);
    setPageState("ready");
  }, [router]);

  async function handleSelect(pokemon: PokemonMatchResult) {
    if (isCreating.current) return;
    if (pageState === "creating") return;

    setSelectedPokemon(pokemon);
    setPageState("selecting");
    setErrorMessage("");

    // 0.6s 대기 (선택 애니메이션)
    await new Promise((r) => setTimeout(r, 600));

    if (isCreating.current) return;
    isCreating.current = true;
    setPageState("creating");

    try {
      const creature = await createCreature({
        matched_pokemon_id: pokemon.pokemon_id,
        match_rank: pokemon.rank,
        similarity_score: pokemon.similarity,
        match_reasons: pokemon.reasons.map((r) => ({
          dimension: r.dimension,
          label: r.label,
          user_value: r.user_value,
          pokemon_value: r.pokemon_value,
        })),
        name: "임시이름",
        story: null,
        image_url: null,
        video_url: null,
        is_public: false,
      });
      router.push(`/generate/${creature.id}`);
    } catch (err) {
      isCreating.current = false;
      setPageState("createError");
      setErrorMessage(err instanceof Error ? err.message : "크리처 생성에 실패했습니다. 다시 시도해주세요.");
    }
  }

  function handleRetry() {
    setSelectedPokemon(null);
    setPageState("ready");
    setErrorMessage("");
  }

  // 카드 렌더 순서: desktop — rank2(left), rank1(center), rank3(right)
  // mobile — rank1, rank2, rank3 (top to bottom)
  const orderedDesktop = matchResult
    ? [
        matchResult.top3.find((p) => p.rank === 2),
        matchResult.top3.find((p) => p.rank === 1),
        matchResult.top3.find((p) => p.rank === 3),
      ].filter(Boolean) as PokemonMatchResult[]
    : [];

  const orderedMobile = matchResult
    ? [...matchResult.top3].sort((a, b) => a.rank - b.rank)
    : [];

  const isDisabled = pageState === "creating" || pageState === "selecting";

  if (pageState === "loadingFromSession" || pageState === "noSession") {
    return (
      <div className="flex min-h-[calc(100vh-72px)] items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* 헤더 */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-black tracking-tight text-ink">Top-3 매칭 결과</h1>
        <p className="mt-2 text-sm text-ink/60">
          가장 잘 어울리는 포켓몬을 선택해 나만의 크리처를 만들어보세요
        </p>
      </div>

      {/* 에러 Toast */}
      {errorMessage && (
        <div className="mb-6">
          <Toast
            message={errorMessage}
            type="error"
            onClose={handleRetry}
          />
        </div>
      )}

      {/* 생성 중 상태 표시 */}
      {pageState === "creating" && (
        <div className="mb-6 flex items-center justify-center gap-2 rounded-xl bg-point/10 py-3 text-sm font-semibold text-point">
          <Spinner className="h-4 w-4" />
          <span>크리처 데이터를 준비하고 있어요...</span>
        </div>
      )}

      {/* Desktop: 3열 카드 (rank2 | rank1 | rank3) */}
      <div className="hidden md:grid md:grid-cols-3 md:gap-6">
        {orderedDesktop.map((pokemon) => {
          const isBest = pokemon.rank === 1;
          const isSelected = selectedPokemon?.pokemon_id === pokemon.pokemon_id;
          const isFading = !!selectedPokemon && !isSelected;
          return (
            <div
              key={pokemon.pokemon_id}
              className="transition-transform duration-300"
              style={{ transform: isBest && !selectedPokemon ? "scale(1.05)" : undefined }}
            >
              <PokemonCard
                pokemon={pokemon}
                isBest={isBest}
                isSelected={isSelected}
                isFading={isFading}
                disabled={isDisabled}
                onSelect={handleSelect}
              />
            </div>
          );
        })}
      </div>

      {/* Mobile: 세로 스택 (rank1 → rank2 → rank3) */}
      <div className="flex flex-col gap-5 md:hidden">
        {orderedMobile.map((pokemon) => {
          const isBest = pokemon.rank === 1;
          const isSelected = selectedPokemon?.pokemon_id === pokemon.pokemon_id;
          const isFading = !!selectedPokemon && !isSelected;
          return (
            <PokemonCard
              key={pokemon.pokemon_id}
              pokemon={pokemon}
              isBest={isBest}
              isSelected={isSelected}
              isFading={isFading}
              disabled={isDisabled}
              onSelect={handleSelect}
            />
          );
        })}
      </div>
    </div>
  );
}
