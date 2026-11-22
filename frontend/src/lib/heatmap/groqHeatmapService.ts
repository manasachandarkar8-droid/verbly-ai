
import type { AnalysisCategoryId } from "@/lib/analysis/types";

import type {
  ConfusionHeatmap,
  ConfusionSegment,
  ExtractedHeatmapSegment,
  ConfusionSeverity,
} from "@/lib/heatmap/types";

interface GroqResponse {
  choices?: Array<{
    message?: {
      content?: string | null;
    };
  }>;
}

interface AIConfusionSegment {
  id: string;
  category: AnalysisCategoryId;
  confusionScore: number;
  reasons: string[];
  recommendation: string;
}

const GROQ_MODEL =
  process.env.GROQ_MODEL || "openai/gpt-oss-20b";

const GROQ_API_KEY = process.env.GROQ_API_KEY;

const GROQ_ENDPOINT =
  "https://api.groq.com/openai/v1/chat/completions";

const BATCH_SIZE = 5;

const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1500;

const RETRYABLE_STATUS_CODES = [
  429,
  500,
  502,
  503,
  504,
];

const ALLOWED_CATEGORIES: AnalysisCategoryId[] = [
  "seo",
  "readability",
  "grammar",
  "content-quality",
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

function buildPrompt(
  segments: ExtractedHeatmapSegment[],
): string {
  return `
You are an expert website usability and content clarity analyst.

Analyze ONLY the following ${segments.length} website sections.

WEBSITE SECTIONS:
${JSON.stringify(segments)}

TASK:

For every supplied section:

1. Preserve its exact original ID.
2. Select the most relevant category:
   seo, readability, grammar, or content-quality.
3. Give a confusionScore from 0 to 100.
4. Higher scores mean greater potential difficulty for readers.
5. Evaluate clarity, sentence complexity, structure, terminology,
   missing context, grammar and information organization.
6. Do not treat length alone as confusion.
7. Do not assume actual visitors experienced confusion.
8. Do not invent information.
9. Provide 1 to 3 short reasons.
10. Provide one practical and concise recommendation.

IMPORTANT:
- Analyze every supplied section.
- Return exactly ${segments.length} results.
- Use only IDs from the supplied input.
- Do not skip any section.
- Do not analyze sections outside this batch.
- Do not provide an introduction or explanation.
- Return structured JSON only.
`;
}

function getSeverity(
  score: number,
): ConfusionSeverity {
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

function validateBatch(
  value: unknown,
  originalSegments: ExtractedHeatmapSegment[],
): ConfusionSegment[] {
  if (!value || typeof value !== "object") {
    throw new Error("Invalid Groq heatmap response.");
  }

  const data = value as Record<string, unknown>;

  if (!Array.isArray(data.segments)) {
    throw new Error("Groq heatmap segments are missing.");
  }

  const results = data.segments as unknown[];

  if (results.length !== originalSegments.length) {
    throw new Error(
      `Groq returned ${results.length} results for ${originalSegments.length} sections.`,
    );
  }

  const resultMap = new Map<string, AIConfusionSegment>();

  for (const item of results) {
    if (!item || typeof item !== "object") {
      throw new Error("Invalid heatmap segment.");
    }

    const segment = item as Record<string, unknown>;

    if (
      typeof segment.id !== "string" ||
      typeof segment.category !== "string" ||
      typeof segment.confusionScore !== "number" ||
      !Array.isArray(segment.reasons) ||
      !segment.reasons.every(
        (reason) => typeof reason === "string",
      ) ||
      typeof segment.recommendation !== "string"
    ) {
      throw new Error("Groq returned an invalid heatmap segment.");
    }

    if (
      !ALLOWED_CATEGORIES.includes(
        segment.category as AnalysisCategoryId,
      )
    ) {
      throw new Error("Groq returned an invalid category.");
    }

    if (
      !Number.isFinite(segment.confusionScore) ||
      segment.confusionScore < 0 ||
      segment.confusionScore > 100
    ) {
      throw new Error("Invalid confusion score.");
    }

    if (
      segment.reasons.length < 1 ||
      segment.reasons.length > 3
    ) {
      throw new Error("Invalid number of confusion reasons.");
    }

    if (resultMap.has(segment.id)) {
      throw new Error("Groq returned duplicate segment IDs.");
    }

    resultMap.set(
      segment.id,
      segment as unknown as AIConfusionSegment,
    );
  }

  return originalSegments.map((original) => {
    const generated = resultMap.get(original.id);

    if (!generated) {
      throw new Error(
        `Groq did not analyze section ${original.id}.`,
      );
    }

    return {
      id: original.id,
      category: generated.category,
      confusionScore: generated.confusionScore,
      severity: getSeverity(generated.confusionScore),
      label: original.label,
      excerpt: original.text,
      reasons: generated.reasons,
      recommendation: generated.recommendation,
    };
  });
}

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
        signal: AbortSignal.timeout(60000),
      });

      if (response.ok) {
        return response;
      }

      const errorText = await response.text();

      const isRetryable =
        RETRYABLE_STATUS_CODES.includes(response.status);

      if (!isRetryable || attempt === MAX_RETRIES) {
        console.error("Groq heatmap API error:", {
          status: response.status,
          error: errorText,
        });

        throw new Error(
          `Groq request failed with status ${response.status}: ${errorText}`,
        );
      }

      const retryAfter = Number(
        response.headers.get("retry-after"),
      );

      const retryDelay =
        Number.isFinite(retryAfter) && retryAfter > 0
          ? Math.min(retryAfter * 1000, 30000)
          : INITIAL_RETRY_DELAY * Math.pow(2, attempt);

      console.log(
        `Groq returned ${response.status}. Retrying in ${retryDelay}ms.`,
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
        console.error("Groq heatmap network error:", error);

        throw new Error(
          "Groq service is unavailable after multiple attempts.",
        );
      }

      await delay(
        INITIAL_RETRY_DELAY * Math.pow(2, attempt),
      );
    }
  }

  throw new Error("Groq heatmap request failed.");
}

