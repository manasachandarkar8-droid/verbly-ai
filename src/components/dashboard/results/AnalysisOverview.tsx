"use client";

import { ArrowRight, BookOpen, FileText, SpellCheck2, Search, Target } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AnalysisCategoryId, AnalysisResult } from "@/lib/analysis/types";
import { useCountUp } from "@/lib/use-count-up";
import ScoreCard from "./ScoreCard";

interface AnalysisOverviewProps {
  result: AnalysisResult;
  /** Optional. When provided, category cards become interactive and jump to that category's findings. */
  onCategorySelect?: (category: AnalysisCategoryId) => void;
}

const CATEGORY_ICON: Record<AnalysisCategoryId, LucideIcon> = {
  seo: Search,
  readability: BookOpen,
  grammar: SpellCheck2,
  "content-quality": FileText,
};

const CATEGORY_LABEL: Record<AnalysisCategoryId, string> = {
  seo: "SEO",
  readability: "Readability",
  grammar: "Grammar",
  "content-quality": "Content quality",
};

function ringColorClass(score: number): string {
  if (score >= 85) return "text-emerald-400";
  if (score >= 70) return "text-[#A78BFA]";
  if (score >= 50) return "text-amber-400";
  return "text-red-400";
}

function overallHeadline(score: number): string {
  if (score >= 85) return "This site is in excellent shape.";
  if (score >= 70) return "This site is in good shape, with room to improve.";
  if (score >= 50) return "This site has some clear opportunities to improve.";
  return "This site needs meaningful improvement.";
}

// Same tier boundary used everywhere else on this page (ringColorClass,
// overallHeadline): a score below 70 is "needs improvement" or worse. Only
// that tier represents a genuinely meaningful gap worth calling out — a
// score of, say, 83 is already in the "good" tier and shouldn't be flagged
// as the site's biggest problem, even if it's the lowest of the four.
const MEANINGFUL_OPPORTUNITY_THRESHOLD = 70;

const RING_SIZE = 168;
const RING_STROKE = 10;
const RING_RADIUS = (RING_SIZE - RING_STROKE) / 2;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

