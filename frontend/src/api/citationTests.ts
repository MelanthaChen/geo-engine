import apiClient from "./client";
import type { LlmProvider } from "@/types/experimentLab";

export type CitationTestRow = {
  id: number | string;
  run_id: number | null;
  property_id: number | null;
  content_id: number | null;
  platform: string | null;
  provider: LlmProvider | null;
  model: string | null;
  query: string | null;
  prompt: string | null;
  target_brand: string | null;
  status: string | null;
  source_type: string | null;
  citation_target: string | null;
  ai_response: string | null;
  raw_response: string | null;
  response_snippet: string | null;
  citations?: string[];
  mentioned: boolean | null;
  rank: number | null;
  latency_ms?: number | null;
  evidence_found: boolean | null;
  citation_type: string | null;
  confidence_score: number | null;
  visibility_score: number | null;
  matched_keywords: string | null;
  tested_at: string | null;
  last_run: string | null;
  created_at: string | null;
};

export type CitationProviderResult = {
  id: number;
  model: string;
  provider: LlmProvider;
  status: string | null;
  mentioned: boolean | null;
  rank: number | null;
  response_snippet: string | null;
  raw_response: string | null;
  response: string | null;
  citations: string[];
  latency_ms: number | null;
  error_message: string | null;
  tested_at: string | null;
};

export type CitationTestRun = {
  run_id: number;
  property_id: number | null;
  question: string;
  prompt: string;
  target_brand: string | null;
  provider: LlmProvider | null;
  status: string | null;
  created_at: string | null;
  completed_at: string | null;
  results: CitationProviderResult[];
};

export type RunCitationTestRequest = {
  property_id: number;
  prompt: string;
  models: string[];
  provider?: LlmProvider;
  providers?: LlmProvider[];
};

export async function fetchCitationTests() {
  const response = await apiClient.get<{
    tests: CitationTestRow[];
    runs?: CitationTestRun[];
  }>(
    "/api/v1/citation-tests",
  );

  return response.data;
}

export async function runPromptCitationTest(
  request: RunCitationTestRequest,
) {
  const response = await apiClient.post(
    "/api/v1/citation-tests/run",
    request,
  );

  return response.data;
}
