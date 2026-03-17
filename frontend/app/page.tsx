"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { Volume2, VolumeX } from "lucide-react"
import { listPublicCreatures } from "@/lib/api"
import type { Creature } from "@/lib/types"

const POKEMON_IDS = [25, 4, 7, 1, 133, 143, 150, 94];
const JOURNEY_STEPS = [
  {
    stage: "STAGE 1",
    icon: "📸",
    title: "포켓 스캔",
    description: "사진 한 장으로 인상과 분위기를 읽어냅니다.",
    accent: "사진 1장",
    accentColor: "bg-pk-yellow text-pk-dark",
    panelTone: "bg-pk-yellow/35",
  },
  {
    stage: "STAGE 2",
    icon: "⚡",
    title: "파트너 매칭",
    description: "가장 닮은 포켓몬 TOP 3를 바로 보여줍니다.",
    accent: "TOP 3",
    accentColor: "bg-pk-blue text-white",
    panelTone: "bg-pk-blue/15",
  },
  {
    stage: "STAGE 3",
    icon: "✨",
    title: "크리처 진화",
    description: "선택한 파트너로 단 하나의 크리처가 완성됩니다.",
    accent: "UNIQUE",
    accentColor: "bg-green-500 text-white",
    panelTone: "bg-green-500/15",
  },
];

