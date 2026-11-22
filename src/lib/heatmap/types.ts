
/**
 * Shared types for the Confusion Heatmap feature.
 *
 * Supports AI-generated segment-level page analysis.
 */

import type { AnalysisCategoryId } from "@/lib/analysis/types";

export type ConfusionSeverity =
  | "low"
  | "medium"
  | "high";

export interface ConfusionSegment {
  id: string;

  /** Reuses the existing analysis taxonomy rather than inventing a new one. */
  category: AnalysisCategoryId;

  /** 0-100. Higher means readers are more likely to find this segment confusing. */
  confusionScore: number;

  /** Severity based on the confusion score. */
  severity?: ConfusionSeverity;

  /** Short label identifying the segment, e.g. a heading or "Paragraph 3". */
  label: string;

  /** The actual page excerpt this segment corresponds to. */
  excerpt: string;

  /** Reasons why this section may confuse readers. */
  reasons?: string[];

  /** Suggested improvement for this section. */
  recommendation?: string;

  /** Optional id of a related Finding that explains this segment in more depth. */
  relatedFindingId?: string;
}

export interface ConfusionHeatmap {
  /** Marks this as demo/local data, mirroring AnalysisResult.isDemo. */
  isDemo: boolean;

  url: string;

  /** ISO 8601. */
  generatedAt: string;

  /** Total number of analyzed website sections. */
  totalSegments?: number;

  segments: ConfusionSegment[];
}

/** Input accepted by the heatmap analysis API. */
export interface AnalyzeHeatmapInput {
  url: string;
}

/** Website sections extracted before AI analysis. */
export interface ExtractedHeatmapSegment {
  id: string;
  type: "heading" | "paragraph";
  label: string;
  text: string;
}
