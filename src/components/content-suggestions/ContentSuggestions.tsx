
"use client";

import { useState } from "react";
import { Sparkles, AlertCircle, Loader2, Lightbulb } from "lucide-react";

interface ContentSuggestion {
  id: string;
  title: string;
  problem: string;
  location: string;
  whyItMatters: string;
  recommendation: string;
  evidence: string;
  severity: "High" | "Medium" | "Low";
}

interface ContentSuggestionsProps {
  url: string;
}

export default function ContentSuggestions({
  url,
}: ContentSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<ContentSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasAnalyzed, setHasAnalyzed] = useState(false);

  const handleGenerateSuggestions = async () => {
    if (!url.trim()) {
      setError("Please analyze a website first.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuggestions([]);
    setHasAnalyzed(false);

    try {
      // Step 1: Extract website content
      const websiteResponse = await fetch(
        "/verbly-ai/api/website-text",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ url }),
        }
      );

      const websiteData = await websiteResponse.json();

      if (!websiteResponse.ok || websiteData.success !== true) {
        throw new Error(
          websiteData.error || "Unable to extract website content."
        );
      }

      if (
        typeof websiteData.text !== "string" ||
        !websiteData.text.trim()
      ) {
        throw new Error("No readable website content was found.");
      }

      // Step 2: Send extracted content to Gemini API
      const suggestionResponse = await fetch(
        "/verbly-ai/api/content-suggestions",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            url,
            text: websiteData.text,
          }),
        }
      );

      const suggestionData = await suggestionResponse.json();

      if (
        !suggestionResponse.ok ||
        suggestionData.success !== true
      ) {
        throw new Error(
          suggestionData.error || "Failed to generate suggestions."
        );
      }

      setSuggestions(suggestionData.suggestions || []);
      setHasAnalyzed(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  };

  const severityStyle = {
    High: "border-red-500/30 bg-red-500/10 text-red-300",
    Medium: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
    Low: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  };

  return (
    <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.025] p-5 sm:p-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-[#A78BFA]" />
            <h2 className="text-xl font-semibold text-white">
              AI Content Suggestions
            </h2>
          </div>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Let AI independently analyze your website content
            and identify meaningful opportunities for improvement.
          </p>
        </div>

        <button
          type="button"
          onClick={handleGenerateSuggestions}
          disabled={loading}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-[#7C5CFF] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#6D4AE8] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate Suggestions
            </>
          )}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="mt-5 flex gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300"
        >
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <p className="mt-5 text-sm text-slate-400">
          Gemini is examining the website content. This may take a moment...
        </p>
      )}

      {hasAnalyzed && !loading && (
        <div className="mt-6 space-y-5">
          <div className="text-sm text-slate-300">
            {suggestions.length} meaningful improvement
            {suggestions.length === 1 ? "" : "s"} identified.
          </div>

          {suggestions.length === 0 ? (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 text-sm text-emerald-300">
              No significant content improvement issues were identified.
            </div>
          ) : (
            suggestions.map((item) => (
              <article
                key={item.id}
                className="rounded-xl border border-white/10 bg-[#08090D]/70 p-5"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="font-semibold text-white">
                    {item.title}
                  </h3>

                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${severityStyle[item.severity]}`}
                  >
                    {item.severity} Priority
                  </span>
                </div>

                <div className="mt-4 space-y-4 text-sm">
                  <div>
                    <p className="font-medium text-slate-300">
                      Problem identified
                    </p>
                    <p className="mt-1 leading-6 text-slate-400">
                      {item.problem}
                    </p>
                  </div>

                  <div>
                    <p className="font-medium text-slate-300">
                      Location
                    </p>
                    <p className="mt-1 text-slate-400">
                      {item.location}
                    </p>
                  </div>

                  <div>
                    <p className="font-medium text-slate-300">
                      Why it matters
                    </p>
                    <p className="mt-1 leading-6 text-slate-400">
                      {item.whyItMatters}
                    </p>
                  </div>

                  {item.evidence && (
                    <div>
                      <p className="font-medium text-slate-300">
                        Website evidence
                      </p>
                      <blockquote className="mt-2 rounded-lg border-l-2 border-[#7C5CFF] bg-white/[0.035] p-3 leading-6 text-slate-400">
                        {item.evidence}
                      </blockquote>
                    </div>
                  )}

                  <div className="rounded-lg border border-[#7C5CFF]/20 bg-[#7C5CFF]/[0.06] p-4">
                    <div className="flex items-center gap-2 font-medium text-[#C4B5FD]">
                      <Lightbulb className="h-4 w-4" />
                      Recommended improvement
                    </div>

                    <p className="mt-2 leading-6 text-slate-300">
                      {item.recommendation}
                    </p>
                  </div>
                </div>
              </article>
            ))
          )}
        </div>
      )}
    </section>
  );
}
