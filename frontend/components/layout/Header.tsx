"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

export function Header() {
  const pathname = usePathname()
  const isLanding = pathname === "/"
  const hideChrome =
    pathname === "/" ||
    pathname === "/intro" ||
    pathname === "/plaza" ||
    pathname.startsWith("/generate/")

  if (hideChrome) {
    return null
  }

  return (
    <header className="sticky top-0 z-50 border-b border-white/20 bg-base/85 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="brand text-ink">
          POCKETMAN
        </Link>
        <nav className="flex items-center gap-2">
          <Link
            href="/plaza"
            className={`nav-pill ${pathname === "/plaza" ? "border-point text-point" : ""}`}
          >
            광장
          </Link>
          {isLanding ? null : (
            <Link
              href="/"
              className="rounded-full bg-point px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
            >
              새 크리처 만들기
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
