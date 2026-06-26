import apiClient from "./client"

export type PlatformQuestion = {
  id: number;
  property_id: number | null;
  platform: string;
  title: string;
  body: string | null;
  url: string | null;
  author: string | null;
  score: number | null;
  created_at: string | null;
  discovered_at: string | null;
  content_hash: string;
};

export type GenerateFaqsResponse = {
  target: string;
  mode: string;
  faqs: string;
  faq_set_id: number;
  faq_set: {
    id: number;
    category: string;
    faq_source: string;
    questions: string[];
  };
  platform_questions: PlatformQuestion[];
};

export async function generateFaqs(
  target: string,
  mode: string,
  contentType: string = "comparison",
): Promise<GenerateFaqsResponse> {
  const params = new URLSearchParams({
    mode,
    content_type: contentType,
  });

  const response = await apiClient.get(
    `/api/v1/content/faqs/${encodeURIComponent(target)}?${params.toString()}`
  )

  return response.data
}
