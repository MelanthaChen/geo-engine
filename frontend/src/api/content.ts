import apiClient from "./client";

export async function generateContent(
  query: string,
  persona: string,
  contentType: string,
  targetUrl: string,
  mode: string,
) {

  const response = await apiClient.post(
    "/api/v1/content/generate",
    {
      query,
      persona,
      content_type: contentType,
      target_url: targetUrl,
      mode,
    }
  );

  return response.data;
}