
export type GrammarIssueCategory =
  | "grammar"
  | "punctuation"
  | "spelling"
  | "word_choice"
  | "sentence_structure";

export type GrammarIssueSeverity = "error" | "warning";

export interface GrammarEngineFinding {
  original: string;
  correction: string;
  explanation: string;
  category: GrammarIssueCategory;
  severity: GrammarIssueSeverity;
  start: number;
  end: number;
}

export interface GrammarEngineResult {
  text_length: number;
  finding_count: number;
  findings: GrammarEngineFinding[];
}

type AIGrammarFinding = {
  original: string;
  correction: string;
  explanation: string;
  category: string;
  severity: string;
};

type AIGrammarResponse = {
  findings: AIGrammarFinding[];
};

const GROQ_API_URL =
  "https://api.groq.com/openai/v1/chat/completions";

const GROQ_MODEL =
  process.env.GROQ_GRAMMAR_MODEL || "openai/gpt-oss-20b";

const MAX_ATTEMPTS = 2;
const REQUEST_TIMEOUT_MS = 45000;

const ALLOWED_CATEGORIES: GrammarIssueCategory[] = [
  "grammar",
  "punctuation",
  "spelling",
  "word_choice",
  "sentence_structure",
];

const SYSTEM_PROMPT = `
You are an expert English grammar editor and linguistic analyzer.

Your task is to detect genuine errors in the supplied text.

Analyze:
- Grammar
- Punctuation
- Spelling
- Word choice
- Sentence structure

IMPORTANT RULES:

1. Analyze the meaning and context of the complete text.
2. Do not rely on fixed keywords or predefined sentence patterns.
3. Do not invent errors in grammatically correct sentences.
4. Do not flag stylistic preferences as grammar errors.
5. Do not rewrite text merely to make it sound professional.
6. Preserve the author's original meaning.
7. Recognize valid variations of English, contractions,
   conversational English, and accepted modern usage.
8. Do not flag valid singular or plural "they".
9. Do not flag intentional headings, labels, slogans,
   navigation text, or short UI content.
10. Ignore URLs, product names, brand names, code,
    and technical identifiers.
11. Only return findings when reasonably certain an actual
    error exists.
12. Copy every original phrase exactly from the input.
13. Corrections must fix the issue without unnecessary rewriting.
14. If the text is correct, return an empty findings array.
15. Never fabricate errors.
16. Do not return duplicate findings.
17. Do not return overlapping findings.
18. Do not include explanations for text that is already correct.

For every finding return:

- original: exact incorrect text
- correction: corrected text
- explanation: concise reason
- category: grammar, punctuation, spelling, word_choice,
  or sentence_structure
- severity: error or warning

Return ONLY valid JSON.

Use exactly this structure:

{
  "findings": [
    {
      "original": "exact incorrect text",
      "correction": "corrected text",
      "explanation": "reason for correction",
      "category": "grammar",
      "severity": "error"
    }
  ]
}

If no errors exist, return:

{
  "findings": []
}

Do not include Markdown code fences or additional text.
`;

class GroqRequestError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "GroqRequestError";
  }
}

