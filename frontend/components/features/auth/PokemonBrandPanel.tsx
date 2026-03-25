"use client";

// 데스크톱 로그인/가입 좌측 브랜딩 패널
// 포켓몬 스프라이트: frontend/public/images/ 에 아래 파일 저장 필요
//   login-pikachu.png    (Pikachu #025)
//   login-charmander.png (Charmander #004)
//   login-mewtwo.png     (Mewtwo #150)
// 다운로드: https://www.serebii.net/pokemongo/pokemon/025.png 등

const POKEMON = [
  {
    src: "/images/login-charmander.png",
    alt: "파이리",
    rotate: "rotate-[5deg]",
    eyesClass: "animate-eyes-look",
    blinkClass: "animate-eye-blink",
    delay: "1.5s",
    translate: "translate-y-2",
  },
  {
    src: "/images/login-pikachu.png",
    alt: "피카츄",
    rotate: "-rotate-[8deg]",
    eyesClass: "animate-eyes-look",
    blinkClass: "animate-eye-blink",
    delay: "0s",
    translate: "-translate-y-1",
  },
  {
    src: "/images/login-mewtwo.png",
    alt: "뮤츠",
    rotate: "-rotate-[3deg]",
    eyesClass: "animate-eyes-look",
    blinkClass: "animate-eye-blink",
    delay: "3s",
    translate: "translate-y-3",
  },
];

export default function PokemonBrandPanel() {
  return (
    <div
      className="relative flex h-full w-full flex-col items-center justify-center overflow-hidden"
      style={{
        background: "linear-gradient(135deg, #FFF5E1 0%, #FFD6B0 40%, #FF9B7A 100%)",
      }}
      aria-hidden="true"
    >
      {/* 오로라 오버레이 */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          background:
            "radial-gradient(ellipse at 30% 70%, #FFB347 0%, transparent 60%), " +
            "radial-gradient(ellipse at 70% 30%, #FF6B8A 0%, transparent 60%)",
        }}
      />

      {/* 로고 */}
      <p className="relative z-10 mb-10 text-2xl font-black tracking-widest text-white/90 drop-shadow">
        POCKETMAN
      </p>

      {/* 포켓몬 3장 부채꼴 */}
      <div className="relative z-10 flex items-end justify-center gap-2">
        {POKEMON.map((p) => (
          <div
            key={p.alt}
            className={`relative flex flex-col items-center ${p.rotate} ${p.translate} transition-transform duration-300 hover:scale-105`}
          >
            {/* 스프라이트 */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={p.src}
              alt={p.alt}
              width={96}
              height={96}
              className="h-24 w-24 object-contain drop-shadow-xl"
              style={{ imageRendering: "pixelated" }}
            />

            {/* 눈 애니메이션 오버레이 — 스프라이트 위에 투명 레이어 */}
            <div
              className={`absolute inset-0 ${p.eyesClass}`}
              style={{ animationDelay: p.delay }}
            />
            <div
              className={`absolute inset-0 ${p.blinkClass}`}
              style={{ animationDelay: p.delay }}
            />
          </div>
        ))}
      </div>

      <p className="relative z-10 mt-8 text-sm font-medium text-white/70">
        나와 닮은 포켓몬을 찾아보세요
      </p>
    </div>
  );
}
