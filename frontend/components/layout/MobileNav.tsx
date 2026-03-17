"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const TAB_ITEMS = [
  { href: "/", label: "홈", icon: "🏠" },
  { href: "/plaza", label: "광장", icon: "🌐" },
  { href: "/upload", label: "만들기", icon: "✨" },
]

export function MobileNav() {
  const pathname = usePathname()
  const hideChrome =
    pathname === "/" ||
    pathname === "/intro" ||
    pathname === "/plaza" ||
    pathname.startsWith("/generate/")

  if (hideChrome) {
    return null
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-ink/10 bg-base/95 backdrop-blur-md lg:hidden">
      <div className="flex items-center justify-around px-4 py-2">
        {TAB_ITEMS.map((item) => {
          const active = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-0.5 px-4 py-1 text-xs transition ${
                active ? "text-point" : "text-ink/60 hover:text-ink"
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
