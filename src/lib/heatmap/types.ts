/**
 * Shared types for the (not yet implemented) Confusion Heatmap feature.
 *
 * There is no backend for this yet — no segment-level page analysis exists.
 * These types define the contract a future backend would need to fulfill.
 * Nothing in the app currently produces a `ConfusionHeatmap` value; until it
 * does, `ConfusionHeatmap.tsx` only ever renders an honest "not connected
 * yet" state, the same way `AnalysisResult` was demo-only before Phase 9.
 */

import type { AnalysisCategoryId } from "@/lib/analysis/types";

export interface ConfusionSegment {
  id: string;
  /** Reuses the existing analysis taxonomy rather than inventing a new one. */
  category: AnalysisCategoryId;
  /** 0-100. Higher means readers are more likely to find this segment confusing. */
  confusionScore: number;
  /** Short label identifying the segment, e.g. a heading or "Paragraph 3". */
  label: string;
  /** The actual page excerpt this segment corresponds to. */
  excerpt: string;
  /** Optional id of a related Finding that explains this segment in more depth. */
  relatedFindingId?: string;
}

export interface ConfusionHeatmap {
  /** Marks this as demo/local data, mirroring AnalysisResult.isDemo. */
  isDemo: true;
  url: string;
  /** ISO 8601. */
  generatedAt: string;
  segments: ConfusionSegment[];
}