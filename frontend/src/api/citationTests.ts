import apiClient from "./client";

export type CitationTestRow = {
  id: number | string;
  run_id: number | null;
  property_id: number | null;
  content_id: number | null;
  platform: string | null;
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
  mentioned: boolean | null;
  rank: number | null;
  evidence_found: boolean | null;
  citation_type: string | null;
  confidence_score: number | null;
  visibility_score: number | null;
  matched_keywords: string | null;
  tested_at: string | null;
  last_run: string | null;
  created_at: string | null;
};

export type RunCitationTestRequest = {
  property_id: number;
  prompt: string;
  models: string[];
};

export async function fetchCitationTests() {
  const response = await apiClient.get<{ tests: CitationTestRow[] }>(
    "/api/v1/citation-tests",
  );

  return response.data.tests;
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
