import { apiRequest } from "./apiClient";

export interface ReadabilityResponse {
  word_count: number;
  sentence_count: number;
  character_count: number;
  average_words_per_sentence: number;
  average_syllables_per_word: number;
  flesch_reading_ease: number;
  flesch_kincaid_grade: number;
  reading_level: string;
}

export async function analyzeReadability(
  text: string,
): Promise<ReadabilityResponse> {
  if (!text.trim()) {
    throw new Error("No website content available for readability analysis.");
  }

  return apiRequest<ReadabilityResponse>(
    "/readability",
    { text: text.trim() },
    30_000,
  );
}