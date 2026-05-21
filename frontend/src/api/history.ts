import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

export async function fetchContentHistory() {

  const response = await axios.get(
    `${API_BASE}/api/v1/content/history`
  );

  return response.data;
}