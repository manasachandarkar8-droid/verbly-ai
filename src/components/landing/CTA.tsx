"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

export default function CTA() {
  return (
    <section
      id="get-started"
      className="relative overflow-hidden bg-[#08090D] px-5 py-24 sm:px-6 sm:py-32 lg:px-8"
    >
      {/* Atmospheric glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/2 h-[420px] w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#7C5CFF]/10 blur-[130px] animate-[ctaGlow_8s_ease-in-out_infinite]"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.035] [background-image:linear-gradient(to_right,#fff_1px,transparent_1px),linear-gradient(to_bottom,#fff_1px,transparent_1px)] [background-size:56px_56px]"
      />

      <div className="relative mx-auto max-w-4xl">
        <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-gradient-to-br from-white/[0.07] via-white/[0.035] to-[#7C5CFF]/[0.05] px-6 py-14 text-center shadow-[0_30px_100px_rgba(0,0,0,0.45)] backdrop-blur-xl sm:px-12 sm:py-20">
          {/* Inner light sweep */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -left-1/2 top-0 h-px w-[200%] bg-gradient-to-r from-transparent via-[#A78BFA]/60 to-transparent animate-[ctaSweep_6s_ease-in-out_infinite]"
          />

          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-[#7C5CFF]/20 bg-[#7C5CFF]/10 px-3.5 py-1.5 text-xs font-medium text-[#C4B5FD]">
            <Sparkles className="h-3.5 w-3.5" />
            Start with clarity
          </div>

          <h2 className="mx-auto mt-6 max-w-3xl text-balance text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl lg:text-5xl">
            Turn your website into{" "}
            <span className="bg-gradient-to-r from-[#A78BFA] via-[#7C5CFF] to-[#67E8F9] bg-clip-text text-transparent">
              clearer, stronger content.
            </span>
          </h2>

          <p className="mx-auto mt-5 max-w-xl text-balance text-sm leading-7 text-slate-400 sm:text-base">
            Find the problems that matter, understand why they matter, and
            improve your content with confidence.
          </p>

          <div className="mt-9">
            <Link
              href="/dashboard"
              className="group relative inline-flex items-center gap-2 overflow-hidden rounded-xl bg-[#7C5CFF] px-6 py-3.5 text-sm font-semibold text-white shadow-[0_12px_35px_rgba(124,92,255,0.25)] transition-all duration-300 hover:-translate-y-1 hover:bg-[#896EFF] hover:shadow-[0_18px_50px_rgba(124,92,255,0.38)] active:translate-y-0"
            >
              <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />

              <span className="relative">Analyze your site</span>

              <ArrowRight className="relative h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes ctaGlow {
          0%,
          100% {
            opacity: 0.45;
            transform: translate(-50%, -50%) scale(1);
          }

          50% {
            opacity: 0.8;
            transform: translate(-50%, -50%) scale(1.08);
          }
        }

        @keyframes ctaSweep {
          0% {
            transform: translateX(-20%);
            opacity: 0;
          }

          20% {
            opacity: 1;
          }

          50% {
            transform: translateX(20%);
            opacity: 0.7;
          }

          100% {
            transform: translateX(20%);
            opacity: 0;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          div {
            animation: none !important;
          }
        }
      `}</style>
    </section>
  );
}