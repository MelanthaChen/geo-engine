import apiClient from "./client"

export async function fetchContentHistory() {

  const response = await apiClient.get(
    "/api/v1/content/history"
  )

  return response.data
}