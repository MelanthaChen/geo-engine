import apiClient from "./client";

export type CitationTestRow = {
  id: number;
  property_id: number | null;
  content_id: number;
  platform: string;
  query: string;
  source_type: string;
  citation_target: string;
  ai_response: string;
  mentioned: boolean;
  evidence_found: boolean;
  citation_type: string;
  confidence_score: number;
  visibility_score: number;
  matched_keywords: string;
  tested_at: string;
};

export async function fetchCitationTests() {
  const response = await apiClient.get<{ tests: CitationTestRow[] }>(
    "/api/v1/citation-tests",
  );

  return response.data.tests;
}
