export type ComparisonProviderId =
  | "chatgpt"
  | "claude"
  | "gemini"
  | "perplexity";

export type ProviderComparisonStatus = "active" | "completed" | "coming_soon";

export type ProviderComparisonRow = {
  provider: ComparisonProviderId;
  label: string;
  status: ProviderComparisonStatus;
  mentioned?: boolean | null;
  rank?: number | null;
  citation?: string | null;
  latency?: string | null;
};

export const comparisonProviders: Array<{
  id: ComparisonProviderId;
  label: string;
  status: ProviderComparisonStatus;
}> = [
  { id: "chatgpt", label: "ChatGPT", status: "active" },
  { id: "claude", label: "Claude", status: "coming_soon" },
  { id: "gemini", label: "Gemini", status: "coming_soon" },
  { id: "perplexity", label: "Perplexity", status: "active" },
];

export function providerLabel(provider?: string | null) {
  const normalized = (provider || "chatgpt").toLowerCase();
  const match = comparisonProviders.find((item) => item.id === normalized);

  return match?.label || "ChatGPT";
}
