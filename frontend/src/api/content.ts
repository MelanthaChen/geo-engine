import apiClient from "./client";

export async function generateContent(
  query: string,
  persona: string,
  contentType: string,
  mode: string,
  aiFaq: string = "",
  platformFaq: string = "",
  faqSource: string = "ai_faq",
  sourceFaqSetId?: number | null,
  publishPlatform: string = "reddit",
) {

  const response = await apiClient.post(
    "/api/v1/content/generate",
    {
      query,
      persona,
      content_type: contentType,
      ai_faq: aiFaq,
      platform_faq: platformFaq,
      faq_source: faqSource,
      source_faq_set_id: sourceFaqSetId,
      publish_platform: publishPlatform,
      mode,
    }
  );

  return response.data;
}
