import type { Metadata } from "next"
import { Header } from "@/components/layout/Header"
import { MobileNav } from "@/components/layout/MobileNav"
import "./globals.css"

export const metadata: Metadata = {
  title: "Pocketman — 내 얼굴을 닮은 포켓몬",
  description: "AI가 얼굴을 분석해 나만의 포켓몬 크리처를 만들어드립니다.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
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