export default function AnalysisOverview({ result, onCategorySelect }: AnalysisOverviewProps) {
  const animatedOverall = useCountUp(result.overallScore, { durationMs: 1100 });
  const dashOffset = RING_CIRCUMFERENCE * (1 - animatedOverall / 100);

  // Identify the single lowest-scoring category to connect the overall score
  // to a concrete next step, rather than leaving four cards of equal weight
  // for the user to prioritize themselves.
  const weakestCategory = result.categoryScores.reduce((weakest, current) =>
    current.score < weakest.score ? current : weakest,
  );
  const hasClearFocusArea = weakestCategory.score < MEANINGFUL_OPPORTUNITY_THRESHOLD;

  return (
    <section id="analysis-overview" aria-labelledby="analysis-overview-heading" className="scroll-mt-8">
      <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl">
        <div className="flex flex-col items-center gap-8 p-6 sm:flex-row sm:items-center sm:gap-10 sm:p-8">
          {/* Overall score ring */}
          <div className="relative flex shrink-0 items-center justify-center">
            <svg
              width={RING_SIZE}
              height={RING_SIZE}
              viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`}
              className="-rotate-90"
              role="img"
              aria-label={`Overall score: ${result.overallScore} out of 100`}
            >
              <circle
                cx={RING_SIZE / 2}
                cy={RING_SIZE / 2}
                r={RING_RADIUS}
                fill="none"
                stroke="currentColor"
                strokeWidth={RING_STROKE}
                className="text-white/[0.06]"
              />
              <defs>
                <linearGradient id="overallScoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#7C5CFF" />
                  <stop offset="100%" stopColor="#67E8F9" />
                </linearGradient>
              </defs>
              <circle
                cx={RING_SIZE / 2}
                cy={RING_SIZE / 2}
                r={RING_RADIUS}
                fill="none"
                stroke="url(#overallScoreGradient)"
                strokeWidth={RING_STROKE}
                strokeLinecap="round"
                strokeDasharray={RING_CIRCUMFERENCE}
                strokeDashoffset={dashOffset}
                className="transition-[stroke-dashoffset] duration-1000 ease-out motion-reduce:transition-none"
              />
            </svg>

            <div className="absolute flex flex-col items-center">
              <span className={`text-4xl font-semibold tabular-nums tracking-tight ${ringColorClass(result.overallScore)}`}>
                {animatedOverall}
              </span>
              <span className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                Overall
              </span>
            </div>
          </div>

          {/* Headline */}
          <div className="flex-1 text-center sm:text-left">
            <h2
              id="analysis-overview-heading"
              className="text-balance text-xl font-semibold tracking-tight text-white sm:text-2xl"
            >
              {overallHeadline(result.overallScore)}
            </h2>

            <p className="mt-2 text-sm leading-6 text-slate-400">
              Sample scores to preview the results experience — actual analysis isn&apos;t
              connected yet.
            </p>

            {hasClearFocusArea ? (
              <button
                type="button"
                onClick={
                  onCategorySelect ? () => onCategorySelect(weakestCategory.category) : undefined
                }
                disabled={!onCategorySelect}
                className="group mt-4 inline-flex max-w-full items-center gap-2 whitespace-nowrap rounded-full border border-[#7C5CFF]/25 bg-[#7C5CFF]/[0.08] px-3.5 py-1.5 text-xs font-medium text-[#C4B5FD] transition-all duration-300 hover:border-[#7C5CFF]/45 hover:bg-[#7C5CFF]/[0.14] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] disabled:cursor-default disabled:hover:border-[#7C5CFF]/25 disabled:hover:bg-[#7C5CFF]/[0.08]"
              >
                <Target className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {/* Shorter wording below the sm breakpoint keeps this pill on a
                    single line at narrow phone widths (375–430px) instead of
                    wrapping inside the rounded-full shape. */}
                <span className="sm:hidden">Focus area: {CATEGORY_LABEL[weakestCategory.category]}</span>
                <span className="hidden sm:inline">
                  Biggest opportunity: {CATEGORY_LABEL[weakestCategory.category]}
                </span>
                {onCategorySelect && (
                  <ArrowRight
                    className="h-3 w-3 shrink-0 transition-transform duration-300 group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                )}
              </button>
            ) : (
              <div className="mt-4 inline-flex max-w-full items-center gap-2 whitespace-nowrap rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-3.5 py-1.5 text-xs font-medium text-emerald-300">
                <Target className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {/* Same fix as the opportunity pill above: the full sentence
                    doesn't fit on one line inside a rounded-full pill at
                    375–430px, so a shorter version is used below sm. */}
                <span className="sm:hidden">No major gaps found.</span>
                <span className="hidden sm:inline">
                  No major gaps — every category is performing well.
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Signature divider: the same violet → cyan gradient as the score ring,
            visually tying the overall score to its category breakdown. */}
        <div
          aria-hidden="true"
          className="h-px w-full bg-gradient-to-r from-transparent via-[#7C5CFF]/40 to-[#67E8F9]/40"
        />

        {/* Category scores */}
        <div className="p-6 pt-6 sm:p-8 sm:pt-6">
          <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Category breakdown
          </h3>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {result.categoryScores.map((categoryScore, index) => (
              <ScoreCard
                key={categoryScore.category}
                icon={CATEGORY_ICON[categoryScore.category]}
                label={CATEGORY_LABEL[categoryScore.category]}
                score={categoryScore.score}
                summary={categoryScore.summary}
                animationDelayMs={index * 90}
                onSelect={
                  onCategorySelect ? () => onCategorySelect(categoryScore.category) : undefined
                }
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}