
import { NextResponse } from "next/server";
import * as cheerio from "cheerio";

import {
  generateGroqHeatmap,
} from "@/lib/heatmap/groqHeatmapService";

import type {
  ExtractedHeatmapSegment,
} from "@/lib/heatmap/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface HeatmapSegment {
  id: string;
  type: "heading" | "paragraph";
  label: string;
  text: string;
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const url = body?.url;

    if (!url || typeof url !== "string") {
      return NextResponse.json(
        { success: false, error: "Website URL is required." },
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

    let parsedUrl: URL;

    try {
      parsedUrl = new URL(websiteUrl);
    } catch {
      return NextResponse.json(
        { success: false, error: "Invalid website URL." },
        { status: 400 },
      );
    }

    if (!["http:", "https:"].includes(parsedUrl.protocol)) {
      return NextResponse.json(
        { success: false, error: "Only HTTP and HTTPS URLs are supported." },
        { status: 400 },
      );
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    let response: Response;

    try {
      response = await fetch(websiteUrl, {
        method: "GET",
        headers: {
          "User-Agent": "Mozilla/5.0 (compatible; VerblyAI/1.0)",
          Accept: "text/html,application/xhtml+xml",
        },
        redirect: "follow",
        cache: "no-store",
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeout);
    }

    if (!response.ok) {
      return NextResponse.json(
        {
          success: false,
          error: `Website returned HTTP ${response.status}.`,
        },
        { status: 502 },
      );
    }

    const contentType = response.headers.get("content-type") || "";

    if (
      !contentType.includes("text/html") &&
      !contentType.includes("application/xhtml+xml")
    ) {
      return NextResponse.json(
        {
          success: false,
          error: "The URL did not return an HTML webpage.",
        },
        { status: 422 },
      );
    }

    const html = await response.text();

    if (!html.trim()) {
      return NextResponse.json(
        {
          success: false,
          error: "The website returned empty content.",
        },
        { status: 422 },
      );
    }

    const $ = cheerio.load(html);

    $(
      "script, style, noscript, iframe, svg, canvas, template, nav, footer, form, header",
    ).remove();

    const mainSelectors = [
      "main",
      "article",
      "[role='main']",
      ".content",
      "#content",
    ];

    // Select the content container without reassigning
    // incompatible Cheerio selection types.
    let contentSelector = "body";
    let longestTextLength = $("body").text().trim().length;

    for (const selector of mainSelectors) {
      const candidateText = $(selector).first().text().trim();

      if (candidateText.length > longestTextLength) {
        longestTextLength = candidateText.length;
        contentSelector = selector;
      }
    }

    const $content = $(contentSelector).first();

    const segments: HeatmapSegment[] = [];
    let paragraphCount = 0;

    $content.find("h1, h2, h3, h4, h5, h6, p").each(
      (index, element) => {
        const text = $(element)
          .text()
          .replace(/\s+/g, " ")
          .replace(/\u00a0/g, " ")
          .trim();

        if (!text || text.length < 10) {
          return;
        }

        const tagName = element.tagName.toLowerCase();
        const isHeading = /^h[1-6]$/.test(tagName);

        if (!isHeading) {
          paragraphCount++;
        }

        segments.push({
          id: `segment-${index + 1}`,
          type: isHeading ? "heading" : "paragraph",
          label: isHeading
            ? `Heading: ${text.slice(0, 80)}`
            : `Paragraph ${paragraphCount}`,
          text: text.slice(0, 3000),
        });
      },
    );

    if (segments.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: "No readable headings or paragraphs were found.",
        },
        { status: 422 },
      );
    }

    // Convert extracted sections into the shared heatmap input type.
    const extractedSegments: ExtractedHeatmapSegment[] =
      segments.map((segment) => ({
        id: segment.id,
        type: segment.type,
        label: segment.label,
        text: segment.text,
      }));

    // Generate actual AI confusion analysis using Groq.
    const heatmap = await generateGroqHeatmap(
      response.url || websiteUrl,
      extractedSegments,
    );

    return NextResponse.json({
      success: true,
      ...heatmap,
    });
  } catch (error) {
    console.error("Heatmap API error:", error);

    const isTimeout =
      error instanceof Error && error.name === "AbortError";

    const message = isTimeout
      ? "The website took too long to respond."
      : error instanceof Error
        ? error.message
        : "Failed to analyze website confusion.";

    return NextResponse.json(
      { success: false, error: message },
      { status: isTimeout ? 504 : 500 },
    );
  }
}
