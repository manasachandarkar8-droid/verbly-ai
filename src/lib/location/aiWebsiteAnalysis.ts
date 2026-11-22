
/*
 * Dynamic AI Website Analysis
 *
 * IMPORTANT:
 * - No company names are hardcoded.
 * - No website domains are hardcoded.
 * - No fixed website-category keyword list is used.
 * - The AI analyzes the actual website content.
 *
 * This file does NOT find physical addresses.
 * Your existing address.ts remains responsible for that.
 */

export type WebsiteLocationStatus =
  | "single_location"
  | "multiple_locations"
  | "platform_or_multiple_businesses"
  | "online_or_no_physical_location"
  | "insufficient_evidence";

export interface AIWebsiteAnalysis {
  websiteType: string;
  locationStatus: WebsiteLocationStatus;
  reason: string;
  suggestedWebsiteTypes: string[];
  confidence: "High" | "Medium" | "Low";
}

interface WebsitePage {
  url?: string;
  title?: string;
  content?: string;
  text?: string;
  html?: string;
  description?: string;
}

interface GeminiResponse {
  candidates?: Array<{
    content?: {
      parts?: Array<{
        text?: string;
      }>;
    };
  }>;
}

const GEMINI_MODEL =
  process.env.GEMINI_MODEL || "gemini-3.8-flash";

const GEMINI_API_KEY =
  process.env.GEMINI_API_KEY ||
  process.env.GOOGLE_API_KEY;

// Retry configuration
const MAX_RETRIES = 2;
const INITIAL_RETRY_DELAY = 1000;
const REQUEST_TIMEOUT = 30000;

const RETRYABLE_STATUS_CODES = [
  408,
  429,
  500,
  502,
  503,
  504,
];

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/*
 * Remove HTML when raw HTML is supplied.
 */
function stripHtml(value: string): string {
  return value
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/\s+/g, " ")
    .trim();
}

/*
 * Clean one page.
 */
function cleanPage(page: WebsitePage): string {
  const pieces: string[] = [];

  if (page.url) {
    pieces.push(`URL: ${page.url}`);
  }

  if (page.title) {
    pieces.push(`TITLE: ${page.title}`);
  }

  if (page.description) {
    pieces.push(`DESCRIPTION: ${page.description}`);
  }

  if (page.content) {
    pieces.push(`CONTENT: ${page.content}`);
  }

  if (page.text) {
    pieces.push(`TEXT: ${page.text}`);
  }

  if (page.html) {
    pieces.push(`HTML: ${stripHtml(page.html)}`);
  }

  return pieces.join("\n");
}

/*
 * Prepare website content for the AI.
 */
function prepareWebsiteContent(
  pages: WebsitePage[]
): string {
  const MAX_TOTAL_CHARS = 50000;
  const MAX_PAGE_CHARS = 7000;

  const chunks: string[] = [];

  for (const page of pages) {
    const cleaned = cleanPage(page);

    if (!cleaned) {
      continue;
    }

    chunks.push(
      cleaned.slice(0, MAX_PAGE_CHARS)
    );
  }

  return chunks
    .join(
      "\n\n---------------- PAGE ----------------\n\n"
    )
    .slice(0, MAX_TOTAL_CHARS);
}

/*
 * Extract JSON from Gemini response.
 */
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

    if (
      start === -1 ||
      end === -1 ||
      end <= start
    ) {
      throw new Error(
        "AI did not return valid JSON."
      );
    }

    return JSON.parse(
      cleaned.slice(start, end + 1)
    );
  }
}

/*
 * Validate AI output.
 */
function validateAnalysis(
  value: unknown
): AIWebsiteAnalysis {
  if (
    !value ||
    typeof value !== "object"
  ) {
    throw new Error("Invalid AI analysis.");
  }

  const data =
    value as Record<string, unknown>;

  const websiteType =
    typeof data.websiteType === "string"
      ? data.websiteType.trim()
      : "";

  const reason =
    typeof data.reason === "string"
      ? data.reason.trim()
      : "";

  const suggestedWebsiteTypes =
    Array.isArray(data.suggestedWebsiteTypes)
      ? data.suggestedWebsiteTypes
          .filter(
            (item): item is string =>
              typeof item === "string"
          )
          .map((item) => item.trim())
          .filter(Boolean)
          .slice(0, 8)
      : [];

  const validStatuses: WebsiteLocationStatus[] = [
    "single_location",
    "multiple_locations",
    "platform_or_multiple_businesses",
    "online_or_no_physical_location",
    "insufficient_evidence",
  ];

  const locationStatus =
    validStatuses.includes(
      data.locationStatus as WebsiteLocationStatus
    )
      ? (data.locationStatus as WebsiteLocationStatus)
      : "insufficient_evidence";

  const confidence =
    data.confidence === "High" ||
    data.confidence === "Medium" ||
    data.confidence === "Low"
      ? data.confidence
      : "Low";

  if (!websiteType || !reason) {
    throw new Error(
      "AI analysis is incomplete."
    );
  }

  return {
    websiteType,
    locationStatus,
    reason,
    suggestedWebsiteTypes,
    confidence,
  };
}

/*
 * Build the AI instruction.
 *
 * No company names.
 * No predefined website categories.
 */