async function analyzeBatch(
  segments: ExtractedHeatmapSegment[],
): Promise<ConfusionSegment[]> {
  const requestBody = JSON.stringify({
    model: GROQ_MODEL,

    messages: [
      {
        role: "system",
        content:
          "You are a website usability analyst. Analyze only the supplied website sections and return valid structured JSON.",
      },
      {
        role: "user",
        content: buildPrompt(segments),
      },
    ],

    temperature: 0.2,
    reasoning_effort: "low",
    max_completion_tokens: 5000,

    response_format: {
      type: "json_schema",

      json_schema: {
        name: "confusion_heatmap_batch",
        strict: true,

        schema: {
          type: "object",

          properties: {
            segments: {
              type: "array",

              items: {
                type: "object",

                properties: {
                  id: {
                    type: "string",
                  },

                  category: {
                    type: "string",
                    enum: [
                      "seo",
                      "readability",
                      "grammar",
                      "content-quality",
                    ],
                  },

                  confusionScore: {
                    type: "number",
                  },

                  reasons: {
                    type: "array",
                    items: {
                      type: "string",
                    },
                  },

                  recommendation: {
                    type: "string",
                  },
                },

                required: [
                  "id",
                  "category",
                  "confusionScore",
                  "reasons",
                  "recommendation",
                ],

                additionalProperties: false,
              },
            },
          },

          required: ["segments"],
          additionalProperties: false,
        },
      },
    },
  });

  const response = await fetchGroqWithRetry(requestBody);

  const data = (await response.json()) as GroqResponse;

  const generatedText =
    data.choices?.[0]?.message?.content;

  if (!generatedText) {
    throw new Error("Groq returned an empty heatmap response.");
  }

  const parsed = extractJson(generatedText);

  return validateBatch(parsed, segments);
}

export async function generateGroqHeatmap(
  url: string,
  segments: ExtractedHeatmapSegment[],
): Promise<ConfusionHeatmap> {
  if (!GROQ_API_KEY) {
    throw new Error("Groq API key is not configured.");
  }

  if (segments.length === 0) {
    throw new Error("No website sections were provided.");
  }

  const allAnalyzedSegments: ConfusionSegment[] = [];

  const totalBatches = Math.ceil(
    segments.length / BATCH_SIZE,
  );

  console.log(
    `Starting heatmap analysis: ${segments.length} sections in ${totalBatches} batches.`,
  );

  for (
    let start = 0;
    start < segments.length;
    start += BATCH_SIZE
  ) {
    const batch = segments.slice(
      start,
      start + BATCH_SIZE,
    );

    const batchNumber =
      Math.floor(start / BATCH_SIZE) + 1;

    console.log(
      `Analyzing heatmap batch ${batchNumber}/${totalBatches} (${batch.length} sections).`,
    );

    const analyzedBatch = await analyzeBatch(batch);

    allAnalyzedSegments.push(...analyzedBatch);

    console.log(
      `Completed heatmap batch ${batchNumber}/${totalBatches}.`,
    );
  }

  const analyzedMap = new Map(
    allAnalyzedSegments.map((segment) => [
      segment.id,
      segment,
    ]),
  );

  const orderedSegments = segments.map((original) => {
    const analyzed = analyzedMap.get(original.id);

    if (!analyzed) {
      throw new Error(
        `Final heatmap is missing section ${original.id}.`,
      );
    }

    return analyzed;
  });

  console.log(
    `Heatmap analysis completed: ${orderedSegments.length} sections analyzed.`,
  );

  return {
    isDemo: false,
    url,
    generatedAt: new Date().toISOString(),
    totalSegments: orderedSegments.length,
    segments: orderedSegments,
  };
}
