"use client";

import { forwardRef } from "react";
import { Wand2 } from "lucide-react";

interface RewriteButtonProps {
  onClick: () => void;
}

/**
 * Trigger that opens the Rewrite workspace for a single finding. Only
 * rendered by AnalysisFindings when a finding has a `sourceExcerpt` — see
 * Finding.sourceExcerpt in src/lib/analysis/types.ts for why.
 *
 * Forwards its ref so the opening component (AnalysisFindings) can return
 * focus to this exact button when the rewrite modal closes.
 */
const RewriteButton = forwardRef<HTMLButtonElement, RewriteButtonProps>(function RewriteButton(
  { onClick },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      onClick={onClick}
      className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#7C5CFF]/25 bg-[#7C5CFF]/[0.08] px-3 py-1.5 text-xs font-medium text-[#C4B5FD] transition-all duration-300 hover:border-[#7C5CFF]/45 hover:bg-[#7C5CFF]/[0.14] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]"
    >
      <Wand2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      Rewrite with AI
    </button>
  );
});

export default RewriteButton;