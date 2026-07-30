import { useCallback, useEffect, useState } from "react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import {
  fetchCitationTests,
  runPromptCitationTest,
  type CitationTestRow,
} from "@/api/citationTests";
import { LlmProviderSelector } from "@/components/LlmProviderSelector";
import { ProviderComparisonTable } from "@/components/ProviderComparisonTable";
import { useProperty } from "@/contexts/PropertyContext";
import type { LlmProvider } from "@/types/experimentLab";
import type { ProviderComparisonRow } from "@/types/providerComparison";

const modelOptions = [
  { label: "ChatGPT", enabled: true },
  { label: "Claude", enabled: false },
  { label: "Gemini", enabled: false },
  { label: "Perplexity", enabled: false },
];

export function CitationTests() {
  const { activeProperty } = useProperty();
  const [tests, setTests] = useState<CitationTestRow[]>([]);
  const [prompt, setPrompt] = useState("");
  const [provider, setProvider] = useState<LlmProvider>("chatgpt");
  const [selectedModels, setSelectedModels] = useState<string[]>(["ChatGPT"]);
  const [expandedTestId, setExpandedTestId] = useState<number | string | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [runMessage, setRunMessage] = useState("");

  const loadTests = useCallback(async () => {
    if (!activeProperty) {
      setTests([]);
      return;
    }

    try {
      setLoading(true);
      const result = await fetchCitationTests();

      setTests(result);
    } catch (error) {
      console.error(error);
      setTests([]);
    } finally {
      setLoading(false);
    }
  }, [activeProperty]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadTests();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadTests]);

  async function handleRunTest() {
    if (!activeProperty || !prompt.trim()) {
      return;
    }

    try {
      setLoading(true);
      setRunMessage("");
      const result = await runPromptCitationTest({
        property_id: activeProperty.id,
        prompt: prompt.trim(),
        models: selectedModels,
        provider,
      });

      if (result.error) {
        throw new Error(result.error);
      }

      setRunMessage("Citation test finished.");
      setPrompt("");
      await loadTests();
    } catch (error) {
      console.error(error);
      setRunMessage(
        error instanceof Error
          ? error.message
          : "Failed to run citation test.",
      );
    } finally {
      setLoading(false);
    }
  }

  function toggleModel(modelName: string) {
    if (modelName !== "ChatGPT") {
      return;
    }

    setSelectedModels((currentModels) => {
      if (currentModels.includes(modelName)) {
        const nextModels = currentModels.filter((item) => item !== modelName);

        return nextModels.length > 0 ? nextModels : currentModels;
      }

      return [...currentModels, modelName];
    });
  }

  const testGroups = groupCitationTests(tests);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Experiments
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Citation Tests
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Run property-scoped prompt tests and inspect previous model
          responses.
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
        <CardContent className="grid gap-4 p-6 lg:grid-cols-[1fr_280px_320px_auto]">
          <label className="space-y-2">
            <span className="text-sm text-zinc-400">Prompt</span>
            <input
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
              placeholder="best ai resume builder for students"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
          </label>

          <LlmProviderSelector value={provider} onChange={setProvider} />

          <label className="space-y-2">
            <span className="text-sm text-zinc-400">Models</span>
            <div className="grid grid-cols-2 gap-2 rounded-lg border border-zinc-800 bg-black p-3">
              {modelOptions.map((model) => (
                <label
                  className={[
                    "flex items-center gap-2 text-sm",
                    model.enabled
                      ? "cursor-pointer text-zinc-300"
                      : "cursor-not-allowed text-zinc-500",
                  ].join(" ")}
                  key={model.label}
                  title={
                    model.enabled
                      ? ""
                      : "Support planned in a future release."
                  }
                >
                  <input
                    checked={selectedModels.includes(model.label)}
                    className="h-4 w-4 accent-blue-500"
                    disabled={!model.enabled}
                    onChange={() => toggleModel(model.label)}
                    type="checkbox"
                  />
                  {model.label}
                  {!model.enabled && (
                    <span className="text-xs text-zinc-600">
                      Coming Soon
                    </span>
                  )}
                </label>
              ))}
            </div>
          </label>

          <div className="flex items-end">
            <Button
              disabled={
                !activeProperty ||
                !prompt.trim() ||
                selectedModels.length === 0 ||
                loading
              }
              onClick={handleRunTest}
            >
              {loading ? "Running..." : "Run Test"}
            </Button>
          </div>

          {runMessage && (
            <div className="rounded-lg border border-amber-800 bg-amber-950/50 p-3 text-sm text-amber-200 lg:col-span-4">
              {runMessage}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="space-y-4 p-6">
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">
              Provider Comparison
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              Each prompt is displayed as a cross-provider citation visibility
              comparison. ChatGPT is the only active provider today.
            </p>
          </div>

          {testGroups.map((group) => (
            <div
              key={group.id}
              className="rounded-xl border border-zinc-800 bg-black p-4"
            >
              <button
                className="w-full text-left"
                onClick={() =>
                  setExpandedTestId((currentId) =>
                    currentId === group.id ? null : group.id,
                  )
                }
                type="button"
              >
                <p className="text-sm font-semibold text-zinc-100">
                  {group.prompt}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {group.timestamp
                    ? new Date(group.timestamp).toLocaleString()
                    : "No timestamp"}
                </p>
              </button>

              <div className="mt-4">
                <ProviderComparisonTable rows={group.rows} />
              </div>

              {expandedTestId === group.id && (
                <div className="mt-4 space-y-4">
                  <div>
                    <p className="mb-2 text-xs uppercase tracking-[0.16em] text-zinc-500">
                      ChatGPT Full Response
                    </p>
                    <div className="whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-sm leading-6 text-zinc-300">
                      {group.rawResponse || "No response stored."}
                    </div>
                  </div>
                  {group.responseSnippet && (
                    <div>
                      <p className="mb-2 text-xs uppercase tracking-[0.16em] text-zinc-500">
                        Response Snippet
                      </p>
                      <div className="whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-sm leading-6 text-zinc-300">
                        {group.responseSnippet}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {testGroups.length === 0 && (
            <div className="rounded-lg border border-zinc-800 bg-black px-5 py-8 text-sm text-zinc-500">
              {loading
                ? "Loading citation tests..."
                : "No citation tests for the current property."}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function groupCitationTests(tests: CitationTestRow[]) {
  const groups = new Map<
    string,
    {
      id: string;
      prompt: string;
      timestamp: string | null;
      rawResponse: string | null;
      responseSnippet: string | null;
      rows: ProviderComparisonRow[];
    }
  >();

  for (const test of tests) {
    const key = String(test.run_id || test.id);
    const prompt = test.prompt || test.query || "Untitled prompt";
    const timestamp = test.last_run || test.tested_at || test.created_at;
    const existing = groups.get(key);
    const row: ProviderComparisonRow = {
      provider: "chatgpt",
      label: "ChatGPT",
      status: "completed",
      mentioned: test.mentioned,
      rank: test.rank,
      citation: test.response_snippet || test.citation_type || null,
      latency: null,
    };

    if (!existing) {
      groups.set(key, {
        id: key,
        prompt,
        timestamp,
        rawResponse: test.raw_response || test.ai_response || null,
        responseSnippet: test.response_snippet,
        rows: [row],
      });
      continue;
    }

    existing.rows = [row];
    existing.rawResponse ||= test.raw_response || test.ai_response || null;
    existing.responseSnippet ||= test.response_snippet;
  }

  return Array.from(groups.values());
}
