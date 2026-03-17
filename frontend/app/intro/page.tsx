"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

const STEPS = [
  {
    // serebii.net Pokemon GO 아트 — 피카츄 #025
    pokemonUrl: "https://www.serebii.net/pokemongo/pokemon/025.png",
    pokemonAlt: "피카츄",
    title: "당신의 얼굴을 분석합니다",
    desc: "AI가 얼굴 특징을 28개 차원으로 측정합니다",
  },
  {
    // 파이리 #004
    pokemonUrl: "https://www.serebii.net/pokemongo/pokemon/004.png",
    pokemonAlt: "파이리",
    title: "386마리 포켓몬과 비교합니다",
    desc: "벡터 유사도로 가장 닮은 포켓몬 Top 3를 찾습니다",
  },
  {
    // 이브이 #133
    pokemonUrl: "https://www.serebii.net/pokemongo/pokemon/133.png",
    pokemonAlt: "이브이",
    title: "나만의 크리처가 탄생합니다",
    desc: "Imagen과 Gemini가 세상에 하나뿐인 크리처를 만듭니다",
  },
]

const STEP_DURATION_MS = 1400

export default function IntroPage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    if (currentStep >= STEPS.length) {
      router.push("/upload")
      return
    }

    const showTimer = setTimeout(() => {
      setVisible(false)
    }, STEP_DURATION_MS - 300)

    const advanceTimer = setTimeout(() => {
      setCurrentStep((prev) => prev + 1)
      setVisible(true)
    }, STEP_DURATION_MS)

    return () => {
      clearTimeout(showTimer)
      clearTimeout(advanceTimer)
    }
  }, [currentStep, router])

  const step = STEPS[currentStep]

  return (
    /* 검정 배경 — 인트로 전용 */
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Pocketman 인트로"
      className="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-black px-4 text-center"
    >
      <div
        className="transition-all duration-300"
        style={{
          opacity: visible ? 1 : 0,
          transform: visible ? "translateY(0)" : "translateY(-12px)",
        }}
      >
        {step && (
          <>
            {/* Pokemon GO 아트 이미지 */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={step.pokemonUrl}
              alt={step.pokemonAlt}
              width={128}
              height={128}
              className="mx-auto mb-6 h-32 w-32 object-contain drop-shadow-2xl"
              style={{ imageRendering: "pixelated" }}
            />
            <h2 className="text-3xl font-black text-white lg:text-4xl">{step.title}</h2>
            <p className="mt-4 text-base text-white/60">{step.desc}</p>
          </>
        )}
      </div>

      {/* Step dots */}
      <div className="mt-12 flex gap-2">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={`h-2 rounded-full transition-all duration-300 ${
              i === currentStep ? "w-8 bg-point" : i < currentStep ? "w-2 bg-point/40" : "w-2 bg-white/20"
            }`}
          />
        ))}
      </div>

      <button
        type="button"
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus
        onClick={() => router.push("/upload")}
        className="mt-10 text-sm text-white/40 underline-offset-4 hover:text-white/70 hover:underline"
      >
        건너뛰기
      </button>
    </div>
  )
}
