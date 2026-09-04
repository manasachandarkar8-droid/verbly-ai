import type {
  AnalysisCategoryId,
  AnalysisCategoryMeta,
  AnalysisResult,
  Finding,
  FindingSeverity,
} from "./types";

export const ANALYSIS_CATEGORIES: AnalysisCategoryMeta[] = [
  {
    id: "seo",
    label: "SEO",
    description: "Search visibility, metadata, headings, and page structure.",
  },
  {
    id: "readability",
    label: "Readability",
    description: "How clearly and easily the content can be understood.",
  },
  {
    id: "grammar",
    label: "Grammar",
    description: "Grammar, consistency, and writing correctness.",
  },
  {
    id: "content-quality",
    label: "Content quality",
    description: "Clarity, specificity, usefulness, and overall messaging.",
  },
];

/**
 * Deterministic demo data generation.
 *
 * There's still no backend or real crawl — but a demo that always returns the
 * exact same score for every URL reads as an obvious placeholder. Instead,
 * each URL is hashed into a seed that deterministically varies scores,
 * summaries, and which findings appear (including severity), so the same URL
 * always reproduces the same result, while different URLs feel distinct.
 */

/** Simple string hash (djb2) used to seed the PRNG from a URL's hostname. */
function hashString(input: string): number {
  let hash = 5381;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 33) ^ input.charCodeAt(i);
  }
  return hash >>> 0;
}

