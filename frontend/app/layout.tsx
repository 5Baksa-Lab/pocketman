import type { Metadata } from "next"
import { Header } from "@/components/layout/Header"
import { MobileNav } from "@/components/layout/MobileNav"
import "./globals.css"

export const metadata: Metadata = {
  title: "Pocketman — 내 얼굴을 닮은 포켓몬",
  description: "AI가 얼굴을 분석해 나만의 포켓몬 크리처를 만들어드립니다.",
}

// 초기 로드 시 localStorage의 theme/font_size를 플래시 없이 적용
const themeInitScript = `
(function(){
  try{
    var t=localStorage.getItem('theme');
    if(t==='dark'||(t==null&&window.matchMedia('(prefers-color-scheme:dark)').matches)){
      document.documentElement.classList.add('dark');
    }
    var f=localStorage.getItem('font_size');
    if(f)document.documentElement.style.fontSize=f+'px';
  }catch(e){}
})();
`.trim();

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      {/* eslint-disable-next-line @next/next/no-before-interactive-script-outside-document */}
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <div className="aurora aurora-a" aria-hidden />
        <div className="aurora aurora-b" aria-hidden />
        <Header />
        <main className="pb-20 lg:pb-0">{children}</main>
        <MobileNav />
      </body>
    </html>
  )
}