function buildPrompt(
  websiteContent: string
): string {
  return `
You are analyzing a website for a Location Intelligence system.

Your task is to understand the website from the supplied content.

IMPORTANT RULES:

1. Analyze ONLY the supplied website content.
2. Do not use a predefined company list.
3. Do not identify a website using hardcoded company rules.
4. Do not invent facts.
5. Do not invent a physical address.
6. Do not invent coordinates.
7. Do not claim that a company has multiple branches unless the
   supplied content gives evidence for multiple locations.
8. A platform that represents many businesses or places should be
   distinguished from a single physical establishment.
9. If the evidence is insufficient, say so.
10. Suggested website types must be based on what this website
    actually appears to be.
11. Suggestions should be WEBSITE TYPES, not specific company names.
12. Keep the explanation concise and factual.

Determine:

- What type of website or organization this appears to be.
- The website's physical-location situation.
- Why selecting one physical address may or may not be appropriate.
- Related website TYPES that would be relevant to explore.
- Confidence in your analysis.

Possible location-status meanings:

single_location:
The website clearly represents one identifiable physical location.

multiple_locations:
The website provides evidence of multiple physical locations.

platform_or_multiple_businesses:
The website represents or aggregates many businesses,
places, stores, providers, restaurants, properties, etc.

online_or_no_physical_location:
The website appears primarily online or does not represent
a physical establishment.

insufficient_evidence:
The supplied content is not sufficient to determine this.

Return ONLY valid JSON using exactly this structure:

{
  "websiteType": "string",
  "locationStatus": "single_location | multiple_locations | platform_or_multiple_businesses | online_or_no_physical_location | insufficient_evidence",
  "reason": "string",
  "suggestedWebsiteTypes": [
    "string",
    "string",
    "string"
  ],
  "confidence": "High | Medium | Low"
}

WEBSITE CONTENT:

${websiteContent}
`;
}

/*
 * Gemini request with automatic retry.
 *
 * Handles temporary API errors and network failures.
 */
async function fetchGeminiWithRetry(
  endpoint: string,
  requestBody: string
): Promise<Response> {
  for (
    let attempt = 0;
    attempt <= MAX_RETRIES;
    attempt++
  ) {
    try {
      const response = await fetch(endpoint, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: requestBody,

        cache: "no-store",

        signal: AbortSignal.timeout(
          REQUEST_TIMEOUT
        ),
      });

      if (response.ok) {
        return response;
      }

      const errorText = await response.text();

      const retryable =
        RETRYABLE_STATUS_CODES.includes(
          response.status
        );

      if (
        !retryable ||
        attempt === MAX_RETRIES
      ) {
        console.error("Gemini API error:", {
          status: response.status,
          error: errorText,
        });

        throw new Error(
          `Gemini API failed: ${response.status} ${errorText}`
        );
      }

      const retryDelay =
        INITIAL_RETRY_DELAY *
        Math.pow(2, attempt);

      console.warn(
        `Gemini returned ${response.status}. ` +
        `Retrying in ${retryDelay}ms. ` +
        `Attempt ${attempt + 1}/${MAX_RETRIES}.`
      );

      await delay(retryDelay);

    } catch (error) {
      if (
        error instanceof Error &&
        error.message.startsWith("Gemini API failed:")
      ) {
        throw error;
      }

      if (attempt === MAX_RETRIES) {
        console.error(
          "Gemini network error:",
          error
        );

        throw new Error(
          "Gemini service is unavailable after multiple attempts."
        );
      }

      const retryDelay =
        INITIAL_RETRY_DELAY *
        Math.pow(2, attempt);

      console.warn(
        `Gemini connection failed. ` +
        `Retrying in ${retryDelay}ms. ` +
        `Attempt ${attempt + 1}/${MAX_RETRIES}.`
      );

      await delay(retryDelay);
    }
  }

  throw new Error(
    "Gemini request failed after multiple attempts."
  );
}

/*
 * Main function.
 */
export async function analyzeWebsiteWithAI(
  pages: WebsitePage[]
): Promise<AIWebsiteAnalysis> {

  if (
    !Array.isArray(pages) ||
    pages.length === 0
  ) {
    return {
      websiteType: "Unknown website type",

      locationStatus: "insufficient_evidence",

      reason:
        "There was not enough website content available to determine the type of website or its physical-location situation.",

      suggestedWebsiteTypes: [],

      confidence: "Low",
    };
  }

  if (!GEMINI_API_KEY) {
    console.warn(
      "GEMINI_API_KEY is not configured."
    );

    return {
      websiteType: "Unknown website type",

      locationStatus: "insufficient_evidence",

      reason:
        "AI website analysis is unavailable because the Gemini API key is not configured.",

      suggestedWebsiteTypes: [],

      confidence: "Low",
    };
  }

  const websiteContent =
    prepareWebsiteContent(pages);

  if (!websiteContent) {
    return {
      websiteType: "Unknown website type",

      locationStatus: "insufficient_evidence",

      reason:
        "The analyzed pages did not contain enough readable content to determine the website type.",

      suggestedWebsiteTypes: [],

      confidence: "Low",
    };
  }

  const prompt = buildPrompt(websiteContent);

  const endpoint =
    `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  try {
    const requestBody = JSON.stringify({
      contents: [
        {
          parts: [
            {
              text: prompt,
            },
          ],
        },
      ],

      generationConfig: {
        temperature: 0.1,

        responseMimeType: "application/json",
      },
    });

    const response = await fetchGeminiWithRetry(
      endpoint,
      requestBody
    );

    const data =
      (await response.json()) as GeminiResponse;

    const text =
      data.candidates?.[0]?.content?.parts?.[0]?.text;

    if (!text) {
      throw new Error(
        "Gemini returned an empty response."
      );
    }

    const parsed = extractJson(text);

    return validateAnalysis(parsed);

  } catch (error) {
    console.error(
      "AI website analysis failed:",
      error
    );

    /*
     * Do not break the physical-address system
     * if AI analysis fails.
     */
    return {
      websiteType: "Unknown website type",

      locationStatus: "insufficient_evidence",

      reason:
        "The website content could not be analyzed by the AI service. No conclusion about the website type or physical location was made.",

      suggestedWebsiteTypes: [],

      confidence: "Low",
    };
  }
}
