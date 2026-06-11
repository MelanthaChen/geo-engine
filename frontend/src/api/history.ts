import apiClient from "./client"

export async function fetchContentHistory() {

  const response = await apiClient.get(
    "/api/v1/content/history"
  )

  return response.data
}

export async function deleteFaqHistory(
  id: number
) {
  const response = await apiClient.delete(
    `/api/v1/history/faqs/${id}`
  )

  return response.data
}

export async function deleteGeneratedContentHistory(
  id: number
) {
  const response = await apiClient.delete(
    `/api/v1/history/content/${id}`
  )

  return response.data
}
