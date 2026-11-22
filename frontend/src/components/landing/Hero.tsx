"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import HeroVisualization from "./HeroVisualization";
import BeforeAfter from "./BeforeAfter";

const ROTATION_MS = 4200;

export default function Hero() {
  const [showAfter, setShowAfter] = useState(false);

  useEffect(() => {
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  if (prefersReducedMotion) {
    return;
  }

  const interval = window.setInterval(() => {
    setShowAfter((previous) => !previous);
  }, ROTATION_MS);

  return () => window.clearInterval(interval);
}, []);

  return (
    <section className="relative overflow-hidden bg-[#08090D] pb-24 pt-36 sm:pb-32 sm:pt-44">
      {/* Ambient atmosphere */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-[-180px] h-[620px] w-[900px] -translate-x-1/2 rounded-full bg-[#7C5CFF]/10 blur-[140px] animate-[pulse_8s_ease-in-out_infinite]"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-[15%] top-[20%] h-64 w-64 rounded-full bg-[#67E8F9]/[0.035] blur-[110px] animate-[pulse_11s_ease-in-out_infinite]"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-[10%] top-[32%] h-72 w-72 rounded-full bg-[#A78BFA]/[0.04] blur-[120px] animate-[pulse_13s_ease-in-out_infinite]"
      />

      {/* Fine background grid */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.045] [background-image:linear-gradient(to_right,#fff_1px,transparent_1px),linear-gradient(to_bottom,#fff_1px,transparent_1px)] [background-size:64px_64px] [mask-image:radial-gradient(ellipse_at_top,black_25%,transparent_75%)]"
      />

      <div className="relative mx-auto max-w-7xl px-5 sm:px-6 lg:px-8">
        {/* Hero copy */}
        <div className="mx-auto max-w-4xl text-center">
          <div className="animate-[heroFadeUp_700ms_cubic-bezier(0.16,1,0.3,1)_both]">
            <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-4 py-2 text-xs font-medium text-slate-300 shadow-[0_0_30px_rgba(124,92,255,0.08)] backdrop-blur-xl">
              <span className="relative flex h-5 w-5 items-center justify-center rounded-full bg-[#7C5CFF]/15">
                <span className="absolute h-2 w-2 animate-ping rounded-full bg-[#A78BFA]/50" />
                <Sparkles className="relative h-3 w-3 text-[#A78BFA]" />
              </span>

              AI-powered content intelligence
            </div>
          </div>

          <h1
            className="mt-7 text-balance text-[clamp(2.7rem,7vw,5.8rem)] font-semibold leading-[0.98] tracking-[-0.045em] text-white animate-[heroFadeUp_800ms_120ms_cubic-bezier(0.16,1,0.3,1)_both]"
          >
            Understand your website.
            <br />
            <span className="bg-gradient-to-r from-[#A78BFA] via-[#7C5CFF] to-[#67E8F9] bg-clip-text text-transparent">
              Rewrite it with confidence.
            </span>
          </h1>

          <p className="mx-auto mt-7 max-w-2xl text-balance text-base leading-7 text-slate-400 sm:text-lg sm:leading-8 animate-[heroFadeUp_800ms_260ms_cubic-bezier(0.16,1,0.3,1)_both]">
            Verbly analyzes your site&apos;s SEO, readability, grammar, and
            content quality, then shows you exactly what to improve before you
            publish a single word.
          </p>

          {/* CTA buttons */}
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row animate-[heroFadeUp_800ms_380ms_cubic-bezier(0.16,1,0.3,1)_both]">
            <Link
              href="#get-started"
              className="group relative inline-flex min-w-[190px] items-center justify-center gap-2 overflow-hidden rounded-xl bg-[#7C5CFF] px-6 py-3.5 text-sm font-semibold text-white shadow-[0_10px_35px_rgba(124,92,255,0.22)] transition-all duration-300 hover:-translate-y-1 hover:bg-[#896EFF] hover:shadow-[0_16px_45px_rgba(124,92,255,0.34)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0"
            >
              <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
              <span className="relative">Analyze your site</span>
              <ArrowRight className="relative h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>

            <Link
              href="#product"
              className="inline-flex min-w-[170px] items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] px-6 py-3.5 text-sm font-medium text-slate-200 backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0"
            >
              See how it works
            </Link>
          </div>
        </div>

        {/* Content intelligence visualization */}
        <div className="relative mx-auto mt-20 max-w-6xl animate-[heroReveal_1000ms_520ms_cubic-bezier(0.16,1,0.3,1)_both] sm:mt-24">
          <HeroVisualization />
        </div>

        {/* Before / After */}
        <div
          className="relative mx-auto mt-20 max-w-5xl sm:mt-28"
          id="before-after"
        >
          <div className="mb-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#A78BFA]">
              From friction to clarity
            </p>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
              See what changes when Verbly gets involved.
            </h2>
          </div>

          <BeforeAfter showAfter={showAfter} />
        </div>
      </div>

      <style jsx>{`
        @keyframes heroFadeUp {
          from {
            opacity: 0;
            transform: translateY(28px);
          }

          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes heroReveal {
          from {
            opacity: 0;
            transform: translateY(35px) scale(0.97);
          }

          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }

        @media (prefers-reduced-motion: reduce) {
          div,
          h1,
          p,
          a {
            animation: none !important;
            transition: none !important;
          }
        }
      `}</style>
    </section>
  );
}