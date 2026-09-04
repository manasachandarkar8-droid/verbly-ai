/**
 * Shared types for the AI Rewrite feature.
 *
 * NOTE: There is no rewrite backend yet. Nothing in this file performs a
 * rewrite — it only defines the contract a future backend/AI integration
 * must satisfy. `RewriteModal` (see src/components/rewrite) accepts an
 * optional `onGenerateRewrite` prop matching the `GenerateRewrite` type
 * below. Until a real implementation is supplied, the UI clearly
 * communicates that AI rewriting isn't connected yet rather than faking a
 * result.
 */

import type { AnalysisCategoryId } from "@/lib/analysis/types";

/** Preset tone/goal options for a rewrite. */
export type RewriteTone = "concise" | "professional" | "friendly" | "seo-optimized";

export interface RewriteToneOption {
  id: RewriteTone;
  label: string;
  description: string;
}

/** What the frontend sends to a (future) backend to request a rewrite. */
export interface RewriteRequest {
  findingId: string;
  category: AnalysisCategoryId;
  /** The original excerpt being rewritten (Finding.sourceExcerpt). */
  originalContent: string;
  tone: RewriteTone;
  /** Optional free-text instruction layered on top of the tone preset. */
  customInstruction?: string;
}

/** What a (future) backend returns for a successful rewrite. */
export interface RewriteResult {
  id: string;
  findingId: string;
  originalContent: string;
  rewrittenContent: string;
  tone: RewriteTone;
  /** ISO 8601 timestamp of when the rewrite was generated. */
  createdAt: string;
}

/** UI status for the rewrite currently in progress (if any) within the modal. */
export type RewriteStatus = "idle" | "loading" | "success" | "error";

export interface RewriteError {
  message: string;
  code?: string;
}

/**
 * The typed boundary a future backend/AI integration must implement.
 *
 * Not supplied anywhere in the app yet — no component currently passes a
 * real implementation of this function. When `RewriteModal` doesn't receive
 * one, it shows an explicit "not connected yet" state instead of generating
 * or fabricating any content.
 */
export type GenerateRewrite = (request: RewriteRequest) => Promise<RewriteResult>;

export const REWRITE_TONE_OPTIONS: RewriteToneOption[] = [
  { id: "concise", label: "Concise", description: "Tighter and more to the point." },
  { id: "professional", label: "Professional", description: "More polished and formal." },
  { id: "friendly", label: "Friendly", description: "Warmer and more conversational." },
  {
    id: "seo-optimized",
    label: "SEO-optimized",
    description: "Written with search intent in mind.",
  },
];