/** Mulberry32 — small, fast, deterministic PRNG from a numeric seed. */
function mulberry32(seed: number): () => number {
  let state = seed;
  return function next() {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seededHostname(url: string): string {
  try {
    return new URL(url).hostname || url;
  } catch {
    return url;
  }
}

type ScoreTier = "strong" | "good" | "needsWork" | "poor";

function tierForScore(score: number): ScoreTier {
  if (score >= 85) return "strong";
  if (score >= 70) return "good";
  if (score >= 50) return "needsWork";
  return "poor";
}

const CATEGORY_SUMMARIES: Record<AnalysisCategoryId, Record<ScoreTier, string>> = {
  seo: {
    strong: "Strong search structure with metadata and headings well in place.",
    good: "Solid search fundamentals, with a few opportunities to improve metadata.",
    needsWork: "Search structure is inconsistent — metadata and headings need attention.",
    poor: "Search visibility is significantly limited by structural issues.",
  },
  readability: {
    strong: "Clear and easy to follow, with well-scannable sections.",
    good: "Generally clear, though some sections could be easier to scan.",
    needsWork: "Several sections are dense or hard to follow at a glance.",
    poor: "Content is difficult to read and scan throughout.",
  },
  grammar: {
    strong: "Very few writing and consistency issues detected.",
    good: "Mostly clean writing, with a handful of small inconsistencies.",
    needsWork: "Noticeable grammar and consistency issues appear throughout.",
    poor: "Frequent grammar issues undermine the writing's credibility.",
  },
  "content-quality": {
    strong: "The message is clear, specific, and compelling.",
    good: "The message is clear but could be more specific and compelling.",
    needsWork: "Messaging feels vague and would benefit from more specific claims.",
    poor: "Content lacks a clear value proposition or specific substance.",
  },
};

interface FindingTemplate {
  id: string;
  category: AnalysisCategoryId;
  title: string;
  explanation: string;
  recommendedFix: string;
  /** Only include this finding when the category's tier is one of these. */
  tiers: ScoreTier[];
  /** Severity to use when shown — may vary by how bad the tier is. */
  severityByTier: Partial<Record<ScoreTier, FindingSeverity>>;
  /**
   * Optional excerpt of sample page content this finding refers to. Only set
   * on findings that point at actual rewritable text — structural findings
   * (missing metadata, heading hierarchy, broken page structure) and purely
   * positive findings intentionally leave this unset, since there's no
   * original text for those to rewrite.
   */
  sourceExcerpt?: string;
}

const FINDING_TEMPLATES: FindingTemplate[] = [
  {
    id: "seo-meta-description",
    category: "seo",
    title: "Missing meta description",
    explanation:
      "A page without a clear meta description can miss an opportunity to communicate its value in search results.",
    recommendedFix:
      "Add a concise description that clearly explains the page's primary value.",
    tiers: ["good", "needsWork", "poor"],
    severityByTier: { good: "info", needsWork: "warning", poor: "warning" },
    // No sourceExcerpt: there's no existing description text to rewrite —
    // one needs to be written from scratch, which isn't a rewrite action.
  },
  {
    id: "seo-heading-hierarchy",
    category: "seo",
    title: "Heading hierarchy could be improved",
    explanation:
      "The page structure may benefit from a clearer progression between major and supporting sections.",
    recommendedFix:
      "Use headings in a logical hierarchy so each section has a clear relationship to the content around it.",
    tiers: ["strong", "good", "needsWork"],
    severityByTier: { strong: "positive", good: "info", needsWork: "warning" },
    // No sourceExcerpt: structural issue, not rewritable body text.
  },
  {
    id: "seo-broken-structure",
    category: "seo",
    title: "Page structure is hard for search engines to parse",
    explanation:
      "Missing or duplicated structural elements make it harder for search engines to understand what the page is about.",
    recommendedFix:
      "Rebuild the page around a single clear heading hierarchy with one primary heading per page.",
    tiers: ["poor"],
    severityByTier: { poor: "critical" },
    // No sourceExcerpt: structural issue, not rewritable body text.
  },
  {
    id: "readability-long-sentence",
    category: "readability",
    title: "Some sentences are difficult to scan",
    explanation:
      "Long sentences can make important information harder to understand, especially for users who scan content quickly.",
    recommendedFix: "Break longer sentences into shorter, more focused statements.",
    tiers: ["good", "needsWork", "poor"],
    severityByTier: { good: "info", needsWork: "warning", poor: "warning" },
    sourceExcerpt:
      "Our platform helps you manage your entire content workflow from the initial idea through to publication and beyond, giving your team a single place to collaborate, review, and ship content faster without losing track of what needs to happen next at each stage of the process.",
  },
  {
    id: "readability-dense-content",
    category: "readability",
    title: "Some sections feel dense",
    explanation:
      "Dense blocks of text can make otherwise useful information harder to navigate.",
    recommendedFix:
      "Use shorter paragraphs, clearer spacing, and lists where they improve scanning.",
    tiers: ["strong", "good", "needsWork"],
    severityByTier: { strong: "positive", good: "info", needsWork: "warning" },
    sourceExcerpt:
      "Getting started is simple: create an account, connect your existing content sources, configure your preferred publishing destinations, invite your team members, set up approval workflows, and begin drafting — all of which can be done directly from the main dashboard without needing to consult separate documentation.",
  },
  {
    id: "readability-wall-of-text",
    category: "readability",
    title: "Large sections read as a wall of text",
    explanation:
      "Extended passages with no visual breaks are easy for readers to abandon, especially on smaller screens.",
    recommendedFix:
      "Introduce subheadings, shorter paragraphs, and lists to break up long passages.",
    tiers: ["poor"],
    severityByTier: { poor: "critical" },
    sourceExcerpt:
      "We built this product because we were frustrated with how scattered content work had become across teams, tools, and documents, and we wanted something that brought planning, writing, review, and publishing into one place so that nobody had to hunt through five different apps just to figure out where a single piece of content actually stood, and so far the response from early users has been overwhelmingly positive.",
  },
  {
    id: "grammar-consistency",
    category: "grammar",
    title: "Writing style could be more consistent",
    explanation:
      "A consistent writing style helps the content feel more polished and intentional.",
    recommendedFix:
      "Choose a consistent style for punctuation, capitalization, and list formatting.",
    tiers: ["good", "needsWork"],
    severityByTier: { good: "info", needsWork: "warning" },
    sourceExcerpt:
      "We offer Real-time collaboration, in-line Comments, and Version history so your team can work together, however some teams prefer to work Async and thats supported too.",
  },
  {
    id: "grammar-errors-frequent",
    category: "grammar",
    title: "Recurring grammar issues found",
    explanation:
      "Frequent grammar mistakes can make otherwise strong content feel unpolished or untrustworthy.",
    recommendedFix:
      "Run a full editing pass focused on tense, subject-verb agreement, and punctuation.",
    tiers: ["poor"],
    severityByTier: { poor: "critical" },
    sourceExcerpt:
      "Their are several way's our tool can help you're team write better content, and it dont require any technical setup what so ever.",
  },
  {
    id: "grammar-positive",
    category: "grammar",
    title: "Overall writing quality is strong",
    explanation: "This result contains very few grammar-related issues.",
    recommendedFix: "Keep the current level of writing consistency as the content evolves.",
    tiers: ["strong"],
    severityByTier: { strong: "positive" },
    // No sourceExcerpt: positive finding, nothing to rewrite.
  },
  {
    id: "quality-vague-value",
    category: "content-quality",
    title: "Value proposition could be more specific",
    explanation:
      "Broad claims are less persuasive when they do not clearly communicate the outcome users can expect.",
    recommendedFix: "Replace vague claims with specific benefits, outcomes, or evidence.",
    tiers: ["good", "needsWork", "poor"],
    severityByTier: { good: "info", needsWork: "warning", poor: "warning" },
    sourceExcerpt:
      "We help businesses grow by making things better and more efficient, so you can achieve more with less effort and see real results.",
  },
  {
    id: "quality-repetition",
    category: "content-quality",
    title: "Some phrasing could be more varied",
    explanation:
      "Repeated wording across nearby sections can make the content feel less natural.",
    recommendedFix: "Vary repeated phrases while keeping the underlying message consistent.",
    tiers: ["strong", "good", "needsWork"],
    severityByTier: { strong: "positive", good: "info", needsWork: "warning" },
    sourceExcerpt:
      "Our tool makes writing easier. Writing becomes easier with our tool. With our tool, the process of writing is made easier for everyone on your team.",
  },
  {
    id: "quality-no-clear-outcome",
    category: "content-quality",
    title: "No clear outcome for the reader",
    explanation:
      "Without a specific, concrete outcome, readers may struggle to see why the content is relevant to them.",
    recommendedFix:
      "Lead each section with the concrete outcome or benefit the reader should take away.",
    tiers: ["poor"],
    severityByTier: { poor: "critical" },
    sourceExcerpt:
      "Our platform offers a wide range of powerful features designed to support your content needs across every stage of the process.",
  },
];

/** Category baseline anchors — roughly reflects typical relative strengths. */
const CATEGORY_BASELINES: Record<AnalysisCategoryId, number> = {
  seo: 82,
  readability: 78,
  grammar: 86,
  "content-quality": 76,
};

const CATEGORY_WEIGHTS: Record<AnalysisCategoryId, number> = {
  seo: 0.28,
  readability: 0.24,
  grammar: 0.22,
  "content-quality": 0.26,
};

function clampScore(score: number): number {
  return Math.min(98, Math.max(28, Math.round(score)));
}

export function buildDemoAnalysisResult(url: string): AnalysisResult {
  const normalizedUrl = url.trim();
  const seed = hashString(seededHostname(normalizedUrl));
  const random = mulberry32(seed);

  const categoryScores = ANALYSIS_CATEGORIES.map(({ id }) => {
    // Deterministic jitter of roughly ±16 around each category's baseline.
    const jitter = (random() - 0.5) * 32;
    const score = clampScore(CATEGORY_BASELINES[id] + jitter);
    const tier = tierForScore(score);

    return {
      category: id,
      score,
      summary: CATEGORY_SUMMARIES[id][tier],
    };
  });

  const overallScoreRaw = categoryScores.reduce(
    (total, { category, score }) => total + score * CATEGORY_WEIGHTS[category],
    0,
  );
  const overallScore = clampScore(overallScoreRaw);

  const tierByCategory = new Map(
    categoryScores.map(({ category, score }) => [category, tierForScore(score)]),
  );

  const findings: Finding[] = FINDING_TEMPLATES.filter((template) =>
    template.tiers.includes(tierByCategory.get(template.category)!),
  ).map((template) => {
    const tier = tierByCategory.get(template.category)!;
    const severity = template.severityByTier[tier] ?? "info";

    return {
      id: template.id,
      category: template.category,
      severity,
      title: template.title,
      explanation: template.explanation,
      recommendedFix: template.recommendedFix,
      sourceExcerpt: template.sourceExcerpt,
    };
  });

  return {
    isDemo: true,
    url: normalizedUrl,
    generatedAt: new Date().toISOString(),
    overallScore,
    categoryScores,
    findings,
  };
}