export default function LandingPage() {
  const [samples, setSamples] = useState<Creature[]>([])
  // 자동 재생을 위해 초기값을 true로 설정 (브라우저 정책에 따라 클릭 전에는 소리가 안 날 수 있음)
  const [isBgmPlaying, setIsBgmPlaying] = useState(true)

  const [silIdx, setSilIdx] = useState(0);
  const [fade, setFade] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setSilIdx((prev) => (prev + 1) % POKEMON_IDS.length);
        setFade(true);
      }, 500);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // 실제 서버가 떠있지 않을 수도 있으므로 Mock 데이터를 Fallback으로 제공
    listPublicCreatures(4, 0)
      .then((res) => setSamples(res.items))
      .catch(() => {
        setSamples([
          { id: "1", name: "염화의 블레이범", story: "주인의 열정적인 성격을 닮아 뜨거운 불꽃을 뿜어냅니다.", image_url: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/157.png" } as Creature,
          { id: "2", name: "심연의 스이쿤", story: "차분하고 냉철한 눈빛을 가진 신비로운 물의 수호자입니다.", image_url: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/245.png" } as Creature,
          { id: "3", name: "봄바람 쉐이미", story: "따뜻한 미소와 함께 주변에 꽃밭을 피워내는 요정입니다.", image_url: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/251.png" } as Creature,
          { id: "4", name: "번개구름 라이코", story: "강인한 인상과 번개처럼 빠른 속도로 적을 제압합니다.", image_url: "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/243.png" } as Creature,
        ])
      })
  }, [])

  return (
    <div className="min-h-screen bg-pk-bg overflow-x-hidden font-sans text-pk-dark">
      {/* Hidden YouTube BGM */}
      {isBgmPlaying && (
        <iframe 
          width="0" 
          height="0" 
          src="https://www.youtube.com/embed/OT_AsSZjMcI?autoplay=1&loop=1&playlist=OT_AsSZjMcI" 
          title="BGM" 
          frameBorder="0" 
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
          allowFullScreen
          className="hidden"
        ></iframe>
      )}

      {/* ── HEADER (Pokedex Style) ── */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-pk-red border-b-4 border-pk-border z-50 flex items-center justify-between px-4 lg:px-8 shadow-md">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-pk-blue rounded-full border-4 border-white shadow-inner flex items-center justify-center relative overflow-hidden">
             <div className="absolute top-1 left-1 w-3 h-3 bg-white/50 rounded-full"></div>
          </div>
          <div className="flex gap-2">
            <div className="w-4 h-4 bg-red-800 rounded-full border border-pk-border shadow-inner"></div>
            <div className="w-4 h-4 bg-pk-yellow rounded-full border border-pk-border shadow-inner"></div>
            <div className="w-4 h-4 bg-green-500 rounded-full border border-pk-border shadow-inner"></div>
          </div>
        </div>
        <div className="flex items-center gap-4 sm:gap-6">
          <button 
            onClick={() => setIsBgmPlaying(!isBgmPlaying)}
            className="flex items-center justify-center w-10 h-10 bg-white text-pk-dark rounded-full border-4 border-pk-border shadow-retro-sm hover:translate-y-[2px] hover:shadow-none transition-all"
            title="Toggle BGM"
          >
            {isBgmPlaying ? <Volume2 size={18} strokeWidth={3} className="text-pk-blue" /> : <VolumeX size={18} strokeWidth={3} className="text-pk-red" />}
          </button>
          <Link href="/plaza" className="hidden sm:block text-white font-bold tracking-widest hover:text-pk-yellow hover:underline decoration-2 underline-offset-4">
            PLAZA
          </Link>
          <Link href="/intro" className="bg-white text-pk-red font-black px-6 py-2 border-b-4 border-pk-border hover:translate-y-1 hover:border-b-0 active:bg-gray-100 transition-all">
            START
          </Link>
        </div>
      </header>

      <main className="pt-16">
        
        {/* ── HERO SECTION ── */}
        <section className="bg-pk-red pt-12 pb-24 px-4 lg:px-8 border-b-8 border-pk-border relative">
          {/* Diagonal retro pattern */}
          <div className="absolute inset-0 opacity-10 pointer-events-none" 
               style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 20px, #000 20px, #000 22px)' }}></div>
          
          <div className="max-w-6xl mx-auto flex flex-col lg:flex-row items-center gap-16 relative z-10">
            
            {/* Left: Typography */}
            <div className="flex-1 text-white text-center lg:text-left mt-8 lg:mt-0">
              <div className="inline-block px-4 py-1 bg-pk-dark text-pk-yellow font-black text-sm md:text-base mb-6 border-2 border-pk-border skew-x-[-12deg] shadow-retro-sm">
                NEW POKEMON DETECTED !
              </div>
              <h1 className="text-5xl md:text-7xl lg:text-8xl font-black leading-[0.9] tracking-tighter mb-8 drop-shadow-md">
                WHO&apos;S THAT <br/>
                <span className="text-pk-yellow drop-shadow-md">POKEMON?</span> <br/>
                IT&apos;S <span className="underline decoration-4 decoration-pk-yellow underline-offset-8">YOU!</span>
              </h1>
              <p className="text-lg md:text-xl font-medium opacity-90 max-w-xl mb-10 mx-auto lg:mx-0 leading-relaxed bg-black/10 p-4 rounded-xl backdrop-blur-sm border border-white/20">
                당신의 얼굴을 스캔하여 386마리의 포켓몬 중 가장 닮은 파트너를 찾고, 
                AI로 세상에 단 하나뿐인 특별한 포켓몬을 만나보세요!
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <Link href="/intro" className="px-8 py-4 bg-pk-yellow text-pk-dark text-xl font-black rounded-lg border-b-4 border-pk-border hover:translate-y-1 hover:border-b-0 shadow-retro transition-all flex items-center justify-center gap-2">
                  <span>📸</span> SCAN FACE
                </Link>
                <Link href="/plaza" className="px-8 py-4 bg-white text-pk-dark text-xl font-black rounded-lg border-b-4 border-pk-border hover:translate-y-1 hover:border-b-0 shadow-retro transition-all flex items-center justify-center gap-2">
                  <span>🌍</span> VIEW PLAZA
                </Link>
              </div>
            </div>

            {/* Right: Retro Device Screen */}
            <div className="flex-1 w-full max-w-md">
              <div className="bg-pk-dark p-3 border-4 border-pk-border rounded-2xl shadow-retro rotate-2 hover:rotate-0 transition-transform duration-500">
                 <div className="bg-white aspect-[4/3] rounded-xl border-4 border-pk-border relative overflow-hidden flex items-center justify-center pokedex-screen-glare shadow-inner">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img 
                      src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${POKEMON_IDS[silIdx]}.png`}
                      alt="Pokemon Silhouette"
                      className={`w-72 h-72 md:w-80 md:h-80 object-contain z-10 transition-opacity duration-500 ${fade ? 'opacity-90' : 'opacity-0'} scale-150`}
                      style={{ filter: 'brightness(0)' }}
                    />
                    <div className={`absolute inset-0 flex items-center justify-center z-20 transition-opacity duration-500 ${fade ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
                      <span className="text-5xl md:text-6xl font-medium text-gray-300 drop-shadow-sm">?</span>
                    </div>
                    <div className="absolute top-3 right-3 flex gap-2 z-30">
                       <div className="w-3 h-3 bg-pk-red rounded-full animate-ping"></div>
                    </div>
                 </div>
                 
                 <div className="mt-4 px-2 flex justify-between items-center">
                    <div className="w-10 h-10 bg-pk-red rounded-full border-2 border-pk-border shadow-inner"></div>
                    <div className="flex gap-2">
                       <div className="w-16 h-3 bg-pk-blue rounded-full border border-pk-border"></div>
                       <div className="w-16 h-3 bg-pk-blue rounded-full border border-pk-border"></div>
                    </div>
                    <div className="w-12 h-12 bg-gray-300 rounded-full border-2 border-pk-border flex items-center justify-center shadow-inner">
                       <div className="w-8 h-8 bg-pk-dark rounded-full"></div>
                    </div>
                 </div>
              </div>
            </div>

          </div>
        </section>

        {/* ── HOW IT WORKS (User Journey) ── */}
        <section className="max-w-6xl mx-auto py-24 px-4 lg:px-8">
          <div className="text-center mb-16">
             <div className="inline-flex items-center gap-2 bg-white px-4 py-2 border-2 border-pk-border shadow-retro-sm mb-5">
               <span className="w-2.5 h-2.5 rounded-full bg-pk-red animate-pulse"></span>
               <span className="text-xs md:text-sm font-black tracking-[0.28em] text-pk-dark">SCAN • MATCH • EVOLVE</span>
             </div>
             <h2 className="text-4xl md:text-5xl font-black tracking-tight text-pk-dark mb-3">
               세 번의 선택이면<br className="sm:hidden" /> 파트너 완성
             </h2>
             <p className="text-pk-dark/60 font-bold text-sm md:text-base">처음이어도 한눈에 따라갈 수 있게 만들었습니다.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12 relative">
            {/* Connecting Line for Desktop */}
            <div className="hidden md:block absolute top-1/2 left-[10%] right-[10%] h-2 bg-pk-border z-0 -translate-y-1/2 border-y-2 border-white"></div>

            {JOURNEY_STEPS.map((step) => (
              <div
                key={step.stage}
                className="relative z-10 overflow-hidden border-4 border-pk-border bg-white shadow-retro transition-transform duration-300 hover:-translate-y-3"
              >
                <div className={`border-b-4 border-pk-border px-5 py-4 ${step.panelTone}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="inline-block bg-pk-red text-white text-[11px] font-black tracking-[0.2em] px-2.5 py-1 border-2 border-pk-border shadow-retro-sm">
                        {step.stage}
                      </div>
                      <h3 className="mt-4 text-2xl font-black text-pk-dark">{step.title}</h3>
                    </div>
                    <div className="flex h-14 w-14 items-center justify-center rounded-full border-4 border-pk-border bg-white text-3xl shadow-inner">
                      {step.icon}
                    </div>
                  </div>
                </div>

                <div className="px-5 py-5 text-left">
                  <p className="text-sm md:text-[15px] font-semibold leading-relaxed text-gray-700">
                    {step.description}
                  </p>

                  <div className="mt-5 flex items-center justify-between gap-3 border-t-2 border-dashed border-pk-border/30 pt-4">
                    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-black tracking-[0.18em] ${step.accentColor}`}>
                      {step.accent}
                    </span>
                    <span className="text-[11px] font-black tracking-[0.3em] text-pk-dark/45">
                      READY
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── PLAZA PREVIEW (Gallery) ── */}
        {samples.length > 0 && (
          <section id="plaza" className="bg-pk-dark py-24 px-4 lg:px-8 border-y-8 border-pk-border relative overflow-hidden">
            {/* Dot grid for dark section */}
            <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(rgba(255,255,255,0.1) 1px, transparent 1px)', backgroundSize: '24px 24px' }}></div>
            
            <div className="max-w-6xl mx-auto relative z-10">
              <div className="flex flex-col sm:flex-row items-center sm:items-end justify-between mb-12 gap-4 text-center sm:text-left">
                <div>
                  <h2 className="text-3xl md:text-4xl font-black text-pk-yellow tracking-tight mb-2">
                    다른 트레이너들이 발견한 <br className="sm:hidden" />
                    <span className="text-white">새로운 포켓몬들</span>
                  </h2>
                  <p className="text-white/60 font-bold text-sm">지금 이 순간에도 새로운 포켓몬이 탄생하고 있습니다.</p>
                </div>
                <Link href="/plaza" className="bg-white text-pk-dark font-black px-6 py-3 border-2 border-pk-border hover:bg-pk-yellow transition-colors shadow-retro-sm whitespace-nowrap">
                  도감 전체 구경하기 →
                </Link>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {samples.map((item, idx) => (
                  <Link href={`/creatures/${item.id}`} key={item.id} className="block group">
                    <div className="bg-white p-3 border-4 border-pk-border rounded-xl group-hover:-translate-y-2 transition-transform duration-300 shadow-retro">
                      <div className="bg-white aspect-square border-4 border-pk-border rounded-lg mb-3 relative overflow-hidden">
                         <div className="pokedex-screen-glare absolute inset-0 z-10 pointer-events-none"></div>
                         {/* eslint-disable-next-line @next/next/no-img-element */}
                         <img src={item.image_url || ""} alt={item.name} className="w-full h-full object-contain p-4 group-hover:scale-110 transition-transform duration-500" />
                         <div className="absolute bottom-0 left-0 bg-pk-dark text-white text-[10px] px-2 py-1 font-mono font-bold z-20">
                            No.{String(idx + 1).padStart(3, '0')}
                         </div>
                      </div>
                      <div className="px-1">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-black text-lg truncate pr-2">{item.name}</span>
                          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shrink-0"></div>
                        </div>
                        {/* HP Bar */}
                        <div className="flex items-center gap-2 mb-2">
                           <span className="text-[10px] font-black text-gray-500">LV.{Math.floor(Math.random() * 50) + 10}</span>
                           <div className="flex-1 h-2.5 bg-gray-200 border-2 border-pk-border rounded-full overflow-hidden">
                              <div className="h-full bg-green-500" style={{ width: `${Math.floor(Math.random() * 40) + 60}%` }}></div>
                           </div>
                        </div>
                        <p className="text-xs font-medium text-gray-600 line-clamp-2 leading-tight">
                          {item.story}
                        </p>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* ── BOTTOM CTA ── */}
        <section className="py-32 px-4 text-center">
          <div className="max-w-2xl mx-auto bg-pk-yellow p-8 md:p-12 border-4 border-pk-border rounded-2xl shadow-[12px_12px_0_0_rgba(0,0,0,1)] hover:shadow-[8px_8px_0_0_rgba(0,0,0,1)] hover:translate-x-1 hover:translate-y-1 transition-all">
            <h2 className="text-4xl md:text-5xl font-black mb-6 leading-tight">
              당신을 기다리고 있는 <br/> <span className="text-pk-red">첫 번째 파트너</span>를 만나볼까요?
            </h2>
            <Link href="/intro" className="inline-flex bg-pk-red text-white text-xl md:text-2xl font-black px-10 py-5 rounded-xl border-b-8 border-pk-border hover:border-b-4 hover:translate-y-1 active:border-b-0 active:translate-y-2 transition-all items-center justify-center gap-3">
               포켓몬 매칭 시작하기 <span>🚀</span>
            </Link>
            <p className="mt-6 font-mono text-sm font-bold opacity-60 tracking-widest">
              무료로 시작할 수 있습니다
            </p>
          </div>
        </section>

      </main>

      {/* ── FOOTER ── */}
      <footer className="bg-pk-dark py-8 border-t-8 border-pk-border text-center">
        <p className="text-white/50 text-xs font-mono font-bold tracking-widest">
          © 2026 POCKETMAN PROJECT.<br className="md:hidden" /> ALL SYSTEMS NORMAL.
        </p>
      </footer>

    </div>
  )
}
