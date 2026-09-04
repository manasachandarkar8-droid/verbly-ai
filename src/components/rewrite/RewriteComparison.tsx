"use client";

import { Loader2 } from "lucide-react";
import type { RewriteStatus } from "@/lib/rewrite/types";

interface RewriteComparisonProps {
  original: string;
  rewritten: string | null;
  status: RewriteStatus;
}

/** Side-by-side (stacked on mobile) original vs. rewritten content. */
export default function RewriteComparison({ original, rewritten, status }: RewriteComparisonProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Original
        </span>
        <p className="mt-2 text-sm leading-6 text-slate-300">{original}</p>
      </div>

      <div
        className="rounded-xl border border-[#7C5CFF]/20 bg-[#7C5CFF]/[0.04] p-4"
        aria-live="polite"
      >
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#A78BFA]">
          Rewritten
        </span>

        {status === "loading" ? (
          <div className="mt-2 flex items-center gap-2 text-sm text-slate-400">
            <Loader2
              className="h-4 w-4 shrink-0 animate-spin motion-reduce:animate-none"
              aria-hidden="true"
            />
            Generating…
          </div>
        ) : rewritten ? (
          <p className="mt-2 text-sm leading-6 text-slate-200">{rewritten}</p>
        ) : (
          <p className="mt-2 text-sm leading-6 text-slate-600">
            The rewritten version will appear here.
          </p>
        )}
      </div>
    </div>
  );
}