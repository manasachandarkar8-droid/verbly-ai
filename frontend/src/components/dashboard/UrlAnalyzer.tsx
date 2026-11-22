"use client";

import { useId, useState, type FormEvent } from "react";
import { ArrowRight, Globe2, Loader2 } from "lucide-react";

interface UrlAnalyzerProps {
  onAnalyze: (url: string) => void;
  isLoading?: boolean;
}

/**
 * Normalizes user input into a fully-qualified URL string.
 * "example.com" -> "https://example.com"
 * Leaves already-qualified http(s) URLs untouched.
 */
function normalizeUrl(rawInput: string): string {
  const trimmed = rawInput.trim();

  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  return `https://${trimmed}`;
}

/**
 * Validates a normalized URL string on the client only.
 * Server-side URL/security validation belongs to a later backend phase.
 */
function validateUrl(normalized: string): string | null {
  if (!normalized || normalized === "https://") {
    return "Enter a website URL to analyze.";
  }

  let parsed: URL;

  try {
    parsed = new URL(normalized);
  } catch {
    return "That doesn't look like a valid URL.";
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return "Only http:// and https:// links are supported.";
  }

  if (!parsed.hostname || !parsed.hostname.includes(".")) {
    return "Enter a complete website address, like example.com.";
  }

  return null;
}

export default function UrlAnalyzer({ onAnalyze, isLoading = false }: UrlAnalyzerProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputId = useId();
  const errorId = useId();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isLoading) return;

    const normalized = normalizeUrl(value);
    const validationError = validateUrl(normalized);

    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    onAnalyze(normalized);
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="w-full">
      <label htmlFor={inputId} className="sr-only">
        Website URL to analyze
      </label>

      <div
        className={`group relative flex flex-col gap-3 rounded-2xl border bg-[#0D0F15]/90 p-2.5 shadow-[0_25px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl transition-all duration-300 sm:flex-row sm:items-center sm:gap-2 ${
          error
            ? "border-red-400/40 shadow-[0_0_0_1px_rgba(248,113,113,0.15)]"
            : "border-white/10 focus-within:border-[#7C5CFF]/50 focus-within:shadow-[0_0_0_4px_rgba(124,92,255,0.12)]"
        }`}
      >
        <div className="flex flex-1 items-center gap-3 rounded-xl px-3 py-2.5 sm:px-4">
          <Globe2
            className={`h-5 w-5 shrink-0 transition-colors duration-300 ${
              error ? "text-red-400" : "text-slate-500 group-focus-within:text-[#A78BFA]"
            }`}
            aria-hidden="true"
          />

          <input
            id={inputId}
            type="text"
            inputMode="url"
            autoComplete="url"
            placeholder="https://yourwebsite.com"
            value={value}
            disabled={isLoading}
            onChange={(event) => {
              setValue(event.target.value);
              if (error) setError(null);
            }}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? errorId : undefined}
            className="w-full min-w-0 bg-transparent text-sm text-white placeholder:text-slate-500 outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:text-base"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="group/btn relative inline-flex shrink-0 items-center justify-center gap-2 overflow-hidden rounded-xl bg-[#7C5CFF] px-6 py-3.5 text-sm font-semibold text-white shadow-[0_12px_35px_rgba(124,92,255,0.25)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#896EFF] hover:shadow-[0_18px_50px_rgba(124,92,255,0.38)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-[0_12px_35px_rgba(124,92,255,0.25)]"
        >
          <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover/btn:translate-x-full" />

          {isLoading ? (
            <>
              <Loader2 className="relative h-4 w-4 animate-spin" aria-hidden="true" />
              <span className="relative">Analyzing…</span>
            </>
          ) : (
            <>
              <span className="relative">Analyze website</span>
              <ArrowRight className="relative h-4 w-4 transition-transform duration-300 group-hover/btn:translate-x-1" />
            </>
          )}
        </button>
      </div>

      <div
        role="alert"
        id={errorId}
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out ${
          error ? "mt-2.5 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <p className="overflow-hidden px-1 text-xs text-red-400 sm:text-sm">{error}</p>
      </div>
    </form>
  );
}
