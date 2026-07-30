import type { LlmProvider } from "@/types/experimentLab";

type ProviderOption =
  | {
      id: LlmProvider;
      label: string;
      status: "available";
    }
  | {
      id: "claude" | "gemini" | "perplexity";
      label: string;
      status: "coming_soon";
    };

const providerOptions: ProviderOption[] = [
  { id: "chatgpt", label: "ChatGPT", status: "available" },
  { id: "claude", label: "Claude", status: "coming_soon" },
  { id: "gemini", label: "Gemini", status: "coming_soon" },
  { id: "perplexity", label: "Perplexity", status: "coming_soon" },
];

type LlmProviderSelectorProps = {
  value: LlmProvider;
  onChange: (provider: LlmProvider) => void;
};

export function LlmProviderSelector({
  onChange,
  value,
}: LlmProviderSelectorProps) {
  return (
    <div className="space-y-2">
      <span className="text-sm text-zinc-400">Provider</span>
      <div className="grid gap-2 rounded-lg border border-zinc-800 bg-black p-3 sm:grid-cols-2">
        {providerOptions.map((option) => {
          const isAvailable = option.status === "available";
          const isSelected = option.id === value;

          return (
            <button
              key={option.id}
              aria-disabled={!isAvailable}
              className={[
                "group relative rounded-md border px-3 py-2 text-left text-sm transition",
                isSelected
                  ? "border-blue-500 bg-blue-950/40 text-blue-100"
                  : "border-zinc-800 bg-zinc-950 text-zinc-300",
                isAvailable
                  ? "cursor-pointer hover:border-blue-500"
                  : "cursor-not-allowed opacity-55",
              ].join(" ")}
              title={!isAvailable ? "Support planned in a future release." : ""}
              type="button"
              onClick={() => {
                if (isAvailable) {
                  onChange(option.id as LlmProvider);
                }
              }}
            >
              <span className="flex items-center justify-between gap-2">
                <span>{option.label}</span>
                {isSelected && <span className="text-blue-300">✓</span>}
              </span>
              {!isAvailable && (
                <>
                  <span className="mt-1 block text-xs text-zinc-500">
                    Coming Soon
                  </span>
                  <span className="pointer-events-none absolute left-2 top-full z-20 mt-2 hidden w-56 rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-300 shadow-xl group-hover:block group-focus:block">
                    Support planned in a future release.
                  </span>
                </>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
