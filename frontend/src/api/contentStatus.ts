import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL;

export async function getContentStatus(
  contentId: number,
) {
  const response = await axios.get(
    `${API_BASE_URL}/api/v1/content/${contentId}`,
  );

  return response.data;
}