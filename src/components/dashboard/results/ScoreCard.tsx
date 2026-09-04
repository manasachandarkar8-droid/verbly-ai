"use client";

import type { LucideIcon } from "lucide-react";
import { useCountUp } from "@/lib/use-count-up";

interface ScoreCardProps {
  icon: LucideIcon;
  label: string;
  score: number;
  summary: string;
  /** Stagger the entrance/count-up animation across a grid of cards. */
  animationDelayMs?: number;
  /**
   * Optional. If provided, the card becomes an interactive control that jumps
   * to this category's findings (e.g. scroll + tab selection).
   */
  onSelect?: () => void;
}

function tierColor(score: number): { text: string; bar: string; ring: string } {
  if (score >= 85) {
    return {
      text: "text-emerald-400",
      bar: "from-emerald-400 to-[#67E8F9]",
      ring: "shadow-[0_0_20px_rgba(52,211,153,0.18)]",
    };
  }
  if (score >= 70) {
    return {
      text: "text-[#A78BFA]",
      bar: "from-[#7C5CFF] to-[#67E8F9]",
      ring: "shadow-[0_0_20px_rgba(124,92,255,0.18)]",
    };
  }
  if (score >= 50) {
    return {
      text: "text-amber-400",
      bar: "from-amber-400 to-[#7C5CFF]",
      ring: "shadow-[0_0_20px_rgba(251,191,36,0.16)]",
    };
  }
  return {
    text: "text-red-400",
    bar: "from-red-400 to-amber-400",
    ring: "shadow-[0_0_20px_rgba(248,113,113,0.16)]",
  };
}

export default function ScoreCard({
  icon: Icon,
  label,
  score,
  summary,
  animationDelayMs = 0,
  onSelect,
}: ScoreCardProps) {
  const animatedScore = useCountUp(score, { durationMs: 1000, delayMs: animationDelayMs });
  const colors = tierColor(score);

  const baseClassName = `group relative w-full overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-left backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.05] ${colors.ring}`;
  const interactiveClassName = `${baseClassName} cursor-pointer focus-visible:-translate-y-1 focus-visible:border-[#A78BFA]/50 focus-visible:bg-white/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]`;

  const content = (
    <>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full bg-[#7C5CFF]/[0.06] blur-2xl transition-opacity duration-300 group-hover:opacity-100"
      />

      <div className="relative flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-slate-300 transition-colors duration-300 group-hover:text-[#A78BFA]">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
          <h3 className="text-sm font-semibold tracking-tight text-white">{label}</h3>
        </div>

        <span className={`text-2xl font-semibold tabular-nums tracking-tight ${colors.text}`}>
          {animatedScore}
        </span>
      </div>

      <div
        className="relative mt-4 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]"
        role="progressbar"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} score`}
      >
        <div
          className={`h-full rounded-full bg-gradient-to-r ${colors.bar} transition-[width] duration-1000 ease-out`}
          style={{ width: `${animatedScore}%` }}
        />
      </div>

      <p className="relative mt-3 text-xs leading-5 text-slate-400">{summary}</p>

      {onSelect && (
        // Persistent at low opacity so touch users (who never trigger :hover
        // or :focus) still see this card is actionable; hover/focus still
        // bring it to full strength as before.
        <span className="relative mt-3 flex items-center gap-1 text-[11px] font-medium text-slate-400 opacity-60 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100">
          View findings →
        </span>
      )}
    </>
  );

  if (onSelect) {
    return (
      <button
        type="button"
        onClick={onSelect}
        aria-label={`View findings for ${label}`}
        className={interactiveClassName}
      >
        {content}
      </button>
    );
  }

  return <div className={baseClassName}>{content}</div>;
}