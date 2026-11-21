
import type {
  GenerateSuggestionsInput,
  Suggestion,
} from "@/lib/suggestions/types";

interface GroqResponse {
  choices?: Array<{
    message?: {
      content?: string | null;
    };
  }>;
}

const GROQ_MODEL =
  process.env.GROQ_MODEL || "openai/gpt-oss-20b";

const GROQ_API_KEY = process.env.GROQ_API_KEY;

const GROQ_ENDPOINT =
  "https://api.groq.com/openai/v1/chat/completions";

const MAX_RETRIES = 2;
const INITIAL_RETRY_DELAY = 1000;

const RETRYABLE_STATUS_CODES = [
  429,
  500,
  502,
  503,
  504,
];

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function extractJson(text: string): unknown {
  const cleaned = text
    .trim()
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();

  try {
    return JSON.parse(cleaned);
  } catch {
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");

    if (start === -1 || end === -1 || end <= start) {
      throw new Error("Groq returned invalid JSON.");
    }

    return JSON.parse(cleaned.slice(start, end + 1));
  }
}

function buildPrompt(input: GenerateSuggestionsInput): string {
  return `
You are an expert website content improvement assistant.

Analyze the following specific website finding and generate
practical suggestions to improve it.

FINDING:
Title: ${input.title}
Category: ${input.category}
Explanation: ${input.explanation}
Recommended fix: ${input.recommendedFix}
Original website excerpt: ${input.sourceExcerpt || "Not provided"}

INSTRUCTIONS:

1. Focus only on the selected finding.
2. Understand the actual problem before suggesting improvements.
3. Generate specific and useful suggestions.
4. Do not use a fixed keyword checklist.
5. Do not invent website facts or unsupported information.
6. Do not give spelling or grammar corrections.
7. Do not rewrite the entire website or entire page.
8. Avoid repeating the same recommendation.
9. Suggestions must be actionable and easy to understand.
10. If the finding needs rewritten content, provide a short
    example that can be used as input to the Rewrite feature.
11. Otherwise provide a practical action item.
12. Return an empty array if no useful additional suggestion exists.

Return only valid JSON in this format:

{
  "suggestions": [
    {
      "actionType": "rewrite-input",
      "label": "Short suggestion title",
      "content": "Specific suggested content or action"
    }
  ]
}

actionType must be either:
- rewrite-input
- action-item

Generate at most 4 suggestions.
`;
}

function validateSuggestions(
  value: unknown,
  findingId: string,
): Suggestion[] {
  if (!value || typeof value !== "object") {
    throw new Error("Invalid Groq suggestion response.");
  }

  const data = value as Record<string, unknown>;

  if (!Array.isArray(data.suggestions)) {
    throw new Error("Groq suggestions are missing.");
  }

  return data.suggestions.slice(0, 4).map((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error("Invalid suggestion item.");
    }

    const suggestion = item as Record<string, unknown>;

    if (
      typeof suggestion.label !== "string" ||
      typeof suggestion.content !== "string" ||
      !["rewrite-input", "action-item"].includes(
        String(suggestion.actionType),
      )
    ) {
      throw new Error("Groq returned an invalid suggestion.");
    }

    return {
      id: `ai-${findingId}-${index + 1}`,
      findingId,
      actionType: suggestion.actionType as
        Suggestion["actionType"],
      label: suggestion.label.trim(),
      content: suggestion.content.trim(),
    };
  });
}

/**
 * Calls Groq with automatic retry handling.
 *
 * Retries temporary rate limits and server errors.
 */
async function fetchGroqWithRetry(
  requestBody: string,
): Promise<Response> {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await fetch(GROQ_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${GROQ_API_KEY}`,
        },
        body: requestBody,
        cache: "no-store",
        signal: AbortSignal.timeout(30000),
      });

      if (response.ok) {
        return response;
      }

      const errorText = await response.text();

      const isRetryable = RETRYABLE_STATUS_CODES.includes(
        response.status,
      );

      if (!isRetryable || attempt === MAX_RETRIES) {
        console.error("Groq API error:", {
          status: response.status,
          error: errorText,
        });

        throw new Error(
          `Groq request failed with status ${response.status}.`,
        );
      }

      const retryAfter = Number(
        response.headers.get("retry-after"),
      );

      const retryDelay =
        Number.isFinite(retryAfter) && retryAfter > 0
          ? Math.min(retryAfter * 1000, 30000)
          : INITIAL_RETRY_DELAY * Math.pow(2, attempt);

      console.warn(
        `Groq returned ${response.status}. ` +
        `Retrying in ${retryDelay}ms...`,
      );

      await delay(retryDelay);
    } catch (error) {
      if (
        error instanceof Error &&
        error.message.startsWith("Groq request failed")
      ) {
        throw error;
      }

      if (attempt === MAX_RETRIES) {
        console.error("Groq network error:", error);

        throw new Error(
          "Groq service is unavailable after multiple attempts.",
        );
      }

      const retryDelay =
        INITIAL_RETRY_DELAY * Math.pow(2, attempt);

      console.warn(
        `Groq connection failed. Retrying in ${retryDelay}ms...`,
      );

      await delay(retryDelay);
    }
  }

  throw new Error("Groq request failed after multiple attempts.");
}

/**
 * Generates AI suggestions using Groq.
 *
 * The function name is preserved for compatibility
 * with the existing API route.
 */
export async function generateGeminiSuggestions(
  input: GenerateSuggestionsInput,
): Promise<Suggestion[]> {
  if (!GROQ_API_KEY) {
    throw new Error("Groq API key is not configured.");
  }

  const requestBody = JSON.stringify({
    model: GROQ_MODEL,
    messages: [
      {
        role: "user",
        content: buildPrompt(input),
      },
    ],
    temperature: 0.3,
    max_completion_tokens: 1500,
    response_format: {
      type: "json_object",
    },
  });

  const response = await fetchGroqWithRetry(requestBody);

  const data = (await response.json()) as GroqResponse;

  const generatedText =
    data.choices?.[0]?.message?.content;

  if (!generatedText) {
    throw new Error("Groq returned an empty response.");
  }

  return validateSuggestions(
    extractJson(generatedText),
    input.findingId,
  );
}
