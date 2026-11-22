import { apiRequest } from "./apiClient";

export interface ContentAnalysisResponse {
  summary: {
    text: string;
  }[];

  topics: {
    phrase: string;
    score: number;
  }[];

  key_concepts: {
    phrase: string;
    score: number;
  }[];

  entities: {
    text: string;
    label: string;
    start: number;
    end: number;
  }[];

  content_intent: {
    label: string;
    confidence: number;
    source: string;
    alternatives: {
      label: string;
      score: number;
    }[];
  };

  content_structure: {
    paragraph_count: number;
    sentence_count: number;
    average_words_per_sentence: number;
    shortest_sentence_words: number;
    longest_sentence_words: number;
    short_sentence_count: number;
    long_sentence_count: number;
    heading_like_count: number;
    list_item_count: number;
  };

  quality_signals: {
    word_count: number;
    unique_word_count: number;
    vocabulary_diversity: number;
    repeated_word_ratio: number;
    average_words_per_sentence: number;
    short_content: boolean;
    repetitive_content: boolean;
    english_likelihood: number;
    warnings: string[];
  };

  semantic_metrics: {
    semantic_coherence: number;
    semantic_redundancy: number;
    concept_diversity: number;
    analyzed_sentences: number;
  };

  analysis_window: {
    received_characters: number;
    original_characters: number;
    analyzed_characters: number;
    analyzed_sentences: number;
    truncated: boolean;
    truncation_reason: string | null;
  };

  warnings: string[];
}

export async function analyzeContent(
  mainText: string,
  title?: string | null,
  description?: string | null,
): Promise<ContentAnalysisResponse> {
  if (!mainText.trim()) {
    throw new Error(
      "No website content available for content analysis.",
    );
  }

  return apiRequest<ContentAnalysisResponse>(
    "/content-analysis",
    {
      main_text: mainText.trim(),
      title: title ?? undefined,
      description: description ?? undefined,
    },
    90_000,
  );
}
