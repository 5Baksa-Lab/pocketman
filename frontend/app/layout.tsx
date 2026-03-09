import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "Pocketman Frontend",
  description: "업로드-매칭-생성-공유-광장 피드 프론트엔드"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <div className="aurora aurora-a" aria-hidden />
        <div className="aurora aurora-b" aria-hidden />

        <header className="sticky top-0 z-50 border-b border-white/20 bg-base/85 backdrop-blur-md">
          <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4">
            <Link href="/" className="brand text-ink">
              POCKETMAN
            </Link>
            <nav className="flex gap-2">
              <Link href="/" className="nav-pill">
                매칭/생성
              </Link>
              <Link href="/plaza" className="nav-pill">
                광장 피드
              </Link>
            </nav>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-8">{children}</main>
      </body>
    </html>
  );
}
