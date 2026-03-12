"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { listPublicCreatures } from "@/lib/api"
import type { Creature } from "@/lib/types"

const HERO_CARDS = [
  { emoji: "🔥", bg: "linear-gradient(135deg, #fff1ee, #ffd6cc)" },
  { emoji: "🌊", bg: "linear-gradient(135deg, #eef4ff, #ccdeff)" },
  { emoji: "⚡", bg: "linear-gradient(135deg, #fffbee, #ffeec0)" },
  { emoji: "🌿", bg: "linear-gradient(135deg, #efffef, #cdffd0)" },
]

const FEATURES = [
  {
    icon: "👤",
    title: "얼굴 CV 분석",
    desc: "AI가 얼굴 특징을 28개 차원으로 분석합니다. 인상, 시각적 특징, 타입 친화도까지 측정합니다.",
  },
  {
    icon: "🎴",
    title: "포켓몬 매칭",
    desc: "386마리 포켓몬 벡터와 유사도를 비교해 나와 가장 닮은 Top 3를 찾아드립니다.",
  },
  {
    icon: "✨",
    title: "나만의 크리처 탄생",
    desc: "Imagen과 Gemini가 세상에 하나뿐인 크리처 이미지와 스토리를 생성합니다.",
  },
]

export default function LandingPage() {
  const [samples, setSamples] = useState<Creature[]>([])

  useEffect(() => {
    listPublicCreatures(4, 0)
      .then((res) => setSamples(res.items))
      .catch(() => {})
  }, [])

  return (
    <div className="mx-auto max-w-6xl px-4">

      {/* ── Hero ── */}
      <section className="flex min-h-[calc(100vh-72px)] flex-col items-center justify-center gap-12 py-16 lg:flex-row lg:gap-16">

        {/* Left: 4-card visual grid */}
        <div className="flex-1 flex items-center justify-center">
          <div className="grid grid-cols-2 gap-4 rotate-[-5deg] scale-90 lg:scale-100">
            {HERO_CARDS.map((card, i) => (
              <div
                key={i}
                className="flex h-36 w-36 items-center justify-center rounded-2xl text-6xl shadow-deck transition-transform duration-700 hover:scale-105 hover:rotate-0"
                style={{ background: card.bg }}
              >
                {card.emoji}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Headline + CTA */}
        <div className="flex-1 text-center lg:text-left">
          <h1 className="text-4xl font-black leading-tight tracking-tight text-ink lg:text-5xl xl:text-6xl">
            내 얼굴을 닮은
            <br />
            <span className="text-point">포켓몬</span>을
            <br />
            찾아보세요
          </h1>
          <p className="mt-5 text-base leading-relaxed text-ink/70 lg:text-lg">
            AI가 얼굴을 분석해 386마리 포켓몬 중
            <br className="hidden lg:block" />
            나와 가장 닮은 포켓몬을 찾고,
            <br className="hidden lg:block" />
            세상에 하나뿐인 크리처를 만들어드립니다.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3 lg:justify-start">
            <Link
              href="/intro"
              className="rounded-full bg-point px-7 py-3.5 text-base font-semibold text-white transition hover:brightness-95"
            >
              포켓몬 찾기 시작 →
            </Link>
            <Link
              href="/plaza"
              className="rounded-full border border-ink/30 px-7 py-3.5 text-base font-semibold text-ink transition hover:border-point hover:text-point"
            >
              광장 구경하기
            </Link>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="py-16">
        <h2 className="mb-10 text-center text-2xl font-bold text-ink">어떻게 만들어지나요?</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {FEATURES.map((feat, i) => (
            <div key={i} className="section-card p-6 text-center">
              <div className="mb-4 text-5xl">{feat.icon}</div>
              <h3 className="text-lg font-semibold text-ink">{feat.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/70">{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Sample Creatures ── */}
      {samples.length > 0 && (
        <section className="py-16">
          <div className="mb-8 flex items-end justify-between">
            <h2 className="text-2xl font-bold text-ink">광장에서 만난 크리처들</h2>
            <Link href="/plaza" className="text-sm font-medium text-point hover:underline">
              전체 보기 →
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {samples.map((item) => (
              <div key={item.id} className="section-card overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.image_url || "https://placehold.co/400x400/png?text=?"}
                  alt={item.name}
                  className="h-44 w-full object-cover"
                />
                <div className="p-3">
                  <p className="font-semibold text-ink">{item.name}</p>
                  <p className="mt-1 line-clamp-2 text-xs text-ink/70">{item.story}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="py-8" />
    </div>
  )
}
