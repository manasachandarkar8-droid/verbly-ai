"use client";

import { MapPin } from "lucide-react";
import type { AnalysisResult } from "@/lib/analysis/types";

interface LocationIntelligenceProps {
  result: AnalysisResult;
}

/**
 * Location Intelligence — locale/regional-targeting signals (hreflang,
 * structured business data, address/format consistency), NOT the user's
 * physical location and NOT a map.
 *
 * There is no backend for this yet. `result.location` is always undefined
 * today (demo-data.ts intentionally never sets it), so this always renders
 * the honest "not connected" state below. The `isAvailable` branch is kept
 * so the component already matches the future `LocationIntelligence`
 * contract in types.ts, but it renders nothing today — there is no real
 * data to show, and this component must never fabricate any.
 */
export default function LocationIntelligence({ result }: LocationIntelligenceProps) {
  const location = result.location;
  const isAvailable = location?.available === true;

  return (
    <section
      id="location-intelligence"
      aria-labelledby="location-intelligence-heading"
      className="mt-8 scroll-mt-8"
    >
      <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl">
        <div className="p-6 sm:p-8">
          <h2
            id="location-intelligence-heading"
            className="text-xl font-semibold tracking-tight text-white sm:text-2xl"
          >
            Location intelligence
          </h2>

          {isAvailable ? null : (
            <div
              role="status"
              className="mt-5 flex flex-col items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.02] px-6 py-10 text-center sm:flex-row sm:items-start sm:gap-4 sm:text-left"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.04]">
                <MapPin className="h-4 w-4 text-slate-400" aria-hidden="true" />
              </span>

              <div>
                <p className="text-sm font-medium text-slate-200">
                  Location intelligence isn&apos;t connected yet.
                </p>
                <p className="mt-1.5 text-sm leading-6 text-slate-400">
                  This section will surface locale and regional-targeting signals — like
                  hreflang tags, structured business data, and address consistency — once a
                  real crawl is available. No location data is shown here today.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}