function cleanText(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function isValidCategory(
  value: string,
): value is GrammarIssueCategory {
  return ALLOWED_CATEGORIES.includes(
    value as GrammarIssueCategory,
  );
}

function locateOriginal(
  text: string,
  original: string,
  usedOffsets: Set<number>,
): number {
  if (!original) return -1;

  let position = text.indexOf(original);

  while (position !== -1 && usedOffsets.has(position)) {
    position = text.indexOf(original, position + 1);
  }

  return position;
}

function validateFinding(
  item: AIGrammarFinding,
  sourceText: string,
  usedOffsets: Set<number>,
): GrammarEngineFinding | null {
  const original = cleanText(item.original);
  const correction = cleanText(item.correction);
  const explanation = cleanText(item.explanation);
  const category = cleanText(item.category).toLowerCase();
  const severity = cleanText(item.severity).toLowerCase();

  if (!original || !correction || !explanation) {
    return null;
  }

  if (original === correction) {
    return null;
  }

  if (!isValidCategory(category)) {
    return null;
  }

  if (severity !== "error" && severity !== "warning") {
    return null;
  }

  const start = locateOriginal(
    sourceText,
    original,
    usedOffsets,
  );

  if (start === -1) {
    return null;
  }

  const end = start + original.length;

  if (sourceText.slice(start, end) !== original) {
    return null;
  }

  usedOffsets.add(start);

  return {
    original,
    correction,
    explanation,
    category,
    severity,
    start,
    end,
  };
}

async function requestGrammarAI(
  input: string,
  apiKey: string,
): Promise<string> {
  const controller = new AbortController();

  const timeout = setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );

  try {
    const response = await fetch(GROQ_API_URL, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },

      signal: controller.signal,

      body: JSON.stringify({
        model: GROQ_MODEL,

        messages: [
          {
            role: "system",
            content: SYSTEM_PROMPT,
          },
          {
            role: "user",
            content: JSON.stringify({
              instruction:
                "Analyze the following text for genuine English grammar errors. Return only the required JSON object.",
              text: input,
            }),
          },
        ],

        response_format: {
          type: "json_object",
        },

        reasoning_format: "hidden",
        reasoning_effort: "low",

        temperature: 0,
        max_completion_tokens: 8192,
        stream: false,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();

      console.error(
        `Groq returned HTTP ${response.status}:`,
        errorText,
      );

      if (
        response.status === 401 ||
        response.status === 403
      ) {
        throw new GroqRequestError(
          "Groq authentication failed. Check your GROQ_API_KEY.",
          response.status,
        );
      }

      if (response.status === 429) {
        throw new GroqRequestError(
          "Groq rate limit or quota reached.",
          response.status,
        );
      }

      throw new GroqRequestError(
        `Groq request failed (${response.status}): ${errorText}`,
        response.status,
      );
    }

    const apiData = await response.json();

    const choice = apiData?.choices?.[0];

    if (choice?.finish_reason === "length") {
      throw new Error(
        "Groq response was truncated. Try analyzing a smaller amount of text.",
      );
    }

    if (choice?.finish_reason === "content_filter") {
      throw new Error(
        "Groq could not process the supplied text.",
      );
    }

    const content = choice?.message?.content;

    if (
      typeof content !== "string" ||
      !content.trim()
    ) {
      throw new Error(
        "Groq returned an empty grammar response.",
      );
    }

    return content;
  } catch (error) {
    if (
      error instanceof Error &&
      error.name === "AbortError"
    ) {
      throw new GroqRequestError(
        "Groq grammar request timed out after 45 seconds.",
        504,
      );
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function isTemporaryError(error: unknown): boolean {
  if (!(error instanceof GroqRequestError)) {
    return false;
  }

  return (
    error.status === 429 ||
    error.status === 500 ||
    error.status === 502 ||
    error.status === 503 ||
    error.status === 504
  );
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getGrammarResponse(
  input: string,
  apiKey: string,
): Promise<string> {
  let lastError: unknown;

  for (
    let attempt = 1;
    attempt <= MAX_ATTEMPTS;
    attempt++
  ) {
    try {
      console.log(
        `Grammar: trying Groq model ${GROQ_MODEL}, attempt ${attempt}`,
      );

      const content = await requestGrammarAI(
        input,
        apiKey,
      );

      console.log(
        `Grammar: successfully used Groq model ${GROQ_MODEL}`,
      );

      return content;
    } catch (error) {
      lastError = error;

      console.error(
        `Groq grammar failed on attempt ${attempt}:`,
        error,
      );

      if (
        error instanceof GroqRequestError &&
        (error.status === 401 || error.status === 403)
      ) {
        throw error;
      }

      if (
        isTemporaryError(error) &&
        attempt < MAX_ATTEMPTS
      ) {
        const delay = 2000 * Math.pow(2, attempt - 1);

        console.log(
          `Retrying Groq in ${delay}ms...`,
        );

        await wait(delay);
        continue;
      }

      break;
    }
  }

  if (lastError instanceof GroqRequestError) {
    if (isTemporaryError(lastError)) {
      throw new Error(
        "Groq grammar service is currently overloaded or rate-limited. Please try again shortly.",
      );
    }

    throw lastError;
  }

  throw lastError instanceof Error
    ? lastError
    : new Error("All Groq grammar attempts failed.");
}

function parseGrammarResponse(
  content: string,
): AIGrammarResponse {
  const cleaned = content
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "");

  try {
    const parsed: unknown = JSON.parse(cleaned);

    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("findings" in parsed) ||
      !Array.isArray(parsed.findings)
    ) {
      throw new Error(
        "Response must contain a findings array.",
      );
    }

    return parsed as AIGrammarResponse;
  } catch (error) {
    console.error("Invalid Groq JSON response:", content);

    throw new Error(
      error instanceof Error &&
      error.message.includes("findings")
        ? error.message
        : "Groq returned invalid JSON.",
    );
  }
}

const GRAMMAR_CHUNK_SIZE = 9000;
const MAX_GRAMMAR_INPUT = 60000;

function splitGrammarText(
  text: string,
  maxLength: number,
): Array<{ text: string; offset: number }> {
  const chunks: Array<{ text: string; offset: number }> = [];
  let start = 0;

  while (start < text.length) {
    let end = Math.min(start + maxLength, text.length);

    if (end < text.length) {
      const section = text.slice(start, end);

      const boundaries = [
        { index: section.lastIndexOf("\n\n"), width: 2 },
        { index: section.lastIndexOf("\n"), width: 1 },
        { index: section.lastIndexOf(". "), width: 2 },
        { index: section.lastIndexOf("? "), width: 2 },
        { index: section.lastIndexOf("! "), width: 2 },
        { index: section.lastIndexOf("; "), width: 2 },
        { index: section.lastIndexOf(" "), width: 1 },
      ];

      const boundary = boundaries
        .filter((item) => item.index >= maxLength * 0.6)
        .sort((a, b) => b.index - a.index)[0];

      if (boundary) {
        end = start + boundary.index + boundary.width;
      }
    }

    chunks.push({
      text: text.slice(start, end),
      offset: start,
    });

    start = end;
  }

  return chunks;
}

export async function analyzeGrammarText(
  text: string,
): Promise<GrammarEngineResult> {
  const input = text.trim();

  if (!input) {
    return {
      text_length: 0,
      finding_count: 0,
      findings: [],
    };
  }

  if (input.length > MAX_GRAMMAR_INPUT) {
    throw new Error(
      `Grammar input exceeds the maximum of ${MAX_GRAMMAR_INPUT} characters.`,
    );
  }

  const apiKey = process.env.GROQ_API_KEY;

  if (!apiKey?.trim()) {
    throw new Error(
      "GROQ_API_KEY is missing from environment variables.",
    );
  }

  const chunks = splitGrammarText(input, GRAMMAR_CHUNK_SIZE);
  const allFindings: GrammarEngineFinding[] = [];
  const seenFindings = new Set<string>();

  console.log(
    `Grammar: analyzing ${input.length} characters in ${chunks.length} chunk(s).`,
  );

  for (let index = 0; index < chunks.length; index++) {
    const chunk = chunks[index];

    console.log(
      `Grammar: processing chunk ${index + 1}/${chunks.length}.`,
    );

    const content = await getGrammarResponse(
      chunk.text,
      apiKey,
    );

    const parsed = parseGrammarResponse(content);
    const usedOffsets = new Set<number>();

    const findings = parsed.findings
      .filter(
        (item): item is AIGrammarFinding =>
          typeof item === "object" &&
          item !== null &&
          typeof item.original === "string" &&
          typeof item.correction === "string" &&
          typeof item.explanation === "string" &&
          typeof item.category === "string" &&
          typeof item.severity === "string",
      )
      .map((item) =>
        validateFinding(item, chunk.text, usedOffsets),
      )
      .filter(
        (
          finding,
        ): finding is GrammarEngineFinding =>
          finding !== null,
      );

    for (const finding of findings) {
      const globalStart = finding.start + chunk.offset;
      const globalEnd = finding.end + chunk.offset;

      const deduplicationKey =
        `${globalStart}:${globalEnd}:${finding.original}`;

      if (seenFindings.has(deduplicationKey)) {
        continue;
      }

      seenFindings.add(deduplicationKey);

      allFindings.push({
        ...finding,
        start: globalStart,
        end: globalEnd,
      });
    }
  }

  allFindings.sort((a, b) => a.start - b.start);

  console.log(
    `Grammar: completed ${chunks.length} chunk(s), found ${allFindings.length} issue(s).`,
  );

  return {
    text_length: input.length,
    finding_count: allFindings.length,
    findings: allFindings,
  };
}