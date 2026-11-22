import type {
  AnalysisCategoryId,
  Finding,
  FindingSeverity,
  GrammarAnalysis,
} from "./types";

import type { SeoResponse } from "@/services/backend/seoService";
import type { ReadabilityResponse } from "@/services/backend/readabilityService";
import type { ContentAnalysisResponse } from "@/services/backend/contentAnalysisService";

function createFinding(
  id: string,
  category: AnalysisCategoryId,
  severity: FindingSeverity,
  title: string,
  explanation: string,
  recommendedFix: string,
): Finding {
  return {
    id,
    category,
    severity,
    title,
    explanation,
    recommendedFix,
  };
}

function mapSeoFindings(seo: SeoResponse): Finding[] {
  const findings: Finding[] = [];
  const seenIssues = new Set<string>();

  const addIssues = (issues: string[], prefix: string) => {
    issues.forEach((issue, index) => {
      const normalizedIssue = issue.trim().toLowerCase();

      // Skip empty or duplicate issues.
      if (!normalizedIssue || seenIssues.has(normalizedIssue)) {
        return;
      }

      seenIssues.add(normalizedIssue);

      findings.push(
        createFinding(
          `${prefix}-${index}`,
          "seo",
          "warning",
          issue,
          issue,
          "Review this SEO issue and update the relevant page element.",
        ),
      );
    });
  };

  addIssues(seo.issues, "seo-general");
  addIssues(seo.title.issues, "seo-title");
  addIssues(seo.meta_description.issues, "seo-meta");
  addIssues(seo.headings.issues, "seo-heading");
  addIssues(seo.url_analysis.issues, "seo-url");
  addIssues(seo.images.issues, "seo-images");
  addIssues(seo.links.issues, "seo-links");
  addIssues(seo.canonical.issues, "seo-canonical");
  addIssues(seo.robots.issues, "seo-robots");
  addIssues(seo.open_graph.issues, "seo-open-graph");

  return findings;
}

function mapReadabilityFindings(
  readability: ReadabilityResponse,
): Finding[] {
  const findings: Finding[] = [];

  if (readability.flesch_reading_ease < 50) {
    findings.push(
      createFinding(
        "readability-low-ease",
        "readability",
        "warning",
        "Difficult reading level",
        `The Flesch Reading Ease score is ${readability.flesch_reading_ease}.`,
        "Use shorter sentences and simpler vocabulary where appropriate.",
      ),
    );
  }

  if (readability.average_words_per_sentence > 20) {
    findings.push(
      createFinding(
        "readability-long-sentences",
        "readability",
        "warning",
        "Long average sentence length",
        `The average sentence contains ${readability.average_words_per_sentence} words.`,
        "Break long sentences into shorter, clearer statements.",
      ),
    );
  }

  if (findings.length === 0) {
    findings.push(
      createFinding(
        "readability-positive",
        "readability",
        "positive",
        "Readability metrics look good",
        `Reading level: ${readability.reading_level}. Flesch Reading Ease: ${readability.flesch_reading_ease}.`,
        "Continue using clear, accessible language.",
      ),
    );
  }

  return findings;
}

function mapContentFindings(
  content: ContentAnalysisResponse,
): Finding[] {
  const findings: Finding[] = [];

  content.quality_signals.warnings.forEach((warning, index) => {
    findings.push(
      createFinding(
        `content-warning-${index}`,
        "content-quality",
        "warning",
        "Content quality warning",
        warning,
        "Review the content and address the identified quality concern.",
      ),
    );
  });

  if (content.quality_signals.short_content) {
    findings.push(
      createFinding(
        "content-short",
        "content-quality",
        "info",
        "Short content detected",
        `The analyzed content contains ${content.quality_signals.word_count} words.`,
        "Consider whether additional useful detail would improve the page.",
      ),
    );
  }

  if (content.quality_signals.repetitive_content) {
    findings.push(
      createFinding(
        "content-repetitive",
        "content-quality",
        "warning",
        "Repetitive content detected",
        `Repeated word ratio: ${content.quality_signals.repeated_word_ratio}.`,
        "Reduce unnecessary repetition and improve wording variety.",
      ),
    );
  }

  content.warnings.forEach((warning, index) => {
    findings.push(
      createFinding(
        `content-analysis-warning-${index}`,
        "content-quality",
        "info",
        "Analysis notice",
        warning,
        "Consider this notice when interpreting the content analysis.",
      ),
    );
  });

  if (findings.length === 0) {
    findings.push(
      createFinding(
        "content-positive",
        "content-quality",
        "positive",
        "Content analysis completed",
        `Detected content intent: ${content.content_intent.label}.`,
        "Continue reviewing the semantic and quality metrics.",
      ),
    );
  }

  return findings;
}

function mapGrammarFindings(
  grammar: GrammarAnalysis,
): Finding[] {
  return grammar.findings.map((finding, index) => {
    const severity: FindingSeverity =
      finding.severity === "error"
        ? "critical"
        : finding.severity === "warning"
          ? "warning"
          : "info";

    return {
      id: `grammar-${finding.rule_id}-${finding.offset}-${index}`,
      category: "grammar",
      severity,
      title: finding.short_message || finding.message,
      explanation: finding.message,
      recommendedFix:
        finding.replacements.length > 0
          ? `Suggested correction: ${finding.replacements.join(", ")}`
          : "Review this sentence and correct the identified grammar issue.",
      sourceExcerpt: finding.context ?? undefined,
    };
  });
}

export function mapAnalysisFindings({
  seo,
  readability,
  contentAnalysis,
  grammar,
}: {
  seo?: SeoResponse | null;
  readability?: ReadabilityResponse | null;
  contentAnalysis?: ContentAnalysisResponse | null;
  grammar?: GrammarAnalysis | null;
}): Finding[] {
  return [
    ...(seo ? mapSeoFindings(seo) : []),
    ...(readability ? mapReadabilityFindings(readability) : []),
    ...(contentAnalysis ? mapContentFindings(contentAnalysis) : []),
    ...(grammar ? mapGrammarFindings(grammar) : []),
  ];
}