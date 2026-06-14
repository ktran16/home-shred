"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/plan", label: "Plan" },
  { href: "/exercises", label: "Exercises" },
  { href: "/progress", label: "Progress" },
  { href: "/nutrition", label: "Nutrition" },
  { href: "/profile", label: "Profile" },
];

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="sticky bottom-0 z-10 mx-auto grid w-full max-w-5xl grid-cols-6 border-t border-zinc-200 bg-white/95 px-1 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95">
      {LINKS.map((l) => {
        const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            className={cn(
              "flex min-h-[58px] flex-col items-center justify-center rounded-lg text-[11px] font-medium transition-colors sm:text-xs",
              active
                ? "text-emerald-700 dark:text-emerald-400"
                : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100",
            )}
          >
            <span
              className={cn(
                "mb-1 h-1.5 w-1.5 rounded-full",
                active ? "bg-emerald-600 dark:bg-emerald-400" : "bg-transparent",
              )}
            />
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
