import apiClient from "./client";

export async function publishContent(
  contentId: number
) {

  const response =
    await apiClient.post(
      `/api/v1/publishing/publish/${contentId}`
    );

  return response.data;
}