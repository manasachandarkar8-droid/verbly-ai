
import { NextResponse } from "next/server";
import { generateContentSuggestions } from "@/lib/contentSuggestions/suggestionService";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    // 1. Read request body
    const body = await request.json();

    const url = body?.url;
    const text = body?.text;

    // 2. Validate website URL
    if (!url || typeof url !== "string") {
      return NextResponse.json(
        {
          success: false,
          error: "Website URL is required.",
        },
        { status: 400 },
      );
    }

    let websiteUrl = url.trim();

    if (
      !websiteUrl.startsWith("http://") &&
      !websiteUrl.startsWith("https://")
    ) {
      websiteUrl = `https://${websiteUrl}`;
    }

    try {
      const parsedUrl = new URL(websiteUrl);

      if (
        parsedUrl.protocol !== "http:" &&
        parsedUrl.protocol !== "https:"
      ) {
        throw new Error("Invalid protocol.");
      }
    } catch {
      return NextResponse.json(
        {
          success: false,
          error: "Invalid website URL.",
        },
        { status: 400 },
      );
    }

    // 3. Validate extracted website content
    if (!text || typeof text !== "string") {
      return NextResponse.json(
        {
          success: false,
          error: "Website content is required.",
        },
        { status: 400 },
      );
    }

    const websiteText = text.trim();

    if (!websiteText) {
      return NextResponse.json(
        {
          success: false,
          error: "No readable website content was provided.",
        },
        { status: 422 },
      );
    }

    if (websiteText.length > 20000) {
      return NextResponse.json(
        {
          success: false,
          error: "Website content exceeds the 20000 character limit.",
        },
        { status: 413 },
      );
    }

    // 4. Generate AI content suggestions
    const suggestions = await generateContentSuggestions(
      websiteText,
      websiteUrl,
    );

    // 5. Return suggestions
    return NextResponse.json({
      success: true,
      url: websiteUrl,
      totalSuggestions: suggestions.length,
      suggestions,
    });
  } catch (error) {
    console.error("Content Suggestions API error:", error);

    return NextResponse.json(
      {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to generate content suggestions.",
      },
      { status: 500 },
    );
  }
}
