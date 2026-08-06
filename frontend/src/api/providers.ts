import apiClient from "./client";

export type ProviderStatus = {
  id: "chatgpt" | "perplexity" | "claude" | "gemini";
  name: string;
  status: "connected" | "missing_session" | "coming_soon";
  detail: string;
  profile_path?: string;
};

export async function fetchProviderStatus() {
  const response = await apiClient.get<{ providers: ProviderStatus[] }>(
    "/api/v1/providers/status",
  );

  return response.data.providers;
}
