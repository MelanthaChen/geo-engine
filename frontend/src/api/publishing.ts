import apiClient from "./client";

export async function publishContent(
  contentId: number,
  publishPlatform: string,
) {
  const response =
    await apiClient.post(
      `/api/v1/publishing/publish/${contentId}`,
      null,
      {
        params: {
          publish_platform: publishPlatform,
        },
      },
    );

  return response.data;
}
