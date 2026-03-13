"use client";

// 팔레트 타운 CSS 일러스트 (모바일 로그인/가입 상단 배경)
// 색상 출처: docs/기획/프론트엔드/implementation_strategy/02_stage_f2_result_generation.md
export default function PaletteTownScene() {
  return (
    <div
      className="relative w-full h-full overflow-hidden"
      style={{ backgroundColor: "#2DA2A0" }}
      aria-hidden="true"
    >
      {/* 구름 1 */}
      <div
        className="absolute top-[12%] animate-cloud-move"
        style={{ animationDuration: "8s" }}
      >
        <Cloud />
      </div>

      {/* 구름 2 (느린 속도, 다른 높이) */}
      <div
        className="absolute top-[25%] animate-cloud-move opacity-80"
        style={{ animationDuration: "12s", animationDelay: "-5s" }}
      >
        <Cloud small />
      </div>

      {/* 땅 */}
      <div
        className="absolute bottom-0 left-0 right-0 h-[38%]"
        style={{ backgroundColor: "#4A992D" }}
      />

      {/* 도로 */}
      <div
        className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[18%] h-[38%]"
        style={{ backgroundColor: "#C8B89A" }}
      />

      {/* Oak 연구소 */}
      <div className="absolute bottom-[37%] left-[8%]">
        <Building wide roofColor="#C8A43E" wallColor="#EDE8D8" />
      </div>

      {/* 주인공 집 */}
      <div className="absolute bottom-[37%] right-[12%]">
        <Building roofColor="#C03028" wallColor="#EDE8D8" />
      </div>

      {/* 나무들 */}
      <div className="absolute bottom-[36%] left-[30%]"><Tree /></div>
      <div className="absolute bottom-[36%] left-[38%]"><Tree dark /></div>
      <div className="absolute bottom-[36%] right-[28%]"><Tree /></div>

      {/* 피카츄 */}
      <div className="absolute bottom-[38%] left-1/2 -translate-x-1/2">
        <PikachuIcon />
      </div>

      {/* Pidgey */}
      <div
        className="absolute top-[30%] left-[10%] animate-pidgey-fly"
        style={{ animationDuration: "6s" }}
      >
        <PidgeyIcon />
      </div>
    </div>
  );
}

function Cloud({ small = false }: { small?: boolean }) {
  const size = small ? "scale-75" : "";
  return (
    <div className={`flex items-end gap-1 ${size}`}>
      <div className="w-8 h-5 rounded-full bg-white/90" />
      <div className="w-12 h-7 rounded-full bg-white/90 -ml-3" />
      <div className="w-8 h-5 rounded-full bg-white/90 -ml-3" />
    </div>
  );
}

function Building({ wide = false, roofColor, wallColor }: { wide?: boolean; roofColor: string; wallColor: string }) {
  const w = wide ? "w-20" : "w-12";
  return (
    <div className={`flex flex-col items-center ${w}`}>
      {/* 지붕 */}
      <div
        className="w-full h-0"
        style={{
          borderLeft: `${wide ? "40px" : "24px"} solid transparent`,
          borderRight: `${wide ? "40px" : "24px"} solid transparent`,
          borderBottom: `20px solid ${roofColor}`,
        }}
      />
      {/* 벽 */}
      <div
        className="w-full"
        style={{ height: wide ? "36px" : "28px", backgroundColor: wallColor }}
      >
        {/* 창문 */}
        <div className="flex justify-center gap-1 pt-1">
          <div className="w-2 h-2 bg-sky-300/70 rounded-sm" />
          {wide && <div className="w-2 h-2 bg-sky-300/70 rounded-sm" />}
        </div>
      </div>
    </div>
  );
}

function Tree({ dark = false }: { dark?: boolean }) {
  const color = dark ? "#1B584E" : "#4A992D";
  const trunk = "#8B5E3C";
  return (
    <div className="flex flex-col items-center">
      <div
        className="w-8 h-9 rounded-t-full"
        style={{ backgroundColor: color }}
      />
      <div
        className="w-2 h-3"
        style={{ backgroundColor: trunk }}
      />
    </div>
  );
}

function PikachuIcon() {
  return (
    <div className="relative w-10 h-10 flex items-center justify-center">
      {/* 몸 */}
      <div className="w-8 h-6 rounded-full bg-yellow-300 absolute bottom-0" />
      {/* 귀 */}
      <div className="w-2 h-4 bg-yellow-300 absolute top-0 left-1 rounded-t-full" style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }} />
      <div className="w-2 h-4 bg-yellow-300 absolute top-0 right-1 rounded-t-full" style={{ clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)" }} />
      {/* 꼬리 */}
      <div
        className="absolute -right-3 bottom-1 w-4 h-2 bg-yellow-300 rounded-full origin-left animate-pikachu-tail"
        style={{ transform: "rotate(-20deg)" }}
      />
      {/* 눈 */}
      <div className="absolute top-2 left-2 w-1 h-1 bg-gray-800 rounded-full" />
      <div className="absolute top-2 right-2 w-1 h-1 bg-gray-800 rounded-full" />
      {/* 볼 */}
      <div className="absolute bottom-2 left-1.5 w-1.5 h-1 bg-red-400 rounded-full opacity-70" />
      <div className="absolute bottom-2 right-1.5 w-1.5 h-1 bg-red-400 rounded-full opacity-70" />
    </div>
  );
}

function PidgeyIcon() {
  return (
    <div className="w-5 h-4 relative">
      <div className="w-4 h-3 rounded-full bg-amber-300 absolute bottom-0" />
      <div className="w-2 h-2 rounded-full bg-amber-200 absolute top-0 right-0" />
      {/* 날개 (애니메이션으로 표현) */}
      <div className="w-3 h-1 bg-amber-400 rounded-full absolute top-1 left-0 origin-right animate-pidgey-fly" />
    </div>
  );
}
