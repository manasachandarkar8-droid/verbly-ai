"use client";

import { Grid3x3 } from "lucide-react";
import type { AnalysisResult } from "@/lib/analysis/types";

interface ConfusionHeatmapProps {
  result: AnalysisResult;
}

// What a future segment-level heatmap would surface, shown here only as a
// description of the capability — not as fake data. No scores, excerpts, or
// segment counts are implied.
const PLANNED_CAPABILITIES = [
  "Segment-level scoring",
  "Confusion intensity",
  "Linked findings",
];

/**
 * Confusion Heatmap section.
 *
 * There is no backend capable of segment-level page analysis yet (see
 * src/lib/heatmap/types.ts), so this section only ever renders an honest
 * "not connected" state. It intentionally does not fetch, generate, or
 * fabricate any heatmap data — when a real backend exists, this component
 * gets a `heatmap?: ConfusionHeatmap` prop and a success state, not a
 * rewrite.
 */
export default function ConfusionHeatmap({ result }: ConfusionHeatmapProps) {
  return (
    <section
      id="confusion-heatmap"
      aria-labelledby="confusion-heatmap-heading"
      className="mt-8 scroll-mt-8"
    >
      <h2
        id="confusion-heatmap-heading"
        className="text-lg font-semibold tracking-tight text-white"
      >
        Confusion heatmap
      </h2>
      <p className="mt-1 text-xs text-slate-400">
        Where readers are most likely to get confused, once page segments can be analyzed.
      </p>

      <div className="mt-4 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl">
        <div className="flex flex-col items-center gap-4 px-6 py-14 text-center sm:px-10">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
            <Grid3x3 className="h-5 w-5 text-[#A78BFA]" aria-hidden="true" />
          </div>

          <div className="max-w-md">
            <h3 className="text-sm font-semibold text-white">
              Confusion heatmap isn&apos;t connected yet
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              This view will highlight the specific sections of{" "}
              <span className="break-all font-medium text-slate-300">{result.url}</span> that
              readers are most likely to find confusing. It requires segment-level page
              analysis that isn&apos;t part of this demo.
            </p>
          </div>

          <ul className="mt-2 flex flex-wrap items-center justify-center gap-2">
            <li className="sr-only">Planned capabilities:</li>
            {PLANNED_CAPABILITIES.map((capability) => (
              <li
                key={capability}
                className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-medium text-slate-400"
              >
                {capability}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}