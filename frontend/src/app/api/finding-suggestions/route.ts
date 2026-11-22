
import { NextRequest, NextResponse } from "next/server";

import type {
  GenerateSuggestionsInput,
} from "@/lib/suggestions/types";

import {
  generateGeminiSuggestions,
} from "@/lib/suggestions/geminiSuggestionService";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const {
      findingId,
      category,
      title,
      explanation,
      recommendedFix,
      sourceExcerpt,
    } = body as GenerateSuggestionsInput;

    if (
      typeof findingId !== "string" ||
      typeof category !== "string" ||
      typeof title !== "string" ||
      typeof explanation !== "string" ||
      typeof recommendedFix !== "string"
    ) {
      return NextResponse.json(
        {
          success: false,
          error: "Required finding details are missing.",
        },
        { status: 400 },
      );
    }

    const input: GenerateSuggestionsInput = {
      findingId,
      category,
      title,
      explanation,
      recommendedFix,
      sourceExcerpt:
        typeof sourceExcerpt === "string"
          ? sourceExcerpt
          : undefined,
    };

    const suggestions =
      await generateGeminiSuggestions(input);

    return NextResponse.json({
      success: true,
      findingId,
      suggestions,
    });
  } catch (error) {
    console.error(
      "Finding suggestions API error:",
      error,
    );

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to generate suggestions.",
      },
      { status: 500 },
    );
  }
}
