import apiClient from "./client"

export async function generateFaqs(
  target: string,
  mode: string,
  contentType: string = "comparison",
  websiteUrl: string = "",
) {
  const params = new URLSearchParams({
    mode,
    content_type: contentType,
  });

  if (websiteUrl) {
    params.set("website_url", websiteUrl);
  }

  const response = await apiClient.get(
    `/api/v1/content/faqs/${encodeURIComponent(target)}?${params.toString()}`
  )

  return response.data
}
