"use client";

import { useState } from "react";
import type { PokemonMatchResult } from "@/lib/types";
import { TypeBadge } from "@/components/ui/Badge";
import ProgressBar from "@/components/ui/ProgressBar";
import { Button } from "@/components/ui/Button";

// 타입별 배경 색상 (davidkpiano 카드 디자인)
const TYPE_BG_COLORS: Record<string, string> = {
  fire:     "#F08030",
  water:    "#6890F0",
  grass:    "#78C850",
  electric: "#F8D030",
  psychic:  "#F85888",
  normal:   "#A8A878",
  fighting: "#C03028",
  ghost:    "#705898",
  rock:     "#B8A038",
  ground:   "#E0C068",
  ice:      "#98D8D8",
  dragon:   "#7038F8",
  dark:     "#705848",
  steel:    "#B8B8D0",
  fairy:    "#EE99AC",
  poison:   "#A040A0",
  flying:   "#A890F0",
  bug:      "#A8B820",
};

const DEFAULT_BG = "#68A090";

interface PokemonCardProps {
  pokemon: PokemonMatchResult;
  isBest: boolean;         // rank 1 강조
  isSelected: boolean;     // 현재 선택된 카드
  isFading: boolean;       // 선택 후 비선택 카드 fade-out
  disabled: boolean;
  onSelect: (pokemon: PokemonMatchResult) => void;
}

export default function PokemonCard({
  pokemon,
  isBest,
  isSelected,
  isFading,
  disabled,
  onSelect,
}: PokemonCardProps) {
  const [imgError, setImgError] = useState(false);

  const bgColor = TYPE_BG_COLORS[pokemon.primary_type?.toLowerCase()] ?? DEFAULT_BG;
  const spriteUrl = `https://www.serebii.net/pokemongo/pokemon/${String(pokemon.pokemon_id).padStart(3, "0")}.png`;
  const numStr = `#${String(pokemon.pokemon_id).padStart(3, "0")}`;

  return (
    <div
      className="relative flex flex-col overflow-hidden rounded-2xl shadow-deck cursor-pointer select-none
                 transition-all duration-400"
      style={{
        opacity: isFading ? 0.35 : 1,
        transform: isSelected ? "scale(1.03)" : "scale(1)",
      }}
      onClick={() => !disabled && onSelect(pokemon)}
    >
      {/* BEST MATCH 뱃지 */}
      {isBest && (
        <div className="absolute top-3 left-3 z-10 rounded-full bg-white/90 px-2.5 py-0.5
                        text-[10px] font-bold tracking-widest text-point shadow">
          BEST MATCH
        </div>
      )}

      {/* 선택 링 */}
      {isSelected && (
        <div className="absolute inset-0 z-20 rounded-2xl ring-4 ring-white/80 pointer-events-none" />
      )}

      {/* 카드 본문: 타입 배경 + 다이아몬드 패턴 */}
      <div
        className="flex min-h-[220px]"
        style={{
          background: bgColor,
          backgroundImage: `
            repeating-linear-gradient(
              45deg,
              transparent, transparent 4px,
              rgba(0,0,0,0.08) 4px, rgba(0,0,0,0.08) 5px
            )
          `,
        }}
      >
        {/* 좌측: 이미지 패널 */}
        <div className="relative flex w-2/5 items-center justify-center p-4">
          {/* 라디얼 글로우 */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                "radial-gradient(circle at 50% 60%, rgba(255,255,255,0.30), transparent 70%)",
            }}
          />
          {imgError ? (
            /* Fallback: 포켓볼 placeholder */
            <div className="relative z-10 flex h-[80px] w-[80px] items-center justify-center
                            rounded-full bg-white/20 text-3xl">
              ⚪
            </div>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={spriteUrl}
              alt={pokemon.name_kr}
              width={96}
              height={96}
              className="relative z-10 h-24 w-24 animate-bounce-head object-contain drop-shadow-lg"
              style={{ imageRendering: "pixelated" }}
              onError={() => setImgError(true)}
            />
          )}
        </div>

        {/* 우측: 정보 패널 */}
        <div
          className="flex w-3/5 flex-col justify-center gap-1.5 p-4 text-white"
          style={{ fontFamily: "'Lato', sans-serif" }}
        >
          <p className="text-[11px] font-bold tracking-widest opacity-80">◉ {numStr}</p>
          <h2 className="text-xl font-black leading-tight">{pokemon.name_kr}</h2>
          <p className="text-[11px] opacity-70">{pokemon.name_en}</p>

          <div className="flex flex-wrap gap-1 pt-0.5">
            <TypeBadge type={pokemon.primary_type} />
            {pokemon.secondary_type && (
              <TypeBadge type={pokemon.secondary_type} />
            )}
          </div>

          <p className="mt-1 text-sm font-semibold">
            유사도 {(pokemon.similarity * 100).toFixed(1)}%
          </p>
          {/* 타입 색상 프로그레스바 — spec: type color bar */}
          <ProgressBar value={pokemon.similarity} colorClass="bg-white" />

          {/* 매칭 이유 (최대 2개) */}
          <div className="flex flex-wrap gap-1 pt-0.5">
            {pokemon.reasons.slice(0, 2).map((r, i) => (
              <span
                key={i}
                className="rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-medium"
              >
                {r.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* 하단 버튼 영역 */}
      <div className="bg-panel/95 px-4 py-3">
        <Button
          className="w-full"
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation();
            if (!disabled) onSelect(pokemon);
          }}
        >
          {isSelected ? "선택됨 ✓" : "이 포켓몬으로 시작하기"}
        </Button>
      </div>
    </div>
  );
}
