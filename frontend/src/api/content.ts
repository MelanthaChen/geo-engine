import apiClient from "./client"

export async function generateContent(
  query: string,
  persona: string,
  contentType: string
) {
  const response = await apiClient.post(
    "/api/v1/content/generate",
    {
      query,
      persona,
      content_type: contentType,
    }
  )

  return response.data
}