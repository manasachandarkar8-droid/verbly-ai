import { apiRequest } from "./apiClient";

export interface SeoTagAnalysis {
  value: string | null;
  present: boolean;
  length?: number;
  length_status?: string;
  duplicate_tags_found?: boolean;
  issues: string[];
}

export interface SeoHeadingAnalysis {
  total: number;
  counts_by_level: Record<string, number>;
  h1_count: number;
  has_multiple_h1: boolean;
  hierarchy_gaps_found: boolean;
  headings: unknown[];
  issues: string[];
}

export interface SeoKeyword {
  keyword: string;
  count: number;
  density: number;
}

export interface SeoResponse {
  requested_url: string;
  final_url: string;

  title: SeoTagAnalysis;
  meta_description: SeoTagAnalysis;

  headings: SeoHeadingAnalysis;

  keywords: SeoKeyword[];

  keyword_relationships: {
    keyword: string;
    in_title: boolean;
    in_meta_description: boolean;
    in_content: boolean;
  }[];

  url_analysis: {
    url: string;
    is_https: boolean;
    length: number;
    length_status: string;
    has_query_parameters: boolean;
    query_parameter_count: number;
    tracking_parameters_found: string[];
    has_fragment: boolean;
    path_segment_count: number;
    issues: string[];
  };

  images: {
    total: number;
    with_alt_text: number;
    without_alt_text: number;
    empty_alt_count: number;
    alt_text_coverage_percent: number;
    issues: string[];
  };

  links: {
    total: number;
    internal: number;
    external: number;
    without_usable_href: number;
    issues: string[];
  };

  canonical: {
    value: string | null;
    present: boolean;
    duplicate_tags_found: boolean;
    matches_page_url: boolean | null;
    issues: string[];
  };

  robots: {
    directives: string[];
    present: boolean;
    indexing_allowed: boolean | null;
    following_allowed: boolean | null;
    issues: string[];
  };

  open_graph: {
    title: string | null;
    description: string | null;
    type: string | null;
    url: string | null;
    image: string | null;
    present_tags: string[];
    missing_tags: string[];
    duplicate_tags_found: string[];
    issues: string[];
  };

  issues: string[];
}

export async function analyzeSeo(
  url: string,
  maxKeywords = 20,
): Promise<SeoResponse> {
  if (!url.trim()) {
    throw new Error("Please enter a website URL for SEO analysis.");
  }

  return apiRequest<SeoResponse>(
    "/seo",
    {
      url: url.trim(),
      max_keywords: maxKeywords,
    },
    60_000,
  );
}