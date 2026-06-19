import apiClient from "./client";

export async function getContentStatus(
  contentId: number,
) {
  const response = await apiClient.get(
    `/api/v1/content/${contentId}`,
  );

  return response.data;
}
