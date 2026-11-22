import { apiRequest } from "./apiClient";

export interface ExtractionResponse {
  requested_url: string;
  final_url: string;
  status_code: number;
  title: string | null;
  author: string | null;
  description: string | null;
  site_name: string | null;
  published_date: string | null;
  main_text: string;
  word_count: number;
  character_count: number;
}

export async function extractWebsite(
  url: string,
): Promise<ExtractionResponse> {
  if (!url.trim()) {
    throw new Error("Please enter a website URL.");
  }

  return apiRequest<ExtractionResponse>(
    "/extraction",
    { url: url.trim() },
    60_000,
  );
}