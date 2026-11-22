"use client";

import { Check, Copy, RotateCcw, Wand2 } from "lucide-react";
import type { RewriteStatus } from "@/lib/rewrite/types";

interface RewriteActionsProps {
  status: RewriteStatus;
  /** Whether a real `onGenerateRewrite` implementation was supplied to the modal. */
  isGeneratorConnected: boolean;
  errorMessage?: string;
  copied: boolean;
  onGenerate: () => void;
  onCopy: () => void;
}

/**
 * Generate/Regenerate/Copy action bar. When no generator is connected, this
 * renders a plain explanatory state instead of buttons that would do
 * nothing (or worse, appear to do something) — there is deliberately no
 * Accept/Apply action here; see Phase 7 audit for why.
 */
export default function RewriteActions({
  status,
  isGeneratorConnected,
  errorMessage,
  copied,
  onGenerate,
  onCopy,
}: RewriteActionsProps) {
  if (!isGeneratorConnected) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3 text-xs leading-5 text-slate-400">
        AI rewriting isn&apos;t connected yet. This workspace is ready for a real rewrite
        backend — once connected, generating here will produce actual AI-rewritten content.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {status === "error" && errorMessage && (
        <p role="alert" className="text-xs font-medium text-red-300">
          {errorMessage}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onGenerate}
          disabled={status === "loading"}
          className="inline-flex items-center gap-2 rounded-xl bg-[#7C5CFF] px-4 py-2.5 text-sm font-medium text-white transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(124,92,255,0.28)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none"
        >
          {status === "success" ? (
            <>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Regenerate
            </>
          ) : (
            <>
              <Wand2 className="h-4 w-4" aria-hidden="true" />
              {status === "loading"
                ? "Generating…"
                : status === "error"
                  ? "Try again"
                  : "Generate rewrite"}
            </>
          )}
        </button>

        <button
          type="button"
          onClick={onCopy}
          disabled={status !== "success"}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-4 py-2.5 text-sm font-medium text-slate-200 transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#A78BFA] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4 text-emerald-400" aria-hidden="true" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" aria-hidden="true" />
              Copy
            </>
          )}
        </button>
      </div>
    </div>
  );
}