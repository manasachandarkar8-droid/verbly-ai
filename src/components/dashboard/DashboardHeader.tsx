"use client";

import Link from "next/link";
import { ArrowLeft, Sparkles } from "lucide-react";

export default function DashboardHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#08090D]/75 backdrop-blur-2xl">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-6 lg:px-8">
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

        {/* Dashboard context */}
        <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3.5 py-1.5 text-xs font-medium text-slate-400 sm:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-[#7C5CFF] shadow-[0_0_8px_rgba(124,92,255,0.7)]" />
          Dashboard
        </div>

        {/* Back to home */}
        <Link
          href="/"
          aria-label="Back to home"
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-4 py-2.5 text-sm font-medium text-slate-200 backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">Back to home</span>
        </Link>
      </div>
    </header>
  );
}