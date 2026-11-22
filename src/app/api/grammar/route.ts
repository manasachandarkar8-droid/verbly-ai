
import { NextResponse } from "next/server";
import { analyzeGrammarText } from "@/services/grammarEngine";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = await request.json();

    if (!body || typeof body.text !== "string") {
      return NextResponse.json(
        {
          success: false,
          error: "Text is required.",
        },
        { status: 400 },
      );
    }

    const text = body.text;

    if (!text.trim()) {
      return NextResponse.json(
        {
          success: false,
          error: "Text cannot be empty.",
        },
        { status: 400 },
      );
    }

    if (text.length > 12000) {
      return NextResponse.json(
        {
          success: false,
          error: "Text cannot exceed 12,000 characters.",
        },
        { status: 400 },
      );
    }

    const result = await analyzeGrammarText(text);

    const findings = result.findings.map((finding) => {
      const category = finding.category;

      return {
        message: `${finding.original} → ${finding.correction}. ${finding.explanation}`,
        short_message: finding.correction,
        category,
        rule_id: `AI_${category.toUpperCase()}`,
        issue_type: category,
        severity: finding.severity,
        offset: finding.start,
        length: finding.end - finding.start,
        context: finding.original,
        replacements: [finding.correction],
      };
    });

    const data = {
      text_length: result.text_length,
      finding_count: findings.length,
      findings,
      issues: findings,
    };

    return NextResponse.json({
      success: true,
      data,
    });
  } catch (error) {
    console.error("Grammar API error:", error);

    const message =
      error instanceof Error
        ? error.message
        : "Grammar analysis failed.";

    return NextResponse.json(
      {
        success: false,
        error: message,
      },
      { status: 500 },
    );
  }
}
