"use client";

import { useState } from "react";
import { ArrowRight, Loader2, RotateCcw, Sparkles } from "lucide-react";
import type { Finding } from "@/lib/analysis/types";
import type {
  GenerateSuggestions,
  Suggestion,
  SuggestionStatus,
} from "@/lib/suggestions/types";

interface SuggestionsPanelProps {
  finding: Finding;
  /** id of this panel, referenced by the trigger's aria-controls. */
  panelId: string;
  /** id of the trigger button, used for this panel's aria-labelledby. */
  triggerId: string;
  /**
   * Optional. The typed boundary a future backend/AI integration
   * implements (see src/lib/suggestions/types.ts). Nothing in the app
   * currently supplies this — when it's absent, the panel clearly
   * communicates that AI suggestions aren't connected yet instead of
   * generating or faking anything.
   */
  onGenerateSuggestions?: GenerateSuggestions;
  /**
   * Optional. Called when the user chooses "Use in Rewrite" on a
   * `rewrite-input` suggestion. That action is only rendered when the
   * finding has a `sourceExcerpt` (something to rewrite) and this callback
   * is supplied.
   */
  onUseInRewrite?: (suggestion: Suggestion) => void;
}

/**
 * Inline (non-modal) disclosure of AI suggestions for a single finding.
 * Rendered inside the finding's existing expanded panel in
 * AnalysisFindings, alongside — not instead of — the Rewrite workspace.
 *
 * Differs from Finding.recommendedFix (static, always-present, one
 * sentence) and from Rewrite (transforms existing source text): this is a
 * plural, AI-generated, on-demand set of concrete options, and it supports
 * findings that have no `sourceExcerpt` at all. See Phase 8 audit.
 */
export default function SuggestionsPanel({
  finding,
  panelId,
  triggerId,
  onGenerateSuggestions,
  onUseInRewrite,
}: SuggestionsPanelProps) {
  const [status, setStatus] = useState<SuggestionStatus>("idle");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);

  const isGeneratorConnected = Boolean(onGenerateSuggestions);

  const handleGenerate = async () => {
    if (!onGenerateSuggestions) return;

    setStatus("loading");
    setErrorMessage(undefined);

    try {
      const generated = await onGenerateSuggestions({
        findingId: finding.id,
        category: finding.category,
        title: finding.title,
        explanation: finding.explanation,
        recommendedFix: finding.recommendedFix,
        sourceExcerpt: finding.sourceExcerpt,
      });
      setSuggestions(generated);
      setStatus("success");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Something went wrong generating suggestions.",
      );
      setStatus("error");
    }
  };

  return (
    <div
      id={panelId}
      role="region"
      aria-labelledby={triggerId}
      className="mt-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"
    >
      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        Suggestions
      </span>

      {!isGeneratorConnected ? (
        <p className="mt-2 text-xs leading-5 text-slate-400">
          AI suggestions aren&apos;t connected yet. This panel is ready for a real
          suggestions backend — once connected, generating here will produce actual
          AI-generated suggestions for this finding.
        </p>
      ) : (
        <div className="mt-2 flex flex-col gap-3" aria-live="polite">
          {status === "error" && errorMessage && (
            <p role="alert" className="text-xs font-medium text-red-300">
              {errorMessage}
            </p>
          )}

          <div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={status === "loading"}
              className="inline-flex items-center gap-2 rounded-lg border border-[#7C5CFF]/25 bg-[#7C5CFF]/[0.08] px-3 py-1.5 text-xs font-medium text-[#C4B5FD] transition-all duration-300 hover:border-[#7C5CFF]/45 hover:bg-[#7C5CFF]/[0.14] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {status === "success" || status === "error" ? (
                <>
                  <RotateCcw className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  Regenerate
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  {status === "loading" ? "Generating…" : "Generate suggestions"}
                </>
              )}
            </button>
          </div>

          {status === "loading" && (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Loader2
                className="h-3.5 w-3.5 shrink-0 animate-spin motion-reduce:animate-none"
                aria-hidden="true"
              />
              Generating suggestions…
            </div>
          )}

          {status === "success" && suggestions.length === 0 && (
            <p className="text-xs leading-5 text-slate-400">
              No suggestions were returned for this finding.
            </p>
          )}

          {status === "success" && suggestions.length > 0 && (
            <ul className="flex flex-col gap-2">
              {suggestions.map((suggestion) => {
                const canUseInRewrite =
                  suggestion.actionType === "rewrite-input" &&
                  Boolean(finding.sourceExcerpt) &&
                  Boolean(onUseInRewrite);

                return (
                  <li
                    key={suggestion.id}
                    className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"
                  >
                    <span className="text-xs font-semibold text-slate-300">
                      {suggestion.label}
                    </span>
                    <p className="mt-1 text-sm leading-6 text-slate-400">{suggestion.content}</p>

                    {canUseInRewrite && (
                      <button
                        type="button"
                        onClick={() => onUseInRewrite?.(suggestion)}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-[#7C5CFF]/25 bg-[#7C5CFF]/[0.08] px-2.5 py-1 text-[11px] font-medium text-[#C4B5FD] transition-all duration-300 hover:border-[#7C5CFF]/45 hover:bg-[#7C5CFF]/[0.14] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]"
                      >
                        Use in Rewrite
                        <ArrowRight className="h-3 w-3 shrink-0" aria-hidden="true" />
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}