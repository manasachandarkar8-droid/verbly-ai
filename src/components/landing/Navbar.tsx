"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Menu, X, Sparkles } from "lucide-react";

// "Pricing" and "FAQ" were removed: there is no corresponding section on this
// page (or anywhere else in the app) for either anchor, so both links were
// dead ends. Re-add once those sections exist.
const NAV_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#product", label: "Product" },
];

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#08090D]/75 backdrop-blur-2xl transition-all duration-700 ease-out motion-reduce:transition-none ${
        mounted
          ? "translate-y-0 opacity-100"
          : "-translate-y-5 opacity-0"
      }`}
    >
      <nav className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link
          href="/"
          className="group flex items-center gap-2.5 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#A78BFA]"
          aria-label="Verbly AI home"
        >
          <span className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-[#7C5CFF]/30 bg-[#7C5CFF]/10 transition-all duration-300 group-hover:scale-105 group-hover:border-[#7C5CFF]/60 group-hover:bg-[#7C5CFF]/15">
            <span className="absolute inset-0 rounded-xl bg-[#7C5CFF]/10 opacity-0 blur-md transition-opacity duration-300 group-hover:opacity-100" />
            <Sparkles className="relative h-[17px] w-[17px] text-[#A78BFA]" />
          </span>

          <span className="text-[19px] font-semibold tracking-tight text-white">
            Verbly<span className="text-[#8B6FFF]">AI</span>
          </span>
        </Link>

        {/* Desktop navigation */}
        <div className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="group relative rounded-sm py-2 text-sm text-slate-400 transition-colors duration-300 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]"
            >
              {link.label}

              <span
                aria-hidden="true"
                className="absolute bottom-0 left-1/2 h-px w-0 -translate-x-1/2 bg-[#8B6FFF] shadow-[0_0_8px_rgba(124,92,255,0.7)] transition-all duration-300 group-hover:w-full"
              />
            </Link>
          ))}
        </div>

        {/* Desktop actions */}
        <div className="hidden items-center gap-4 md:flex">
          <Link
            href="/dashboard"
            className="group relative overflow-hidden rounded-xl bg-[#7C5CFF] px-4 py-2.5 text-sm font-medium text-white shadow-[0_0_0_rgba(124,92,255,0)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#896EFF] hover:shadow-[0_8px_30px_rgba(124,92,255,0.28)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0"
          >
            <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
            <span className="relative">Get started</span>
          </Link>
        </div>

        {/* Mobile menu button */}
        <button
          type="button"
          onClick={() => setIsOpen((previous) => !previous)}
          className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 text-slate-300 transition-all duration-300 hover:border-[#7C5CFF]/40 hover:bg-white/[0.04] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] md:hidden"
          aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={isOpen}
        >
          <Menu
            className={`absolute h-5 w-5 transition-all duration-300 ${
              isOpen
                ? "rotate-90 scale-75 opacity-0"
                : "rotate-0 scale-100 opacity-100"
            }`}
          />

          <X
            className={`absolute h-5 w-5 transition-all duration-300 ${
              isOpen
                ? "rotate-0 scale-100 opacity-100"
                : "-rotate-90 scale-75 opacity-0"
            }`}
          />
        </button>
      </nav>

      {/* Mobile navigation */}
      <div
        className={`grid overflow-hidden border-t border-white/[0.06] bg-[#08090D]/95 backdrop-blur-2xl transition-[grid-template-rows,opacity] duration-400 ease-out md:hidden ${
          isOpen
            ? "grid-rows-[1fr] opacity-100"
            : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="flex flex-col gap-1 px-5 pb-6 pt-3">
            {NAV_LINKS.map((link, index) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                style={{
                  transitionDelay: isOpen ? `${index * 55}ms` : "0ms",
                }}
                className={`rounded-lg px-3 py-3 text-sm text-slate-300 transition-all duration-300 hover:bg-white/[0.04] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] ${
                  isOpen
                    ? "translate-x-0 opacity-100"
                    : "-translate-x-3 opacity-0"
                }`}
              >
                {link.label}
              </Link>
            ))}

            <div className="mt-3 flex flex-col gap-3 border-t border-white/[0.06] pt-4">
              <Link
                href="/dashboard"
                onClick={() => setIsOpen(false)}
                className="rounded-xl bg-[#7C5CFF] px-4 py-3 text-center text-sm font-medium text-white transition-all duration-300 hover:bg-[#896EFF] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]"
              >
                Get started
              </Link>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}