import apiClient from "./client";

export async function runCitationTest(
  contentId: number,
  sourceType = "published_content",
) {

  const response = await apiClient.post(
    `/api/v1/citation-tests/run/${contentId}`,
    null,
    {
      params: {
        source_type: sourceType,
        provider: "chatgpt",
      },
    }
  );

  return response.data;
}
