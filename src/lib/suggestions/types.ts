/**
 * Shared types for the (currently unconnected) AI Suggestions feature.
 *
 * Mirrors the pattern established in src/lib/rewrite/types.ts: a typed
 * boundary a future backend/AI integration implements. Nothing in the app
 * currently supplies a real `GenerateSuggestions` implementation — until it
 * does, the UI clearly communicates that suggestions aren't connected
 * rather than generating or faking anything.
 */

import type { AnalysisCategoryId } from "@/lib/analysis/types";

/**
 * What a suggestion is meant to be used for:
 * - "rewrite-input": concrete text that can be handed to the Rewrite
 *   workspace as a starting custom instruction. Only meaningful for
 *   findings that have a `sourceExcerpt` — see Finding.sourceExcerpt.
 * - "action-item": a concrete manual step, used for findings with no
 *   original text to rewrite (e.g. missing metadata, structural issues).
 */
export type SuggestionActionType = "rewrite-input" | "action-item";

export type SuggestionStatus = "idle" | "loading" | "success" | "error";

export interface Suggestion {
  id: string;
  findingId: string;
  actionType: SuggestionActionType;
  /** Short label describing this option, e.g. "More specific phrasing". */
  label: string;
  /** The actual suggested text or instruction. */
  content: string;
}

export interface GenerateSuggestionsInput {
  findingId: string;
  category: AnalysisCategoryId;
  title: string;
  explanation: string;
  recommendedFix: string;
  /** Present only for findings that have rewritable source text. */
  sourceExcerpt?: string;
}

/**
 * The typed boundary a future backend/AI integration implements. Nothing in
 * the app currently supplies this — when it's absent, the suggestions panel
 * clearly communicates that AI suggestions aren't connected yet instead of
 * generating or faking anything.
 */
export type GenerateSuggestions = (
  input: GenerateSuggestionsInput,
) => Promise<Suggestion[]>;