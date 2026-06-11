import apiClient from "./client";

export async function generateContent(
  query: string,
  persona: string,
  contentType: string,
  targetUrl: string,
  mode: string,
  aiFaq: string = "",
  platformFaq: string = "",
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
      mode,
    }
  );

  return response.data;
}
