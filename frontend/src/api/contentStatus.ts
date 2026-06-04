import axios from "axios";

const API_BASE_URL =
  "https://geo-engine.onrender.com";

export async function getContentStatus(
  contentId: number,
) {
  const response = await axios.get(
    `${API_BASE_URL}/api/v1/content/${contentId}`,
  );

  return response.data;
}