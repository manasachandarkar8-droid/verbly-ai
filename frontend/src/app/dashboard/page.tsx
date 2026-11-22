
"use client";

import { useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabase";
import { Globe2, RotateCcw, Sparkles } from "lucide-react";

import DashboardHeader from "@/components/dashboard/DashboardHeader";
import UrlAnalyzer from "@/components/dashboard/UrlAnalyzer";
import AnalysisOverview from "@/components/dashboard/results/AnalysisOverview";
import AnalysisFindings from "@/components/dashboard/results/AnalysisFindings";
import ConfusionHeatmap from "@/components/heatmap/ConfusionHeatmap";
import LocationIntelligence from "@/components/location/LocationIntelligence";

import { ANALYSIS_CATEGORIES } from "@/lib/analysis/categories";
import { mapAnalysisFindings } from "@/lib/analysis/findings-mapper";

import type {
  AnalysisCategoryId,
  AnalysisResult,
  GrammarAnalysis,
} from "@/lib/analysis/types";

import {
  extractWebsite,
  type ExtractionResponse,
} from "@/services/backend/extractionService";

import {
  analyzeReadability,
  type ReadabilityResponse,
} from "@/services/backend/readabilityService";

import {
  analyzeSeo,
  type SeoResponse,
} from "@/services/backend/seoService";

import {
  analyzeContent,
  type ContentAnalysisResponse,
} from "@/services/backend/contentAnalysisService";

import type {
  GenerateSuggestions,
  Suggestion,
} from "@/lib/suggestions/types";

type DashboardState = "idle" | "results";

type ResultSectionId =
  | "analysis-overview"
  | "analysis-findings"
  | "confusion-heatmap"
  | "location-intelligence";

type ApiResponse = {
  success?: boolean;
  text?: string;
  error?: string;
  data?: unknown;
  suggestions?: unknown;
};

const EXAMPLE_SITES = [
  "stripe.com",
  "linear.app",
  "airbnb.com",
];

const RESULT_SECTIONS: {
  id: ResultSectionId;
  label: string;
}[] = [
  {
    id: "analysis-overview",
    label: "Overview",
  },
  {
    id: "analysis-findings",
    label: "Findings",
  },
  {
    id: "confusion-heatmap",
    label: "Confusion",
  },
  {
    id: "location-intelligence",
    label: "Location",
  },
];

function formatRelativeTime(iso: string): string {
  const diffSec = Math.round(
    (Date.now() - new Date(iso).getTime()) / 1000,
  );

  if (diffSec < 5) {
    return "just now";
  }

  if (diffSec < 60) {
    return `${diffSec}s ago`;
  }

  const diffMin = Math.round(diffSec / 60);

  if (diffMin < 60) {
    return `${diffMin}m ago`;
  }

  const diffHr = Math.round(diffMin / 60);

  return `${diffHr}h ago`;
}

/*
 * Safely read JSON from an API response.
 * This prevents the:
 * Unexpected token '<'
 * error when the API returns HTML.
 */
async function readJsonResponse(
  response: Response,
  apiName: string,
): Promise<ApiResponse> {
  const raw = await response.text();

  const contentType =
    response.headers.get("content-type") || "";

  if (!contentType.includes("application/json")) {
    console.error(
      `${apiName} returned non-JSON response:`,
      {
        status: response.status,
        url: response.url,
        contentType,
        response: raw.slice(0, 500),
      },
    );

    throw new Error(
      `${apiName} returned HTML instead of JSON. ` +
        `Status: ${response.status}. ` +
        `URL: ${response.url}`,
    );
  }

  try {
    const parsed: unknown = JSON.parse(raw);

    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      throw new Error("Response is not a valid JSON object.");
    }

    return parsed as ApiResponse;
  } catch {
    console.error(
      `${apiName} returned invalid JSON:`,
      raw.slice(0, 500),
    );

    throw new Error(
      `${apiName} returned invalid JSON.`,
    );
  }
}

/*
 * Get real grammar analysis from LanguageTool.
 */
