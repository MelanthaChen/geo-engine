import apiClient from "./client"

export async function generateFaqs(
  target: string,
  mode: string
) {

  const response = await apiClient.get(
    `/api/v1/content/faqs/${target}?mode=${mode}`
  )

  return response.data
}