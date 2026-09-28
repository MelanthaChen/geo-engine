export function searchProviderLabel(provider: string | null | undefined) {
  return provider?.trim() || "Unavailable";
}