async function getGrammarAnalysis(
  url: string,
): Promise<GrammarAnalysis | null> {
  try {
    /*
     * Get website text.
     */
    const websiteResponse = await fetch(
      "/verbly-ai/api/website-text",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
        }),
      },
    );

    const websiteData =
      await readJsonResponse(
        websiteResponse,
        "Website Text API",
      );

    if (
      !websiteResponse.ok ||
      websiteData.success !== true ||
      typeof websiteData.text !== "string"
    ) {
      throw new Error(
        websiteData.error ||
          `Website text API returned ${websiteResponse.status}`,
      );
    }

    const websiteText =
      websiteData.text.trim().slice(0, 20000);

    if (!websiteText) {
      return null;
    }

    /*
     * Send website text to real Grammar API.
     */
    const grammarResponse = await fetch(
      "/verbly-ai/api/grammar",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: websiteText,
        }),
      },
    );

    const grammarData =
      await readJsonResponse(
        grammarResponse,
        "Grammar API",
      );

    console.log(
      "Grammar API response:",
      grammarData,
    );

    if (
      !grammarResponse.ok ||
      grammarData.success !== true ||
      !grammarData.data
    ) {
      throw new Error(
        grammarData.error ||
          `Grammar API returned ${grammarResponse.status}`,
      );
    }

    return grammarData.data as GrammarAnalysis;
  } catch (error) {
    console.error(
      "Failed to get grammar analysis:",
      error,
    );

    return null;
  }
}

export default function DashboardPage() {
  const [state, setState] =
    useState<DashboardState>("idle");

  const [result, setResult] =
  useState<AnalysisResult | null>(null);
/*
   * URL used by the main Website Analyzer.
   * This same URL is passed to LocationIntelligence.
   */
  const [analyzedUrl, setAnalyzedUrl] =
    useState("");

  const [activeCategory, setActiveCategory] =
    useState<AnalysisCategoryId>(
      ANALYSIS_CATEGORIES[0].id,
    );

  const [activeSection, setActiveSection] =
    useState<ResultSectionId>(
      "analysis-overview",
    );

  const [isAnalyzing, setIsAnalyzing] =
    useState(false);

  const [loginMessage, setLoginMessage] =
    useState<string | null>(null);

  const [grammarError, setGrammarError] =
    useState<string | null>(null);

  const resultsHeadingRef =
    useRef<HTMLHeadingElement>(null);

  const urlAnalyzerContainerRef =
    useRef<HTMLDivElement>(null);

  const previousStateRef =
    useRef<DashboardState>(state);

  /*
   * Focus management
   */
  useEffect(() => {
    const previousState =
      previousStateRef.current;

    if (previousState !== state) {
      if (state === "results") {
        resultsHeadingRef.current?.focus();
      }

      if (state === "idle") {
        const input =
          urlAnalyzerContainerRef.current?.querySelector<HTMLInputElement>(
            "input, textarea",
          );

        input?.focus();
      }
    }

    previousStateRef.current = state;
  }, [state]);

  /*
   * Scroll spy
   */
  useEffect(() => {
    if (state !== "results") {
      return;
    }

    const observer =
      new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setActiveSection(
                entry.target.id as ResultSectionId,
              );
            }
          });
        },
        {
          rootMargin: "-35% 0px -55% 0px",
          threshold: 0,
        },
      );

    RESULT_SECTIONS.forEach(({ id }) => {
      const element =
        document.getElementById(id);

      if (element) {
        observer.observe(element);
      }
    });

    return () => {
      observer.disconnect();
    };
  }, [state]);

  /*
   * Scroll to result section
   */
  const scrollToSection = (
    id: ResultSectionId,
  ) => {
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;

    document
      .getElementById(id)
      ?.scrollIntoView({
        behavior: prefersReducedMotion
          ? "auto"
          : "smooth",
        block: "start",
      });
  };

  /*
 * GENERATE AI SUGGESTIONS FOR EACH FINDING
 */
