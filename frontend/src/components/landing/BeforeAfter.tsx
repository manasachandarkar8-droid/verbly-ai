"use client";

interface BeforeAfterProps {
  showAfter: boolean;
}

const BEFORE_TEXT =
  "Our platform helps users to be able to do things faster and also more efficiently than before, which is good for productivity.";

const AFTER_TEXT =
  "Our platform helps you move faster, with fewer steps and less friction.";

export default function BeforeAfter({ showAfter }: BeforeAfterProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0D0F15]/90 p-6 shadow-[0_25px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-8">
      {/* Animated scanning glow */}
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-y-0 w-px bg-gradient-to-b from-transparent via-[#7C5CFF] to-transparent blur-[1px] transition-all duration-[1400ms] ease-in-out ${
          showAfter ? "left-[92%]" : "left-[8%]"
        }`}
      />

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full transition-all duration-500 ${
              showAfter
                ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.7)]"
                : "bg-slate-500"
            }`}
          />

          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
            {showAfter ? "After Verbly" : "Before Verbly"}
          </span>
        </div>

        <span className="rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[10px] font-medium text-slate-400">
          {showAfter ? "Optimized" : "Original"}
        </span>
      </div>

      {/* Content */}
      <div className="relative min-h-[105px]">
        <p
          aria-hidden={showAfter}
          className={`absolute inset-0 text-sm leading-7 text-slate-300 transition-all duration-500 ease-out sm:text-base sm:leading-8 ${
            showAfter
              ? "-translate-y-3 opacity-0"
              : "translate-y-0 opacity-100"
          }`}
        >
          {BEFORE_TEXT}
        </p>

        <p
          aria-hidden={!showAfter}
          className={`absolute inset-0 text-sm leading-7 text-slate-200 transition-all duration-500 ease-out sm:text-base sm:leading-8 ${
            showAfter
              ? "translate-y-0 opacity-100"
              : "translate-y-3 opacity-0"
          }`}
        >
          {AFTER_TEXT}
        </p>
      </div>

      {/* Bottom status */}
      <div className="mt-6 flex items-center gap-3 border-t border-white/[0.06] pt-5">
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
          <div
            className={`h-full rounded-full bg-gradient-to-r from-[#7C5CFF] to-[#67E8F9] transition-all duration-700 ease-out ${
              showAfter ? "w-full" : "w-[42%]"
            }`}
          />
        </div>

        <span className="text-[10px] font-medium text-slate-400">
          {showAfter ? "Clarity improved" : "Needs improvement"}
        </span>
      </div>
    </div>
  );
}