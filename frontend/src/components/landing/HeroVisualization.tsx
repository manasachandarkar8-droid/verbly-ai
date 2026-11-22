"use client";

import { useEffect, useState } from "react";
import {
  Check,
  FileText,
  Gauge,
  ScanSearch,
  Sparkles,
} from "lucide-react";

const SCORES = [
  { label: "SEO", value: 92 },
  { label: "Readability", value: 88 },
  { label: "Grammar", value: 97 },
  { label: "Quality", value: 90 },
];

const SUGGESTIONS = [
  "Make the opening sentence more direct.",
  "Improve the paragraph structure.",
  "Use clearer action-oriented wording.",
];

export default function HeroVisualization() {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const sequence = [
      window.setTimeout(() => setStage(1), 900),
      window.setTimeout(() => setStage(2), 1900),
      window.setTimeout(() => setStage(3), 3000),
      window.setTimeout(() => setStage(4), 4100),
    ];

    return () => {
      sequence.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  return (
    <div className="relative">
      {/* Outer ambient glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/2 h-[70%] w-[80%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#7C5CFF]/10 blur-[100px]"
      />

      {/* Main interface */}
      <div className="group relative overflow-hidden rounded-[24px] border border-white/[0.10] bg-[#0D0F15]/95 shadow-[0_40px_120px_rgba(0,0,0,0.55)] backdrop-blur-2xl transition-all duration-700 hover:border-[#7C5CFF]/25 hover:shadow-[0_45px_140px_rgba(0,0,0,0.65)]">
        {/* Animated top light */}
        <div
          aria-hidden="true"
          className="absolute left-[-20%] top-0 h-px w-[40%] bg-gradient-to-r from-transparent via-[#A78BFA] to-transparent opacity-70 animate-[visualSweep_5s_ease-in-out_infinite]"
        />

        {/* Browser header */}
        <div className="flex h-12 items-center border-b border-white/[0.06] px-4 sm:px-5">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
            <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
            <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
          </div>

          <div className="mx-auto flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.025] px-3 py-1">
            <Sparkles className="h-3 w-3 text-[#A78BFA]" />
            <span className="text-[10px] text-slate-400">
              Verbly Content Intelligence
            </span>
          </div>

          <div className="hidden items-center gap-2 sm:flex">
            <span
              className={`h-1.5 w-1.5 rounded-full transition-all duration-500 ${
                stage >= 3
                  ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]"
                  : "bg-[#7C5CFF]"
              }`}
            />

            <span className="text-[10px] text-slate-400">
              {stage >= 3 ? "Analysis ready" : "Analyzing"}
            </span>
          </div>
        </div>

        <div className="grid lg:grid-cols-[1.1fr_0.9fr]">
          {/* Content analysis side */}
          <div className="relative border-b border-white/[0.06] p-5 sm:p-7 lg:border-b-0 lg:border-r">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#A78BFA]">
                  Content input
                </p>

                <p className="mt-1 text-xs text-slate-400">
                  Homepage content
                </p>
              </div>

              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.06] bg-white/[0.025]">
                <FileText className="h-4 w-4 text-slate-400" />
              </div>
            </div>

            {/* Content document */}
            <div className="relative mt-6 overflow-hidden rounded-xl border border-white/[0.07] bg-[#08090D] p-5">
              {/* Scanning line */}
              <div
                aria-hidden="true"
                className={`pointer-events-none absolute left-0 right-0 z-10 h-px bg-gradient-to-r from-transparent via-[#7C5CFF] to-transparent transition-opacity duration-500 ${
                  stage >= 1 && stage < 3
                    ? "opacity-100 animate-[scanLine_1.8s_ease-in-out_infinite]"
                    : "opacity-0"
                }`}
              />

              <div className="space-y-3">
                <div className="h-2.5 w-[86%] rounded-full bg-white/[0.08]" />
                <div className="h-2.5 w-[94%] rounded-full bg-white/[0.055]" />
                <div className="h-2.5 w-[72%] rounded-full bg-white/[0.055]" />

                <div className="h-4" />

                <div
                  className={`h-2.5 rounded-full transition-all duration-700 ${
                    stage >= 1
                      ? "w-[80%] bg-[#7C5CFF]/30"
                      : "w-[60%] bg-white/[0.055]"
                  }`}
                />

                <div
                  className={`h-2.5 rounded-full transition-all duration-700 delay-100 ${
                    stage >= 1
                      ? "w-[68%] bg-[#7C5CFF]/20"
                      : "w-[88%] bg-white/[0.055]"
                  }`}
                />

                <div className="h-2.5 w-[90%] rounded-full bg-white/[0.055]" />

                <div className="h-4" />

                <div className="h-2.5 w-[76%] rounded-full bg-white/[0.055]" />
                <div className="h-2.5 w-[58%] rounded-full bg-white/[0.055]" />
              </div>

              {/* Highlighted issue */}
              <div
                className={`absolute bottom-5 left-5 h-7 rounded-md border border-[#7C5CFF]/30 bg-[#7C5CFF]/10 transition-all duration-700 ${
                  stage >= 2
                    ? "w-[62%] opacity-100"
                    : "w-0 opacity-0"
                }`}
              />
            </div>

            {/* Analysis status */}
            <div className="mt-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ScanSearch
                  className={`h-4 w-4 transition-colors duration-500 ${
                    stage >= 3 ? "text-emerald-400" : "text-[#8B6FFF]"
                  }`}
                />

                <span className="text-xs text-slate-400">
                  {stage >= 3
                    ? "Content intelligence complete"
                    : stage >= 1
                      ? "Scanning content..."
                      : "Preparing analysis..."}
                </span>
              </div>

              <span className="text-[10px] text-slate-600">
                {stage >= 3 ? "100%" : stage >= 2 ? "68%" : "32%"}
              </span>
            </div>

            <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.05]">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#7C5CFF] to-[#67E8F9] transition-all duration-1000 ease-out"
                style={{
                  width:
                    stage >= 3
                      ? "100%"
                      : stage >= 2
                        ? "68%"
                        : stage >= 1
                          ? "42%"
                          : "12%",
                }}
              />
            </div>
          </div>

          {/* Intelligence results */}
          <div className="p-5 sm:p-7">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#A78BFA]">
                  Intelligence
                </p>

                <p className="mt-1 text-xs text-slate-400">
                  Live content signals
                </p>
              </div>

              <div
                className={`flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-500 ${
                  stage >= 3
                    ? "border-emerald-400/20 bg-emerald-400/10"
                    : "border-[#7C5CFF]/20 bg-[#7C5CFF]/10"
                }`}
              >
                <Gauge
                  className={`h-4 w-4 transition-colors duration-500 ${
                    stage >= 3 ? "text-emerald-400" : "text-[#A78BFA]"
                  }`}
                />
              </div>
            </div>

            {/* Scores */}
            <div className="mt-6 grid grid-cols-2 gap-2.5">
              {SCORES.map((score, index) => (
                <div
                  key={score.label}
                  className={`rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 transition-all duration-700 ${
                    stage >= 3
                      ? "translate-y-0 opacity-100"
                      : "translate-y-3 opacity-40"
                  }`}
                  style={{
                    transitionDelay: `${index * 120}ms`,
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-slate-400">
                      {score.label}
                    </span>

                    <span className="text-sm font-semibold text-white">
                      {stage >= 3 ? score.value : "—"}
                    </span>
                  </div>

                  <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.06]">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[#7C5CFF] to-[#A78BFA] transition-all duration-1000"
                      style={{
                        width: stage >= 3 ? `${score.value}%` : "0%",
                        transitionDelay: `${index * 100}ms`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Suggestions */}
            <div className="mt-5 rounded-xl border border-white/[0.06] bg-white/[0.018] p-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  Improvements
                </span>

                <span
                  className={`text-[10px] transition-all duration-500 ${
                    stage >= 4
                      ? "text-emerald-400"
                      : "text-slate-600"
                  }`}
                >
                  {stage >= 4 ? "3 found" : "Scanning"}
                </span>
              </div>

              <div className="mt-3 space-y-2.5">
                {SUGGESTIONS.map((suggestion, index) => (
                  <div
                    key={suggestion}
                    className={`flex items-start gap-2 transition-all duration-500 ${
                      stage >= 4
                        ? "translate-x-0 opacity-100"
                        : "translate-x-2 opacity-0"
                    }`}
                    style={{
                      transitionDelay: `${index * 120}ms`,
                    }}
                  >
                    <span className="mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#7C5CFF]/15">
                      <Check className="h-2.5 w-2.5 text-[#A78BFA]" />
                    </span>

                    <span className="text-[11px] leading-5 text-slate-400">
                      {suggestion}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Completion state */}
            <div
              className={`mt-4 flex items-center gap-2 rounded-lg border px-3 py-2 transition-all duration-700 ${
                stage >= 4
                  ? "border-emerald-400/15 bg-emerald-400/[0.05] opacity-100"
                  : "border-white/[0.05] bg-white/[0.02] opacity-50"
              }`}
            >
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full transition-colors duration-500 ${
                  stage >= 4
                    ? "bg-emerald-400/15"
                    : "bg-white/[0.05]"
                }`}
              >
                <Check
                  className={`h-3 w-3 transition-colors duration-500 ${
                    stage >= 4
                      ? "text-emerald-400"
                      : "text-slate-600"
                  }`}
                />
              </span>

              <span className="text-[10px] text-slate-400">
                {stage >= 4
                  ? "Ready to improve your content"
                  : "Building your content profile..."}
              </span>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes scanLine {
          0% {
            top: 0%;
            opacity: 0;
          }

          15% {
            opacity: 1;
          }

          85% {
            opacity: 1;
          }

          100% {
            top: 100%;
            opacity: 0;
          }
        }

        @keyframes visualSweep {
          0% {
            transform: translateX(0);
            opacity: 0;
          }

          15% {
            opacity: 0.7;
          }

          50% {
            transform: translateX(350%);
            opacity: 0.8;
          }

          70% {
            opacity: 0;
          }

          100% {
            transform: translateX(350%);
            opacity: 0;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          div {
            animation: none !important;
          }
        }
      `}</style>
    </div>
  );
}