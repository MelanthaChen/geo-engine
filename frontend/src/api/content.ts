import apiClient from "./client";

export async function generateContent(
  query: string,
  persona: string,
  contentType: string,
  targetUrl: string,
  mode: string,
  aiFaq: string = "",
  platformFaq: string = "",
  faqSource: string = "ai_faq",
  sourceFaqSetId?: number | null,
) {

  const response = await apiClient.post(
    "/api/v1/content/generate",
    {
      query,
      persona,
      content_type: contentType,
      product_url: targetUrl,
      target_url: targetUrl,
      ai_faq: aiFaq,
      platform_faq: platformFaq,
      faq_source: faqSource,
      source_faq_set_id: sourceFaqSetId,
      mode,
    }
  );

  return response.data;
}
