"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { MatchResultStorage } from "@/lib/storage"
import type { MatchResponse } from "@/lib/types"

export default function MatchPage() {
  const router = useRouter()
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null)

  useEffect(() => {
    const data = MatchResultStorage.load()
    if (!data) {
      router.push("/upload")
      return
    }
    setMatchResult(data)
  }, [router])

  if (!matchResult) {
    return (
      <div className="flex min-h-[calc(100vh-72px)] items-center justify-center">
        <p className="text-ink/60">데이터 로딩 중...</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 text-center">
      <h1 className="text-3xl font-bold text-ink">Top-3 포켓몬 선택</h1>
      <p className="mt-2 text-sm text-ink/60">F2 Stage에서 구현됩니다</p>

      {/* 데이터 수신 확인 (F1 DoD 검증용) */}
      <div className="mt-8 section-card p-6 text-left">
        <p className="text-sm font-semibold text-ink mb-3">
          sessionStorage 수신 완료 ✅ — Top {matchResult.top3.length}마리
        </p>
        <div className="grid gap-3 md:grid-cols-3">
          {matchResult.top3.map((pokemon) => (
            <div key={pokemon.pokemon_id} className="rounded-xl border border-ink/10 bg-white/80 p-4">
              <p className="text-xs font-semibold text-point">#{pokemon.rank}</p>
              <p className="mt-1 text-lg font-bold text-ink">{pokemon.name_kr}</p>
              <p className="text-xs text-ink/60">{pokemon.name_en}</p>
              <p className="mt-1 text-xs text-ink/70">
                유사도: {(pokemon.similarity * 100).toFixed(1)}%
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
