import axios from "axios";

const API_BASE =
  "http://127.0.0.1:8000/api/v1";


export async function runCitationTest(
  contentId: number
) {

  const response = await axios.post(
    `${API_BASE}/citation-tests/run/${contentId}`
  );

  return response.data;
}