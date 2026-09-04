"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Info,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ANALYSIS_CATEGORIES } from "@/lib/analysis/demo-data";
import type { AnalysisCategoryId, AnalysisResult, Finding, FindingSeverity } from "@/lib/analysis/types";
import RewriteButton from "@/components/rewrite/RewriteButton";
import RewriteModal from "@/components/rewrite/RewriteModal";
import SuggestionButton from "@/components/suggestions/SuggestionButton";
import SuggestionsPanel from "@/components/suggestions/SuggestionsPanel";
import type { GenerateSuggestions, Suggestion } from "@/lib/suggestions/types";
import type { RewriteResult } from "@/lib/rewrite/types";

interface AnalysisFindingsProps {
  result: AnalysisResult;
  /** Optional. Controls the active category tab from outside (e.g. a ScoreCard). */
  activeCategory?: AnalysisCategoryId;
  /** Optional. Called when the active category changes, for lifting state up. */
  onCategoryChange?: (category: AnalysisCategoryId) => void;
  /**
   * Optional. The typed boundary a future backend/AI integration implements
   * (see src/lib/suggestions/types.ts). Nothing in the app currently
   * supplies this — when it's absent, each finding's Suggestions panel
   * clearly communicates that AI suggestions aren't connected yet instead
   * of generating or faking anything.
   */
  onGenerateSuggestions?: GenerateSuggestions;
}

const SEVERITY_ORDER: FindingSeverity[] = ["critical", "warning", "info", "positive"];

const SEVERITY_META: Record<
  FindingSeverity,
  { label: string; icon: LucideIcon; badgeClass: string; iconClass: string; dotClass: string }
> = {
  critical: {
    label: "Critical",
    icon: AlertCircle,
    badgeClass: "border-red-400/25 bg-red-400/10 text-red-300",
    iconClass: "text-red-400",
    dotClass: "bg-red-400",
  },
  warning: {
    label: "Warning",
    icon: AlertTriangle,
    badgeClass: "border-amber-400/25 bg-amber-400/10 text-amber-300",
    iconClass: "text-amber-400",
    dotClass: "bg-amber-400",
  },
  info: {
    label: "Info",
    icon: Info,
    badgeClass: "border-[#7C5CFF]/25 bg-[#7C5CFF]/10 text-[#C4B5FD]",
    iconClass: "text-[#A78BFA]",
    dotClass: "bg-[#A78BFA]",
  },
  positive: {
    label: "Looking good",
    icon: CheckCircle2,
    badgeClass: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
    iconClass: "text-emerald-400",
    dotClass: "bg-emerald-400",
  },
};

function sortFindings(findings: Finding[]): Finding[] {
  return [...findings].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );
}

/** Worst (most urgent) severity present in a set of findings, or null if none/only positive. */
function worstSeverity(findings: Finding[]): FindingSeverity | null {
  for (const severity of SEVERITY_ORDER) {
    if (severity === "positive") continue;
    if (findings.some((finding) => finding.severity === severity)) return severity;
  }
  return null;
}

