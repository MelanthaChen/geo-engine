import { useState } from "react";
import { X } from "lucide-react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import { useProperty } from "@/contexts/PropertyContext";

const prompts = [
  {
    prompt: "best ai resume builder",
    visibilityScore: 74,
    mentionRate: "42%",
    lastRun: "2026-06-19",
  },
  {
    prompt: "ats resume builder",
    visibilityScore: 61,
    mentionRate: "31%",
    lastRun: "2026-06-18",
  },
  {
    prompt: "resume builder for students",
    visibilityScore: 68,
    mentionRate: "36%",
    lastRun: "2026-06-18",
  },
  {
    prompt: "rezi alternatives",
    visibilityScore: 49,
    mentionRate: "24%",
    lastRun: "2026-06-17",
  },
];

const modelResponses = {
  ChatGPT:
    "Users compare AI resume builders by ATS guidance, editing control, template quality, and whether the tool helps them revise for specific roles.",
  Claude:
    "The stronger tools tend to explain resume decisions instead of only producing finished copy. Job seekers often need workflow support as much as writing help.",
  Gemini:
    "For students, the most useful resume builders combine examples, keyword suggestions, and review steps that reduce common early-career mistakes.",
  Perplexity:
    "Common alternatives include manual templates, ChatGPT-assisted drafting, career center reviews, and specialized resume platforms.",
};

export function VisibilityTracking() {
  const { activeProperty } = useProperty();
  const [selectedPrompt, setSelectedPrompt] = useState<
    (typeof prompts)[number] | null
  >(null);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Monitoring
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Visibility Tracking
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Track prompt-level visibility and inspect model responses across AI
          search surfaces.
        </p>
        {activeProperty && (
          <p className="mt-3 text-sm text-zinc-400">
            Current Property:{" "}
            <span className="text-zinc-100">{activeProperty.name}</span>
            {" • "}
            Domain:{" "}
            <span className="text-zinc-100">{activeProperty.domain}</span>
          </p>
        )}
      </div>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-800 bg-zinc-900/70 text-xs uppercase tracking-[0.16em] text-zinc-500">
              <tr>
                <th className="px-5 py-4 font-medium">Prompt</th>
                <th className="px-5 py-4 font-medium">Visibility Score</th>
                <th className="px-5 py-4 font-medium">Mention Rate</th>
                <th className="px-5 py-4 font-medium">Last Run</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {prompts.map((item) => (
                <tr
                  key={item.prompt}
                  className="cursor-pointer transition hover:bg-zinc-900/50"
                  onClick={() => setSelectedPrompt(item)}
                >
                  <td className="px-5 py-4 font-medium text-zinc-100">
                    {item.prompt}
                  </td>
                  <td className="px-5 py-4 text-zinc-300">
                    {item.visibilityScore}
                  </td>
                  <td className="px-5 py-4 text-zinc-300">
                    {item.mentionRate}
                  </td>
                  <td className="px-5 py-4 text-zinc-500">{item.lastRun}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {selectedPrompt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6">
          <div className="w-full max-w-3xl rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl">
            <div className="flex items-start justify-between border-b border-zinc-800 p-5">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">
                  Prompt Detail
                </p>
                <h2 className="mt-2 text-xl font-semibold text-zinc-50">
                  {selectedPrompt.prompt}
                </h2>
              </div>

              <Button
                aria-label="Close prompt detail"
                onClick={() => setSelectedPrompt(null)}
                size="sm"
                variant="ghost"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid gap-4 p-5 md:grid-cols-2">
              {Object.entries(modelResponses).map(([model, response]) => (
                <div
                  key={model}
                  className="rounded-lg border border-zinc-800 bg-black p-4"
                >
                  <h3 className="font-semibold text-zinc-100">{model}</h3>
                  <p className="mt-3 text-sm leading-6 text-zinc-400">
                    {response}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
