
export interface ContentSuggestion {
  id: string;
  title: string;
  problem: string;
  location: string;
  whyItMatters: string;
  recommendation: string;
  evidence: string;
  severity: "High" | "Medium" | "Low";
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

// Extract JSON from Gemini response
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
      throw new Error("Gemini did not return valid JSON.");
    }

    return JSON.parse(cleaned.slice(start, end + 1));
  }
}

// Validate Gemini suggestions
function validateSuggestions(
  value: unknown,
): ContentSuggestion[] {
  if (!value || typeof value !== "object") {
    throw new Error("Invalid suggestion response.");
  }

  const data = value as Record<string, unknown>;

  if (!Array.isArray(data.suggestions)) {
    throw new Error("AI suggestions are missing.");
  }

  const validSeverities = ["High", "Medium", "Low"];

  return data.suggestions
    .slice(0, 20)
    .map((item, index) => {
      if (!item || typeof item !== "object") {
        throw new Error("Invalid suggestion item.");
      }

      const suggestion = item as Record<string, unknown>;

      const requiredFields = [
        "title",
        "problem",
        "location",
        "whyItMatters",
        "recommendation",
        "evidence",
      ];

      for (const field of requiredFields) {
        if (
          typeof suggestion[field] !== "string"
        ) {
          throw new Error(
            `Suggestion is missing ${field}.`,
          );
        }
      }

      if (
        typeof suggestion.severity !== "string" ||
        !validSeverities.includes(suggestion.severity)
      ) {
        throw new Error("Invalid suggestion severity.");
      }

      return {
        id: `suggestion-${index + 1}`,
        title: (suggestion.title as string).trim(),
        problem: (suggestion.problem as string).trim(),
        location: (suggestion.location as string).trim(),
        whyItMatters: (
          suggestion.whyItMatters as string
        ).trim(),
        recommendation: (
          suggestion.recommendation as string
        ).trim(),
        evidence: (suggestion.evidence as string).trim(),
        severity: suggestion.severity as
          ContentSuggestion["severity"],
      };
    });
}

// Build Gemini prompt
function buildPrompt(
  websiteText: string,
  url: string,
): string {
  return `
You are an advanced AI website content analysis expert.

Your task is to thoroughly analyze the entire supplied website
content and identify meaningful opportunities for improvement.

WEBSITE URL:
${url}

ANALYSIS INSTRUCTIONS:

Read and understand the complete supplied content before
generating suggestions.

Do not restrict your analysis to predefined categories,
keywords, rules, or a fixed checklist.

Think independently and identify any issue that could affect
the website's quality, usefulness, clarity, accuracy,
completeness, organization, or visitor experience.

Examine the content from different perspectives.

Identify problems such as unclear information, insufficient
explanations, missing details, repetitive information, poor
organization, vague statements, inconsistent information,
weak communication, or irrelevant content.

These are only examples, NOT a fixed list.

You must also identify other problems that you discover
through your own analysis.

IMPORTANT RULES:

1. Analyze the actual supplied website content.
2. Do not depend on keyword matching.
3. Do not limit your analysis to predefined examples.
4. Do not invent problems or missing information without evidence.
5. Do not invent facts about the website.
6. Identify the specific location of each problem wherever possible.
7. Explain why each identified issue matters.
8. Give practical and specific improvement recommendations.
9. Avoid duplicate suggestions.
10. Do not rewrite entire paragraphs or the website.
11. Do not focus on spelling and grammar corrections because
    those belong to a separate feature.
12. Do not force suggestions when the content is already good.
13. Prioritize important improvements.
14. Understand the website's actual purpose and audience.
15. Do not force a fixed number of suggestions.
16. Return only meaningful, evidence-supported findings.
17. Do not confuse an opinion or stylistic preference with
    an actual content problem.

SEVERITY:

High: An important issue that may significantly affect visitors.

Medium: An improvement that would make the content clearer
or more useful.

Low: A minor improvement or optional enhancement.

FOR EACH SUGGESTION PROVIDE:

- title: Short description of the issue.
- problem: What you identified.
- location: Where the issue occurs.
- whyItMatters: Why this issue should be improved.
- recommendation: A specific way to improve it.
- evidence: Relevant original website text, if available.
- severity: High, Medium, or Low.

RETURN ONLY VALID JSON:

{
  "suggestions": [
    {
      "title": "Short issue title",
      "problem": "Description of the identified issue",
      "location": "Relevant section or content location",
      "whyItMatters": "Explanation of its impact",
      "recommendation": "Specific improvement recommendation",
      "evidence": "Relevant original website text",
      "severity": "High"
    }
  ]
}

If no meaningful issues are identified, return:
{
  "suggestions": []
}

WEBSITE CONTENT:

${websiteText}
`;
}

// Main Gemini suggestion function
export async function generateContentSuggestions(
  websiteText: string,
  url: string,
): Promise<ContentSuggestion[]> {
  if (!websiteText || !websiteText.trim()) {
    throw new Error("Website content is required.");
  }

  if (!GEMINI_API_KEY) {
    throw new Error("Gemini API key is not configured.");
  }

  const prompt = buildPrompt(
    websiteText.slice(0, 20000),
    url,
  );

  const endpoint =
    `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  const response = await fetch(endpoint, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
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
        temperature: 0.3,
        responseMimeType: "application/json",
      },
    }),

    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text();

    console.error("Gemini API error:", errorText);

    throw new Error(
      `Gemini API request failed with status ${response.status}.`,
    );
  }

  const data =
    (await response.json()) as GeminiResponse;

  const generatedText =
    data.candidates?.[0]?.content?.parts?.[0]?.text;

  if (!generatedText) {
    throw new Error("Gemini returned an empty response.");
  }

  const parsed = extractJson(generatedText);

  return validateSuggestions(parsed);
}
