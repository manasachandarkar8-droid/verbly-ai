"use client";

import { useEffect, useRef, useState } from "react";
import { Globe2, RotateCcw, Sparkles } from "lucide-react";
import DashboardHeader from "@/components/dashboard/DashboardHeader";
import UrlAnalyzer from "@/components/dashboard/UrlAnalyzer";
import AnalysisOverview from "@/components/dashboard/results/AnalysisOverview";
import AnalysisFindings from "@/components/dashboard/results/AnalysisFindings";
import ConfusionHeatmap from "@/components/heatmap/ConfusionHeatmap";
import LocationIntelligence from "@/components/location/LocationIntelligence";
import { ANALYSIS_CATEGORIES, buildDemoAnalysisResult } from "@/lib/analysis/demo-data";
import type { AnalysisCategoryId, AnalysisResult } from "@/lib/analysis/types";

type DashboardState = "idle" | "results";

type ResultSectionId =
  | "analysis-overview"
  | "analysis-findings"
  | "confusion-heatmap"
  | "location-intelligence";

// A quick way to see a result without typing — useful on a first visit, and
// harmless since these still only ever produce local demo data.
const EXAMPLE_SITES = ["stripe.com", "linear.app", "airbnb.com"];

const RESULT_SECTIONS: { id: ResultSectionId; label: string }[] = [
  { id: "analysis-overview", label: "Overview" },
  { id: "analysis-findings", label: "Findings" },
  { id: "confusion-heatmap", label: "Confusion" },
  { id: "location-intelligence", label: "Location" },
];

/** Short, human relative timestamp for the demo result's generatedAt field. */
function formatRelativeTime(iso: string): string {
  const diffSec = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (diffSec < 5) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  return `${diffHr}h ago`;
}

export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeCategory, setActiveCategory] = useState<AnalysisCategoryId>(
    ANALYSIS_CATEGORIES[0].id,
  );
  const [activeSection, setActiveSection] = useState<ResultSectionId>("analysis-overview");

  // Focus management for the idle <-> results transition. The results
  // heading is a plain, non-interactive element so it's only made
  // programmatically focusable (tabIndex={-1}) rather than becoming a
  // permanent extra stop in the page's tab order. The URL input lives
  // inside UrlAnalyzer, so instead of reaching into that component we
  // locate its input via the wrapping container ref once it's back on
  // screen.
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);
  const urlAnalyzerContainerRef = useRef<HTMLDivElement>(null);
  const previousStateRef = useRef<DashboardState>(state);

  useEffect(() => {
    const previousState = previousStateRef.current;

    if (previousState !== state) {
      if (state === "results") {
        resultsHeadingRef.current?.focus();
      } else if (state === "idle") {
        const input = urlAnalyzerContainerRef.current?.querySelector<HTMLInputElement>(
          "input, textarea",
        );
        input?.focus();
      }
    }

    previousStateRef.current = state;
  }, [state]);

  // Lightweight scroll-spy for the in-page results nav. Observes the overview,
  // findings, heatmap, and location sections and highlights whichever one is
  // currently in view.
  useEffect(() => {
    if (state !== "results") return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id as ResultSectionId);
          }
        });
      },
      { rootMargin: "-35% 0px -55% 0px", threshold: 0 },
    );

    RESULT_SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [state]);

  const scrollToSection = (id: ResultSectionId) => {
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    document.getElementById(id)?.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "start",
    });
  };

  // No backend yet. This builds a local, clearly-labelled demo result —
  // see src/lib/analysis/demo-data.ts. Real crawling/analysis is a later phase.
  const handleAnalyze = (url: string) => {
    setResult(buildDemoAnalysisResult(url));
    setActiveCategory(ANALYSIS_CATEGORIES[0].id);
    setState("results");
  };

  const handleReset = () => {
    setState("idle");
    setResult(null);
  };

  // Jump from an overview score card straight to that category's findings.
  const handleCategorySelect = (category: AnalysisCategoryId) => {
    setActiveCategory(category);
    scrollToSection("analysis-findings");
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#08090D] text-white">
      {/* Atmospheric background, consistent with Stage 2 */}
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
              <Sparkles className="h-3.5 w-3.5 text-[#A78BFA]" aria-hidden="true" />
              Your content workspace
            </div>

            <h1 className="mt-6 text-balance text-3xl font-semibold leading-tight tracking-[-0.03em] text-white sm:text-4xl lg:text-5xl">
              Analyze a website.
            </h1>

            <p className="mx-auto mt-4 max-w-xl text-balance text-sm leading-7 text-slate-400 sm:text-base">
              Paste a URL below and Verbly will look at its SEO, readability,
              grammar, and content quality — with clear suggestions on what to
              improve.
            </p>
          </div>

          <div
            ref={urlAnalyzerContainerRef}
            className="mt-10 w-full max-w-2xl motion-safe:animate-[dashFadeUp_800ms_150ms_cubic-bezier(0.16,1,0.3,1)_both]"
          >
            <UrlAnalyzer onAnalyze={handleAnalyze} />

            <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-400">
              <span>Try:</span>
              {EXAMPLE_SITES.map((site) => (
                <button
                  key={site}
                  type="button"
                  onClick={() => handleAnalyze(`https://${site}`)}
                  className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 font-medium text-slate-400 transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.06] hover:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA]"
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
                    <Globe2 className="h-3.5 w-3.5 shrink-0 text-slate-500" aria-hidden="true" />
                    <span className="break-all font-medium text-slate-300">{result.url}</span>
                  </div>

                  <p className="mt-1.5 text-xs text-slate-400 ">
                    Generated {formatRelativeTime(result.generatedAt)} · Local demo data, not a
                    live crawl.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleReset}
                  className="inline-flex shrink-0 items-center gap-2 self-start rounded-xl border border-white/10 bg-white/[0.035] px-4 py-2.5 text-sm font-medium text-slate-200 backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0 sm:self-auto"
                >
                  <RotateCcw className="h-4 w-4" aria-hidden="true" />
                  Analyze another website
                </button>
              </div>

              {/* Restrained in-page nav communicating overall → categories → findings structure.
                  overflow-x-auto (with each pill kept shrink-0/whitespace-nowrap) lets this row
                  scroll horizontally instead of clipping or breaking layout now that a 4th item
                  ("Location") has been added and narrow viewports (375px) can run out of room. */}
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
                      scrollToSection(section.id);
                    }}
                    aria-current={activeSection === section.id ? "true" : undefined}
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

              <div className="mt-8">
                <AnalysisOverview result={result} onCategorySelect={handleCategorySelect} />
                <AnalysisFindings
                  result={result}
                  activeCategory={activeCategory}
                  onCategoryChange={setActiveCategory}
                />
                <ConfusionHeatmap result={result} />
                <LocationIntelligence result={result} />
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