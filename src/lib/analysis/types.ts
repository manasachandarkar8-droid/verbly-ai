/**
 * Shared types for the (currently local/demo) website analysis feature.
 *
 * NOTE: There is no backend yet. `AnalysisResult` values are produced by
 * `buildDemoAnalysisResult` in `./demo-data.ts` and are clearly demo data,
 * not the output of a real crawl or analysis engine.
 */

/** The four categories Verbly evaluates a page against. */
export type AnalysisCategoryId =
  | "seo"
  | "readability"
  | "grammar"
  | "content-quality";

export interface AnalysisCategoryMeta {
  id: AnalysisCategoryId;
  /** Short display label, e.g. "SEO". */
  label: string;
  /** One-line description of what this category measures. */
  description: string;
}

/** How serious a single finding is. Ordered worst-to-least-bad for sorting. */
export type FindingSeverity = "critical" | "warning" | "info" | "positive";

export interface Finding {
  id: string;
  category: AnalysisCategoryId;
  severity: FindingSeverity;
  /** Short, specific title, e.g. "Missing meta description". */
  title: string;
  /** Plain-language explanation of what was found and why it matters. */
  explanation: string;
  /** Concrete, actionable next step to resolve the finding. */
  recommendedFix: string;
  /**
   * Optional excerpt of the actual page content this finding refers to.
   * Only present for findings that point at rewritable text (e.g. a dense
   * paragraph or an awkward sentence) — not for structural findings like a
   * missing meta tag or a broken heading hierarchy, which have no original
   * text to rewrite. The presence of this field is what determines whether
   * the "Rewrite with AI" action is offered for a given finding.
   */
  sourceExcerpt?: string;
}

export interface CategoryScore {
  category: AnalysisCategoryId;
  /** 0-100 */
  score: number;
  /** Short one-line explanation of the score. */
  summary: string;
}

/**
 * Location Intelligence — regional/locale-targeting signals detected on the
 * page (hreflang, structured business data, address/format consistency).
 * This is NOT the end user's physical location and does not involve a map.
 *
 * There is no backend for this yet. `AnalysisResult.location` is optional
 * and demo-data.ts intentionally never sets it — see LocationIntelligence.tsx
 * for the honest "not connected" UI this produces today.
 */
export type LocationSignal =
  | "hreflang"
  | "locale-meta"
  | "structured-data"
  | "nap-consistency"
  | "format-consistency";

export type LocationInsightStatus = "detected" | "missing" | "inconsistent";

export interface LocationInsight {
  id: string;
  signal: LocationSignal;
  status: LocationInsightStatus;
  /** Short, specific title, e.g. "Missing hreflang tags". */
  title: string;
  /** Plain-language explanation of what was found and why it matters. */
  explanation: string;
  /** Concrete, actionable next step to resolve the insight. */
  recommendedFix: string;
  /** Same rules as Finding.sourceExcerpt — only set when rewritable. */
  sourceExcerpt?: string;
}

export interface LocationIntelligence {
  /** False (or absent parent field) until a real crawl can populate this. */
  available: boolean;
  /** Locales detected on the page, if any (e.g. from hreflang/lang attrs). */
  detectedLocales?: string[];
  insights: LocationInsight[];
}

export interface AnalysisResult {
  /** Marks this result as demo/local data. Always true until a backend exists. */
  isDemo: true;
  /** The (normalized) URL the user entered. Not actually crawled. */
  url: string;
  /** When this demo result was generated, ISO 8601. */
  generatedAt: string;
  /** 0-100 aggregate score. */
  overallScore: number;
  categoryScores: CategoryScore[];
  findings: Finding[];
  /** Optional — undefined until a real crawl backend exists. See LocationIntelligence. */
  location?: LocationIntelligence;
}