export default function AnalysisFindings({
  result,
  activeCategory,
  onCategoryChange,
  onGenerateSuggestions,
}: AnalysisFindingsProps) {
  const [internalCategory, setInternalCategory] = useState<AnalysisCategoryId>(
    activeCategory ?? ANALYSIS_CATEGORIES[0].id,
  );
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Which finding's Rewrite workspace is currently open, if any. Kept local
  // to this component (rather than lifted to page.tsx) since it's per-finding
  // UI state, the same way `expandedId` above already is.
  const [activeRewriteFinding, setActiveRewriteFinding] = useState<Finding | null>(null);

  // Pre-fill for the Rewrite modal's custom instruction field when it's
  // opened from a Suggestion's "Use in Rewrite" action rather than from the
  // finding's own "Rewrite with AI" button. Undefined in the latter case,
  // which preserves the exact Phase 7 behavior of starting blank.
  const [rewriteInitialInstruction, setRewriteInitialInstruction] =
    useState<string | undefined>(undefined);

  // Which trigger opened the Rewrite modal, so focus can be returned to the
  // correct control (the finding's Rewrite button, or its Suggestions
  // toggle) once the modal closes.
  const [rewriteOpenedFrom, setRewriteOpenedFrom] =
    useState<"rewrite-button" | "suggestion" | null>(null);

  // Successfully generated rewrite results, keyed by finding id, kept for
  // the current client session only (Phase 11). Reset on page reload; never
  // persisted. Lets closing and reopening the Rewrite modal for the same
  // finding restore its existing Before/After result instead of losing it.
  const [rewriteResults, setRewriteResults] = useState<Record<string, RewriteResult>>({});

  // Which finding's Suggestions panel is currently expanded, if any. Mirrors
  // `expandedId` above: a single open panel at a time, local to this
  // component since it's per-finding UI state.
  const [expandedSuggestionsId, setExpandedSuggestionsId] = useState<string | null>(null);

  // Stay in sync when a parent controls the active category (e.g. a ScoreCard click).
  useEffect(() => {
    if (activeCategory) setInternalCategory(activeCategory);
  }, [activeCategory]);

  const currentCategory = activeCategory ?? internalCategory;
  const currentCategoryMeta = ANALYSIS_CATEGORIES.find((category) => category.id === currentCategory);

  const selectCategory = (category: AnalysisCategoryId) => {
    setExpandedId(null);
    if (onCategoryChange) {
      onCategoryChange(category);
    } else {
      setInternalCategory(category);
    }
  };

  const findingsForActiveCategory = sortFindings(
    result.findings.filter((finding) => finding.category === currentCategory),
  );

  // Severity counts scoped to the currently selected category tab, so the
  // summary always describes what's actually showing below it rather than
  // the whole result regardless of which tab is active.
  const severityCounts = SEVERITY_ORDER.reduce(
    (counts, severity) => {
      counts[severity] = findingsForActiveCategory.filter(
        (finding) => finding.severity === severity,
      ).length;
      return counts;
    },
    {} as Record<FindingSeverity, number>,
  );

  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  // Roving-tabindex keyboard support for the tablist: Left/Right/Home/End move
  // focus and selection between categories, per the WAI-ARIA tabs pattern.
  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const lastIndex = ANALYSIS_CATEGORIES.length - 1;
    let nextIndex: number | null = null;

    if (event.key === "ArrowRight") nextIndex = index === lastIndex ? 0 : index + 1;
    else if (event.key === "ArrowLeft") nextIndex = index === 0 ? lastIndex : index - 1;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = lastIndex;

    if (nextIndex === null) return;

    event.preventDefault();
    const nextCategory = ANALYSIS_CATEGORIES[nextIndex];
    selectCategory(nextCategory.id);
    tabRefs.current[nextCategory.id]?.focus();
  };

  // Refs to each finding's "Rewrite with AI" trigger button, keyed by
  // finding id, so focus can be returned to the exact button that opened
  // the rewrite modal once it closes.
  const rewriteButtonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  // Refs to each finding's Suggestions toggle button, keyed by finding id.
  // Used both to return focus after the Suggestions panel's own toggling,
  // and to return focus here when the Rewrite modal was opened via a
  // suggestion's "Use in Rewrite" action rather than the Rewrite button.
  const suggestionButtonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const openRewriteFromButton = (finding: Finding) => {
    setRewriteInitialInstruction(undefined);
    setRewriteOpenedFrom("rewrite-button");
    setActiveRewriteFinding(finding);
  };

  const openRewriteFromSuggestion = (finding: Finding, suggestion: Suggestion) => {
    setRewriteInitialInstruction(suggestion.content);
    setRewriteOpenedFrom("suggestion");
    setActiveRewriteFinding(finding);
  };

  const closeRewrite = () => {
    const findingId = activeRewriteFinding?.id ?? null;
    const openedFrom = rewriteOpenedFrom;
    setActiveRewriteFinding(null);
    setRewriteInitialInstruction(undefined);
    setRewriteOpenedFrom(null);
    if (findingId) {
      if (openedFrom === "suggestion") {
        suggestionButtonRefs.current[findingId]?.focus();
      } else {
        rewriteButtonRefs.current[findingId]?.focus();
      }
    }
  };

  const toggleSuggestions = (findingId: string) => {
    setExpandedSuggestionsId((current) => (current === findingId ? null : findingId));
  };

  const handleRewriteComplete = (result: RewriteResult) => {
    setRewriteResults((current) => ({ ...current, [result.findingId]: result }));
  };

  return (
    <section id="analysis-findings" aria-labelledby="analysis-findings-heading" className="mt-8 scroll-mt-8">
      <h2
        id="analysis-findings-heading"
        className="text-lg font-semibold tracking-tight text-white"
      >
        Findings
      </h2>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <p className="text-xs text-slate-400">
          {findingsForActiveCategory.length > 0
            ? `${currentCategoryMeta?.label ?? "This category"} findings, sorted by severity.`
            : `No findings recorded for ${currentCategoryMeta?.label ?? "this category"}.`}
        </p>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {SEVERITY_ORDER.filter((severity) => severityCounts[severity] > 0).map((severity) => (
            <span
              key={severity}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400"
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${SEVERITY_META[severity].dotClass}`}
                aria-hidden="true"
              />
              {severityCounts[severity]} {SEVERITY_META[severity].label.toLowerCase()}
            </span>
          ))}
        </div>
      </div>

      {/* Category tabs */}
      <div
        role="tablist"
        aria-label="Finding category"
        className="mt-4 flex flex-wrap gap-2 rounded-2xl border border-white/10 bg-white/[0.02] p-1.5"
      >
        {ANALYSIS_CATEGORIES.map((category, index) => {
          const isActive = category.id === currentCategory;
          const categoryFindings = result.findings.filter(
            (finding) => finding.category === category.id,
          );
          const worst = worstSeverity(categoryFindings);

          return (
            <button
              key={category.id}
              ref={(el) => {
                tabRefs.current[category.id] = el;
              }}
              type="button"
              role="tab"
              id={`tab-${category.id}`}
              aria-selected={isActive}
              aria-controls={`findings-panel-${category.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => selectCategory(category.id)}
              onKeyDown={(event) => handleTabKeyDown(event, index)}
              className={`relative whitespace-nowrap rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] ${
                isActive
                  ? "bg-[#7C5CFF] text-white shadow-[0_8px_24px_rgba(124,92,255,0.28)]"
                  : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
              }`}
            >
              <span className="inline-flex items-center gap-1.5">
                {!isActive && worst && (
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${SEVERITY_META[worst].dotClass}`}
                    aria-hidden="true"
                  />
                )}
                {category.label}
              </span>
              <span
                className={`ml-2 rounded-full px-1.5 py-0.5 text-[11px] tabular-nums ${
                  isActive ? "bg-white/20" : "bg-white/[0.06] text-slate-400"
                }`}
              >
                {categoryFindings.length}
                <span className="sr-only"> findings</span>
              </span>
            </button>
          );
        })}
      </div>

      {/* Findings list */}
      <div
        role="tabpanel"
        id={`findings-panel-${currentCategory}`}
        aria-labelledby={`tab-${currentCategory}`}
        tabIndex={0}
        className="mt-4 space-y-3 focus-visible:outline-none"
      >
        {findingsForActiveCategory.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.02] px-6 py-12 text-center">
            <CheckCircle2 className="h-6 w-6 text-emerald-400" aria-hidden="true" />
            <p className="text-sm font-medium text-slate-300">No findings in this category</p>
            <p className="max-w-sm text-sm text-slate-400">
              This demo result doesn&apos;t include any sample findings here — in a real
              analysis, issues and suggestions for this category would appear.
            </p>
          </div>
        ) : (
          findingsForActiveCategory.map((finding, index) => {
            const severity = SEVERITY_META[finding.severity];
            const SeverityIcon = severity.icon;
            const isExpanded = expandedId === finding.id;
            const panelId = `finding-panel-${finding.id}`;
            const suggestionsTriggerId = `suggestions-trigger-${finding.id}`;
            const suggestionsPanelId = `suggestions-panel-${finding.id}`;
            const isSuggestionsExpanded = expandedSuggestionsId === finding.id;

            return (
              <div
                key={finding.id}
                style={{ animationDelay: `${index * 60}ms` }}
                className="group overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl transition-all duration-300 motion-safe:animate-[findingFadeIn_500ms_both] hover:border-white/20 hover:bg-white/[0.05]"
              >
                <button
                  type="button"
                  aria-expanded={isExpanded}
                  aria-controls={panelId}
                  onClick={() => setExpandedId(isExpanded ? null : finding.id)}
                  className="flex w-full items-start justify-between gap-3 p-5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#A78BFA]"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <SeverityIcon
                      className={`mt-0.5 h-4 w-4 shrink-0 ${severity.iconClass}`}
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold tracking-tight text-white">
                        {finding.title}
                      </h3>
                      <span
                        className={`mt-1.5 inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${severity.badgeClass}`}
                      >
                        {severity.label}
                      </span>
                    </div>
                  </div>

                  <ChevronDown
                    className={`mt-0.5 h-4 w-4 shrink-0 text-slate-500 transition-transform duration-300 motion-reduce:transition-none ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                    aria-hidden="true"
                  />
                </button>

                <div
                  id={panelId}
                  className={`grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none ${
                    isExpanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                  }`}
                >
                  <div className="overflow-hidden">
                    <div className="px-5 pb-5 pl-12">
                      <p className="text-sm leading-6 text-slate-400">{finding.explanation}</p>

                      <div className="mt-3 flex gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                        <span className="mt-0.5 shrink-0 text-[11px] font-semibold uppercase tracking-wider text-[#A78BFA]">
                          Fix
                        </span>
                        <p className="text-sm leading-6 text-slate-300">{finding.recommendedFix}</p>
                      </div>

                      {finding.sourceExcerpt && (
                        <div className="flex flex-wrap items-center gap-2">
                          <RewriteButton
                            ref={(el) => {
                              rewriteButtonRefs.current[finding.id] = el;
                            }}
                            onClick={() => openRewriteFromButton(finding)}
                          />
                          {rewriteResults[finding.id] && (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/[0.06] px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                              <CheckCircle2 className="h-3 w-3 shrink-0" aria-hidden="true" />
                              Rewritten
                            </span>
                          )}
                        </div>
                      )}

                      <SuggestionButton
                        ref={(el) => {
                          suggestionButtonRefs.current[finding.id] = el;
                        }}
                        isExpanded={isSuggestionsExpanded}
                        triggerId={suggestionsTriggerId}
                        panelId={suggestionsPanelId}
                        onClick={() => toggleSuggestions(finding.id)}
                      />

                      {isSuggestionsExpanded && (
                        <SuggestionsPanel
                          finding={finding}
                          panelId={suggestionsPanelId}
                          triggerId={suggestionsTriggerId}
                          onGenerateSuggestions={onGenerateSuggestions}
                          onUseInRewrite={(suggestion) =>
                            openRewriteFromSuggestion(finding, suggestion)
                          }
                        />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {activeRewriteFinding && (
        <RewriteModal
          finding={activeRewriteFinding}
          onClose={closeRewrite}
          initialCustomInstruction={rewriteInitialInstruction}
          initialResult={rewriteResults[activeRewriteFinding.id]}
          onRewriteComplete={handleRewriteComplete}
        />
      )}

      <style jsx>{`
        @keyframes findingFadeIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </section>
  );
}