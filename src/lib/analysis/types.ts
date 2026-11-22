
/**
 * Shared types for website analysis.
 *
 * SEO, readability and content-quality data may still come from
 * the existing analysis result.
 *
 * Grammar analysis is now connected to the real LanguageTool backend.
 */

/** The four categories Verbly evaluates a page against. */
export type AnalysisCategoryId =
  | "seo"
  | "readability"
  | "grammar"
  | "content-quality";

export interface AnalysisCategoryMeta {
  id: AnalysisCategoryId;
  label: string;
  description: string;
}

/** How serious a single finding is. */
export type FindingSeverity =
  | "critical"
  | "warning"
  | "info"
  | "positive";

export interface Finding {
  id: string;
  category: AnalysisCategoryId;
  severity: FindingSeverity;
  title: string;
  explanation: string;
  recommendedFix: string;
  sourceExcerpt?: string;
}

export interface CategoryScore {
  category: AnalysisCategoryId;
  score: number;
  summary: string;
}

/* ============================================================
   Location Intelligence
   ============================================================ */

export type LocationSignal =
  | "hreflang"
  | "locale-meta"
  | "structured-data"
  | "nap-consistency"
  | "format-consistency";

export type LocationInsightStatus =
  | "detected"
  | "missing"
  | "inconsistent";

export interface LocationInsight {
  id: string;
  signal: LocationSignal;
  status: LocationInsightStatus;
  title: string;
  explanation: string;
  recommendedFix: string;
  sourceExcerpt?: string;
}

export interface LocationIntelligence {
  available: boolean;
  detectedLocales?: string[];
  insights: LocationInsight[];
}

/* ============================================================
   Real Grammar Analysis
   ============================================================ */

export type GrammarSeverity =
  | "error"
  | "warning"
  | "info"
  | null;

export interface GrammarFinding {
  message: string;
  short_message: string | null;
  category: string;
  rule_id: string;
  issue_type: string;
  severity: GrammarSeverity;
  offset: number;
  length: number;
  context: string | null;
  replacements: string[];
}

export interface GrammarAnalysis {
  text_length: number;
  finding_count: number;
  findings: GrammarFinding[];
  issues: GrammarFinding[];
}

/* ============================================================
   Main Analysis Result
   ============================================================ */

export interface AnalysisResult {
  /**
   * True when using demo data.
   * False when using real backend analysis.
   */
  isDemo: boolean;

  url: string;

  generatedAt: string;

  /**
   * Existing dashboard scores.
   * Optional because real API analysis may not provide them.
   */
  overallScore?: number;

  categoryScores?: CategoryScore[];

  findings: Finding[];

  /**
   * Existing Location Intelligence data.
   */
  location?: LocationIntelligence;

  /**
   * Real LanguageTool grammar result.
   */
  grammar?: GrammarAnalysis;

  /**
   * Real website extraction result.
   */
  extraction?: {
  title: string | null;
  description: string | null;
  main_text: string;
  word_count: number;
  character_count: number;
};

  /**
   * Real SEO analysis.
   */
  seo?: unknown;

  /**
   * Real readability analysis.
   */
  readability?: unknown;

  /**
   * Real AI content analysis.
   */
  contentAnalysis?: unknown;
}