const handleGenerateSuggestions: GenerateSuggestions =
  async (input) => {
    const response = await fetch(
      "/verbly-ai/api/finding-suggestions",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(input),
      },
    );

    const data = await readJsonResponse(
      response,
      "Finding Suggestions API",
    );

    if (
      !response.ok ||
      data.success !== true ||
      !Array.isArray(data.suggestions)
    ) {
      throw new Error(
        data.error ||
          "Unable to generate AI suggestions.",
      );
    }

    return data.suggestions as Suggestion[];
  };

  /*
   * MAIN ANALYZE FUNCTION
   */
  const handleAnalyze = async (url: string) => {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    setLoginMessage("Please login to analyze a website.");
    return;
  }

  setAnalyzedUrl(url);
  setLoginMessage(null);
  setGrammarError(null);
  setIsAnalyzing(true);


  setResult(null);

  try {
    /*
     * STEP 1: Run independent analyses.
     *
     * Extraction, SEO and Grammar do not depend
     * on one another.
     */

    const [extractionOutcome, seoOutcome, grammarOutcome] =
      await Promise.allSettled([
        extractWebsite(url),
        analyzeSeo(url),
        getGrammarAnalysis(url),
      ]);

    /*
     * STEP 2: Process extraction.
     */

    let extractionResult: ExtractionResponse | null = null;

    if (extractionOutcome.status === "fulfilled") {
      extractionResult = extractionOutcome.value;

      if (!extractionResult.main_text.trim()) {
        extractionResult = null;
      } else {

        console.log("Website extraction successful:", {
          title: extractionResult.title,
          wordCount: extractionResult.word_count,
        });
      }
    } else {
      console.error(
        "Website extraction failed:",
        extractionOutcome.reason,
      );
    }

    /*
     * STEP 3: Process SEO.
     */

    let seoResult: SeoResponse | null = null;

    if (seoOutcome.status === "fulfilled") {
      seoResult = seoOutcome.value;

      console.log("SEO analysis successful:", seoResult);
    } else {
      console.error("SEO analysis failed:", seoOutcome.reason);
    }

    /*
     * STEP 4: Process Grammar.
     *
     * Preserve your friend's existing implementation.
     */

    let grammarResult: GrammarAnalysis | null = null;

    if (grammarOutcome.status === "fulfilled") {
      grammarResult = grammarOutcome.value;

      if (!grammarResult) {
        setGrammarError(
          "Grammar analysis is currently unavailable.",
        );
      }
    } else {
      console.error(
        "Grammar analysis failed:",
        grammarOutcome.reason,
      );

      setGrammarError(
        "Grammar analysis is currently unavailable. Check LanguageTool configuration.",
      );
    }

    /*
     * STEP 5: Readability and Content Analysis.
     *
     * Both require successfully extracted website text.
     */

    let readabilityResult: ReadabilityResponse | null = null;
    let contentResult: ContentAnalysisResponse | null = null;

    if (extractionResult) {
      const [readabilityOutcome, contentOutcome] =
        await Promise.allSettled([
          analyzeReadability(extractionResult.main_text),

          analyzeContent(
            extractionResult.main_text,
            extractionResult.title,
            extractionResult.description,
          ),
        ]);

      if (readabilityOutcome.status === "fulfilled") {
        readabilityResult = readabilityOutcome.value;

        console.log(
          "Readability analysis successful:",
          readabilityResult,
        );
      } else {
        console.error(
          "Readability analysis failed:",
          readabilityOutcome.reason,
        );
      }

      if (contentOutcome.status === "fulfilled") {
        contentResult = contentOutcome.value;

        console.log(
          "Content analysis successful:",
          contentResult,
        );
      } else {
        console.error(
          "Content analysis failed:",
          contentOutcome.reason,
        );
      }
    }

    /*
     * STEP 6: Convert actual API responses into findings.
     */

    const findings = mapAnalysisFindings({
      seo: seoResult,
      readability: readabilityResult,
      contentAnalysis: contentResult,
      grammar: grammarResult,
    }).map((finding) => ({
      ...finding,
      sourceExcerpt:
        finding.sourceExcerpt ??
        (finding.severity !== "positive" && extractionResult?.main_text.trim()
          ? extractionResult.main_text
          : undefined),
    }));

    /*
     * STEP 7: Build the real analysis result.
     *
     * No demo scores or fabricated findings.
     */

    const finalResult: AnalysisResult = {
      isDemo: false,
      url,
      generatedAt: new Date().toISOString(),

      extraction: extractionResult ?? undefined,
      seo: seoResult ?? undefined,
      readability: readabilityResult ?? undefined,
      contentAnalysis: contentResult ?? undefined,
      grammar: grammarResult ?? undefined,

      findings,
    };

    setResult(finalResult);

    setActiveCategory(ANALYSIS_CATEGORIES[0].id);
    setState("results");

    console.log("Verbly AI analysis completed:", {
      extraction: !!extractionResult,
      seo: !!seoResult,
      readability: !!readabilityResult,
      contentAnalysis: !!contentResult,
      grammar: !!grammarResult,
      findings: findings.length,
    });

  } catch (error) {
    console.error("Website analysis failed:", error);

    setLoginMessage(
      error instanceof Error
        ? error.message
        : "An unexpected error occurred during analysis.",
    );
  } finally {
    setIsAnalyzing(false);
  }
};
  /*
   * RESET
   */
  const handleReset = () => {
    setState("idle");

    setResult(null);

    /*
     * Clear the URL passed to
     * LocationIntelligence.
     */
    setAnalyzedUrl("");

    setActiveCategory(
      ANALYSIS_CATEGORIES[0].id,
    );

    setActiveSection(
      "analysis-overview",
    );

    setIsAnalyzing(false);

    setLoginMessage(null);

    setGrammarError(null);
  };

  /*
   * CATEGORY SELECT
   */
  const handleCategorySelect = (
    category: AnalysisCategoryId,
  ) => {
    setActiveCategory(category);

    scrollToSection(
      "analysis-findings",
    );
  };

  /*
   * UI
   */
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#08090D] text-white">

      {/* Atmospheric background */}

      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-[-160px] h-[560px] w-[880px] -translate-x-1/2 rounded-full bg-[#7C5CFF]/[0.08] blur-[140px]"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-[8%] top-[28%] h-72 w-72 rounded-full bg-[#67E8F9]/[0.035] blur-[120px]"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.04] [background-image:linear-gradient(to_right,#fff_1px,transparent_1px),linear-gradient(to_bottom,#fff_1px,transparent_1px)] [background-size:64px_64px] [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]"
      />

      <DashboardHeader />

      {state === "idle" ? (
        <div className="relative mx-auto flex min-h-[calc(100vh-72px)] max-w-4xl flex-col items-center justify-center px-5 py-20 sm:px-6 lg:px-8">

          <div className="w-full text-center motion-safe:animate-[dashFadeUp_700ms_cubic-bezier(0.16,1,0.3,1)_both]">

            <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-4 py-2 text-xs font-medium text-slate-300 shadow-[0_0_30px_rgba(124,92,255,0.08)] backdrop-blur-xl">

              <Sparkles
                className="h-3.5 w-3.5 text-[#A78BFA]"
                aria-hidden="true"
              />

              Your content workspace

            </div>

            <h1 className="mt-6 text-balance text-3xl font-semibold leading-tight tracking-[-0.03em] text-white sm:text-4xl lg:text-5xl">
              Analyze a website.
            </h1>

            <p className="mx-auto mt-4 max-w-xl text-balance text-sm leading-7 text-slate-400 sm:text-base">
              Paste a URL below and Verbly
              will look at its SEO,
              readability, grammar, and
              content quality — with clear
              suggestions on what to improve.
            </p>

          </div>

          <div
            ref={urlAnalyzerContainerRef}
            className="mt-10 w-full max-w-2xl motion-safe:animate-[dashFadeUp_800ms_150ms_cubic-bezier(0.16,1,0.3,1)_both]"
          >

            {loginMessage && (
              <div
                role="alert"
                className="mb-4 rounded-xl border border-[#7C5CFF]/30 bg-[#7C5CFF]/10 px-4 py-3 text-center text-sm font-medium text-[#C4B5FD]"
              >
                {loginMessage}
              </div>
            )}

            <UrlAnalyzer
              onAnalyze={handleAnalyze}
            />

            {isAnalyzing && (
              <p className="mt-4 text-center text-sm text-slate-400">
                Analyzing website and checking
                grammar...
              </p>
            )}

            <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-400">

              <span>Try:</span>

              {EXAMPLE_SITES.map((site) => (
                <button
                  key={site}
                  type="button"
                  disabled={isAnalyzing}
                  onClick={() =>
                    handleAnalyze(
                      `https://${site}`,
                    )
                  }
                  className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 font-medium text-slate-400 transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.06] hover:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {site}
                </button>
              ))}

            </div>

          </div>
        </div>
      ) : (
        result && (
          <div className="relative mx-auto max-w-5xl px-5 py-12 sm:px-6 lg:px-8">

            <div className="motion-safe:animate-[dashFadeUp_600ms_cubic-bezier(0.16,1,0.3,1)_both]">

              {/* Results header */}

              <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">

                <div className="min-w-0">

                  <h1
                    ref={resultsHeadingRef}
                    tabIndex={-1}
                    className="text-2xl font-semibold tracking-tight text-white outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#A78BFA] sm:text-3xl"
                  >
                    Analysis results
                  </h1>

                  <div
                    className="mt-2 flex max-w-full items-center gap-1.5 text-sm text-slate-400"
                    title={result.url}
                  >

                    <Globe2
                      className="h-3.5 w-3.5 shrink-0 text-slate-500"
                      aria-hidden="true"
                    />

                    <span className="break-all font-medium text-slate-300">
                      {result.url}
                    </span>

                  </div>

                  <p className="mt-1.5 text-xs text-slate-400">

                    Generated{" "}
                    {formatRelativeTime(
                      result.generatedAt,
                    )}

                    {result.grammar
                      ? " · Real grammar analysis"
                      : " · Grammar analysis unavailable"}

                  </p>

                  {grammarError && (
                    <div
                      role="alert"
                      className="mt-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300"
                    >
                      {grammarError}
                    </div>
                  )}

                </div>

                <button
                  type="button"
                  onClick={handleReset}
                  className="inline-flex shrink-0 items-center gap-2 self-start rounded-xl border border-white/10 bg-white/[0.035] px-4 py-2.5 text-sm font-medium text-slate-200 backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0 sm:self-auto"
                >

                  <RotateCcw
                    className="h-4 w-4"
                    aria-hidden="true"
                  />

                  Analyze another website

                </button>

              </div>

              {/* Results navigation */}

              <nav
                aria-label="Results sections"
                className="mt-6 flex max-w-full gap-1 overflow-x-auto rounded-full border border-white/10 bg-white/[0.02] p-1"
              >

                {RESULT_SECTIONS.map((section) => (
                  <a
                    key={section.id}
                    href={`#${section.id}`}
                    onClick={(event) => {
                      event.preventDefault();

                      scrollToSection(
                        section.id,
                      );
                    }}
                    aria-current={
                      activeSection === section.id
                        ? "true"
                        : undefined
                    }
                    className={`shrink-0 whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] ${
                      activeSection === section.id
                        ? "bg-white/10 text-white"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
                  >
                    {section.label}
                  </a>
                ))}

              </nav>

              {/* Existing result components */}

              <div className="mt-8">

                <AnalysisOverview
                  result={result}
                  onCategorySelect={handleCategorySelect}
                />

                <AnalysisFindings
                  result={result}
                  activeCategory={activeCategory}
                  onCategoryChange={setActiveCategory}
                  onGenerateSuggestions={handleGenerateSuggestions}
                />

                <ConfusionHeatmap
                  result={result}
                />

                {/*
                 * Location Intelligence receives
                 * the same URL entered in the main
                 * Website Analyzer.
                 */}
                <LocationIntelligence
                  url={analyzedUrl}
                />

              </div>

            </div>
          </div>
        )
      )}

      <style jsx>{`
        @keyframes dashFadeUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }

          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>

    </main>
  );
}
