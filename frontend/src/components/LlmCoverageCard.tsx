import { Card, CardContent } from "../../@/components/ui/card";
import { comparisonProviders } from "@/types/providerComparison";

export function LlmCoverageCard() {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <h2 className="text-lg font-semibold text-zinc-50">LLM Coverage</h2>
        <div className="mt-4 space-y-3">
          {comparisonProviders.map((provider) => (
            <div
              key={provider.id}
              className="flex items-center justify-between rounded-lg border border-zinc-800 bg-black p-3"
            >
              <span className="text-sm font-medium text-zinc-100">
                {provider.label}
              </span>
              <span
                className={
                  provider.id === "chatgpt"
                    ? "rounded-full border border-emerald-700 bg-emerald-950 px-3 py-1 text-xs text-emerald-300"
                    : "rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1 text-xs text-zinc-400"
                }
              >
                {provider.id === "chatgpt" ? "Active" : "Coming Soon"}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
