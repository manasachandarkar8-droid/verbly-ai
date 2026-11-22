"use client";

import { forwardRef } from "react";
import { ChevronDown, Sparkles } from "lucide-react";

interface SuggestionButtonProps {
  isExpanded: boolean;
  onClick: () => void;
  /** id applied to this button, referenced by the panel's aria-labelledby. */
  triggerId: string;
  /** id of the panel this button controls, per aria-expanded/aria-controls. */
  panelId: string;
}

/**
 * Trigger that expands/collapses the inline Suggestions panel for a single
 * finding. Unlike RewriteButton, this is rendered for every finding
 * regardless of `sourceExcerpt` — suggestions are meaningful even for
 * findings with no rewritable source text (e.g. structural findings). See
 * Phase 8 audit for the rationale.
 *
 * Forwards its ref so the opening component (AnalysisFindings) can return
 * focus to this exact button, matching the pattern already used for
 * RewriteButton in Phase 7.
 */
const SuggestionButton = forwardRef<HTMLButtonElement, SuggestionButtonProps>(
  function SuggestionButton({ isExpanded, onClick, triggerId, panelId }, ref) {
    return (
      <button
        ref={ref}
        id={triggerId}
        type="button"
        aria-expanded={isExpanded}
        aria-controls={panelId}
        onClick={onClick}
        className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-slate-300 transition-all duration-300 hover:border-white/20 hover:bg-white/[0.06] hover:text-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]"
      >
        <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        Suggestions
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 transition-transform duration-300 motion-reduce:transition-none ${
            isExpanded ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        />
      </button>
    );
  },
);

export default SuggestionButton;