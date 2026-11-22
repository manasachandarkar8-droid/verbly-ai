import { apiRequest } from "./apiClient";
import type { GenerateRewrite } from "@/lib/rewrite/types";

interface RewriteApiResponse {
  rewritten_text: string;
}

export const generateRewrite: GenerateRewrite = async (request) => {
  const response = await apiRequest<RewriteApiResponse>(
    "/rewrite",
    {
      main_text: request.originalContent,
      tone: request.tone,
      custom_instruction: request.customInstruction?.trim() || null,
    },
    120_000,
  );

  if (
    !response ||
    typeof response.rewritten_text !== "string" ||
    !response.rewritten_text.trim()
  ) {
    throw new Error("The backend returned an invalid rewrite response.");
  }

  return {
    id: crypto.randomUUID(),
    findingId: request.findingId,
    originalContent: request.originalContent,
    rewrittenContent: response.rewritten_text,
    tone: request.tone,
    createdAt: new Date().toISOString(),
  };
};