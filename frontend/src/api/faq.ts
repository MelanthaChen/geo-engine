import apiClient from "./client"

export type PlatformQuestion = {
  id: number;
  property_id: number | null;
  platform: string;
  title: string;
  body: string | null;
  url: string | null;
  author: string | null;
  hashtags?: string[];
  score: number | null;
  engagement_metrics?: Record<string, unknown>;
  retrieval_method?: string | null;
  raw_metadata?: Record<string, unknown>;
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
  publishPlatform: string = "reddit",
  propertyId?: number | null,
  accountId?: number | null,
): Promise<GenerateFaqsResponse> {
  const params = new URLSearchParams({
    mode,
    content_type: contentType,
    publish_platform: publishPlatform,
  });

  if (propertyId) {
    params.set("property_id", String(propertyId));
  }

  if (accountId) {
    params.set("account_id", String(accountId));
  }

  const response = await apiClient.get(
    `/api/v1/content/faqs/${encodeURIComponent(target)}?${params.toString()}`
  )

  return response.data
}
