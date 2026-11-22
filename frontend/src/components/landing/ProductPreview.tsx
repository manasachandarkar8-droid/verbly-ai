"use client";

import {
  BarChart3,
  CheckCircle2,
  FileText,
  Gauge,
  SpellCheck2,
} from "lucide-react";
import Reveal from "@/components/common/Reveal";

const METRICS = [
  { label: "SEO Score", value: 92, icon: BarChart3 },
  { label: "Readability", value: 88, icon: Gauge },
  { label: "Grammar", value: 97, icon: SpellCheck2 },
  { label: "Content Quality", value: 90, icon: FileText },
];

const SUGGESTIONS = [
  "Shorten the hero paragraph to improve clarity.",
  "Replace passive voice in the third section.",
  "Add a missing meta description for the pricing page.",
];

function ScoreRing({
  value,
  index,
}: {
  value: number;
  index: number;
}) {
  return (
    <div
      className="relative h-12 w-12 shrink-0 rounded-full opacity-0 animate-[ringReveal_700ms_cubic-bezier(0.16,1,0.3,1)_forwards]"
      style={{
        background: `conic-gradient(#7C5CFF ${value}%, rgba(255,255,255,0.07) 0)`,
        animationDelay: `${350 + index * 120}ms`,
      }}
    >
      <div className="absolute inset-[4px] flex items-center justify-center rounded-full bg-[#0D0F15]">
        <span className="text-[10px] font-semibold text-[#A78BFA]">
          {value}
        </span>
      </div>
    </div>
  );
}

export default function ProductPreview() {
  return (
    <section
      id="product"
      className="relative overflow-hidden bg-[#08090D] py-24 sm:py-32"
    >
      {/* Ambient dashboard glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-20 h-72 w-[700px] -translate-x-1/2 rounded-full bg-[#7C5CFF]/[0.07] blur-[120px]"
      />

      <div className="relative mx-auto max-w-6xl px-5 sm:px-6 lg:px-8">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#A78BFA]">
            Content intelligence
          </p>

          <h2 className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">
            See your site the way Verbly sees it.
          </h2>

          <p className="mt-4 text-base leading-7 text-slate-400">
            One intelligent workspace for every score, suggestion, and
            improvement.
          </p>
        </Reveal>

        <div className="relative mx-auto mt-14 max-w-5xl sm:mt-16">
          <Reveal
            delayMs={120}
            className="group relative overflow-hidden rounded-2xl border border-white/10 bg-[#0D0F15]/90 shadow-[0_30px_100px_rgba(0,0,0,0.45)] backdrop-blur-xl transition-all duration-500 hover:-translate-y-1 hover:border-[#7C5CFF]/25 hover:shadow-[0_35px_110px_rgba(0,0,0,0.55)]"
          >
            {/* Moving top highlight */}
            <div
              aria-hidden="true"
              className="pointer-events-none absolute left-[-30%] top-0 h-px w-[60%] bg-gradient-to-r from-transparent via-[#A78BFA] to-transparent opacity-60 transition-transform duration-[1800ms] ease-out group-hover:translate-x-[260%]"
            />

            {/* Browser chrome */}
            <div className="flex items-center gap-2 border-b border-white/[0.06] px-5 py-4">
              <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/10" />

              <div className="ml-3 rounded-md border border-white/[0.06] bg-white/[0.025] px-3 py-1 text-[10px] text-slate-400">
                verbly.ai / analysis
              </div>

              <div className="ml-auto hidden items-center gap-2 sm:flex">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                <span className="text-[10px] text-slate-400">
                  Analysis ready
                </span>
              </div>
            </div>

            {/* Metrics */}
            <div className="grid gap-px bg-white/[0.05] sm:grid-cols-2 lg:grid-cols-4">
              {METRICS.map((metric, index) => (
                <Reveal
                  key={metric.label}
                  delayMs={180 + index * 100}
                  className="bg-[#0D0F15] p-5 transition-colors duration-300 hover:bg-white/[0.025] sm:p-6"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-400">
                        {metric.label}
                      </p>

                      <p className="mt-2 text-2xl font-semibold tracking-tight text-white">
                        {metric.value}
                      </p>

                      <p className="mt-1 text-[10px] text-emerald-400/80">
                        Excellent
                      </p>
                    </div>

                    <ScoreRing value={metric.value} index={index} />
                  </div>
                </Reveal>
              ))}
            </div>

            {/* Suggestions */}
            <div className="border-t border-white/[0.06] p-5 sm:p-7">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Suggested improvements
                </p>

                <span className="rounded-full border border-[#7C5CFF]/20 bg-[#7C5CFF]/10 px-2.5 py-1 text-[10px] text-[#A78BFA]">
                  3 suggestions
                </span>
              </div>

              <ul className="mt-5 space-y-3">
                {SUGGESTIONS.map((suggestion, index) => (
                  <Reveal
                    key={suggestion}
                    delayMs={600 + index * 120}
                    className="group/item flex items-start gap-3 rounded-xl border border-transparent p-2 transition-all duration-300 hover:border-white/[0.06] hover:bg-white/[0.025]"
                  >
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#8B6FFF] transition-transform duration-300 group-hover/item:scale-110" />

                    <span className="text-sm leading-6 text-slate-300">
                      {suggestion}
                    </span>
                  </Reveal>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </div>

      <style jsx>{`
        @keyframes ringReveal {
          from {
            opacity: 0;
            transform: scale(0.65) rotate(-45deg);
          }

          to {
            opacity: 1;
            transform: scale(1) rotate(0deg);
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