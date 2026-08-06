import { useCallback, useEffect, useState } from "react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import {
  fetchCitationTests,
  runPromptCitationTest,
  type CitationProviderResult,
  type CitationTestRun,
} from "@/api/citationTests";
import { useProperty } from "@/contexts/PropertyContext";
import type { LlmProvider } from "@/types/experimentLab";
import {
  comparisonProviders,
  providerLabel,
} from "@/types/providerComparison";

const executableProviders: LlmProvider[] = ["chatgpt", "perplexity"];

function isExecutableProvider(provider: string): provider is LlmProvider {
  return executableProviders.includes(provider as LlmProvider);
}

export function CitationTests() {
  const { activeProperty } = useProperty();
  const [testRuns, setTestRuns] = useState<CitationTestRun[]>([]);
  const [prompt, setPrompt] = useState("");
  const [selectedProviders, setSelectedProviders] = useState<LlmProvider[]>([
    "chatgpt",
    "perplexity",
  ]);
  const [expandedTestId, setExpandedTestId] = useState<number | string | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [runMessage, setRunMessage] = useState("");

  const loadTests = useCallback(async () => {
    if (!activeProperty) {
      setTestRuns([]);
      return;
    }

    try {
      setLoading(true);
      const result = await fetchCitationTests();

      setTestRuns(result.runs || groupLegacyRows(result.tests || []));
    } catch (error) {
      console.error(error);
      setTestRuns([]);
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
    if (!activeProperty || !prompt.trim() || selectedProviders.length === 0) {
      return;
    }

    try {
      setLoading(true);
      setRunMessage("");
      const result = await runPromptCitationTest({
        property_id: activeProperty.id,
        prompt: prompt.trim(),
        models: selectedProviders.map(providerLabel),
        provider: selectedProviders[0],
        providers: selectedProviders,
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

  function toggleProvider(provider: string) {
    if (!executableProviders.includes(provider as LlmProvider)) {
      return;
    }

    setSelectedProviders((currentProviders) => {
      if (currentProviders.includes(provider as LlmProvider)) {
        const nextProviders = currentProviders.filter(
          (item) => item !== provider,
        );

        return nextProviders.length > 0 ? nextProviders : currentProviders;
      }

      return [...currentProviders, provider as LlmProvider];
    });
  }

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
        <CardContent className="grid gap-4 p-6 lg:grid-cols-[1fr_420px_auto]">
          <label className="space-y-2">
            <span className="text-sm text-zinc-400">Prompt</span>
            <input
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
              placeholder="best ai resume builder for students"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm text-zinc-400">Providers</span>
            <div className="grid grid-cols-2 gap-2 rounded-lg border border-zinc-800 bg-black p-3">
              {comparisonProviders.map((provider) => {
                const enabled = isExecutableProvider(provider.id);
                const executableId = isExecutableProvider(provider.id)
                  ? provider.id
                  : null;
                const selected =
                  executableId !== null &&
                  selectedProviders.includes(executableId);

                return (
                <label
                  className={[
                    "flex items-center gap-2 text-sm",
                    enabled
                      ? "cursor-pointer text-zinc-300"
                      : "cursor-not-allowed text-zinc-500",
                  ].join(" ")}
                  key={provider.id}
                  title={
                    enabled
                      ? ""
                      : "Support planned in a future release."
                  }
                >
                  <input
                    checked={selected}
                    className="h-4 w-4 accent-blue-500"
                    disabled={!enabled}
                    onChange={() => toggleProvider(provider.id)}
                    type="checkbox"
                  />
                  {provider.label}
                  {!enabled && (
                    <span className="text-xs text-zinc-600">
                      Coming Soon
                    </span>
                  )}
                </label>
                );
              })}
            </div>
          </label>

          <div className="flex items-end">
            <Button
              disabled={
                !activeProperty ||
                !prompt.trim() ||
                selectedProviders.length === 0 ||
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
              comparison. ChatGPT and Perplexity execute today.
            </p>
          </div>

          {testRuns.map((group) => (
            <div
              key={group.run_id}
              className="rounded-xl border border-zinc-800 bg-black p-4"
            >
              <button
                className="w-full text-left"
                onClick={() =>
                  setExpandedTestId((currentId) =>
                    currentId === group.run_id ? null : group.run_id,
                  )
                }
                type="button"
              >
                <p className="text-sm font-semibold text-zinc-100">
                  {group.question || group.prompt}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {group.completed_at || group.created_at
                    ? new Date(
                        group.completed_at || group.created_at || "",
                      ).toLocaleString()
                    : "No timestamp"}
                </p>
              </button>

              <ProviderResultCards
                expanded={expandedTestId === group.run_id}
                results={group.results}
              />
            </div>
          ))}

          {testRuns.length === 0 && (
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

function ProviderResultCards({
  expanded,
  results,
}: {
  expanded: boolean;
  results: CitationProviderResult[];
}) {
  const resultMap = new Map<string, CitationProviderResult>(
    results.map((result) => [result.provider, result]),
  );
  const visibleProviders = comparisonProviders.filter(
    (provider) =>
      isExecutableProvider(provider.id) || resultMap.has(provider.id),
  );

  return (
    <div className="mt-4 grid gap-4 xl:grid-cols-2">
      {visibleProviders.map((provider) => {
        const result = resultMap.get(provider.id);

        return (
          <div
            className="rounded-lg border border-zinc-800 bg-zinc-950 p-4"
            key={provider.id}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium text-zinc-100">{provider.label}</p>
                <p className="mt-1 text-xs text-zinc-500">
                  {result?.status || "Not run"}
                </p>
              </div>
              <span
                className={[
                  "rounded-full border px-2 py-1 text-xs",
                  result?.mentioned
                    ? "border-emerald-700 bg-emerald-950 text-emerald-300"
                    : "border-zinc-700 bg-black text-zinc-400",
                ].join(" ")}
              >
                {result?.mentioned ? "Mentioned" : "No Mention"}
              </span>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <MiniMetric
                label="Rank"
                value={result?.rank ? `#${result.rank}` : "-"}
              />
              <MiniMetric
                label="Latency"
                value={
                  result?.latency_ms === null ||
                  result?.latency_ms === undefined
                    ? "-"
                    : `${result.latency_ms} ms`
                }
              />
              <MiniMetric
                label="Citations"
                value={String(result?.citations?.length || 0)}
              />
            </div>

            {result?.citations && result.citations.length > 0 && (
              <div className="mt-4 space-y-1">
                <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">
                  Citations
                </p>
                {result.citations.slice(0, 5).map((citation) => (
                  <a
                    className="block truncate text-sm text-blue-400 underline hover:text-blue-300"
                    href={citation}
                    key={citation}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {citation}
                  </a>
                ))}
              </div>
            )}

            <div className="mt-4 whitespace-pre-wrap rounded-lg border border-zinc-800 bg-black p-3 text-sm leading-6 text-zinc-300">
              {expanded
                ? result?.raw_response || result?.error_message || "No response."
                : result?.response_snippet ||
                  result?.error_message ||
                  "No response stored."}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-black p-3">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-zinc-100">{value}</p>
    </div>
  );
}

function groupLegacyRows(tests: Array<{
  id: number | string;
  run_id: number | null;
  property_id: number | null;
  provider: LlmProvider | null;
  model: string | null;
  prompt: string | null;
  query: string | null;
  target_brand: string | null;
  status: string | null;
  mentioned: boolean | null;
  rank: number | null;
  response_snippet: string | null;
  raw_response: string | null;
  citations?: string[];
  latency_ms?: number | null;
  error_message?: string | null;
  tested_at: string | null;
  last_run: string | null;
  created_at: string | null;
}>): CitationTestRun[] {
  const groups = new Map<number | string, CitationTestRun>();

  for (const test of tests) {
    const key = test.run_id || test.id;
    const existing = groups.get(key);
    const result: CitationProviderResult = {
      id: Number(test.id),
      model: test.model || providerLabel(test.provider),
      provider: test.provider || "chatgpt",
      status: test.status,
      mentioned: test.mentioned,
      rank: test.rank,
      response_snippet: test.response_snippet,
      raw_response: test.raw_response,
      response: test.raw_response,
      citations: test.citations || [],
      latency_ms: test.latency_ms || null,
      error_message: test.error_message || null,
      tested_at: test.tested_at,
    };

    if (existing) {
      existing.results.push(result);
      continue;
    }

    groups.set(key, {
      run_id: Number(test.run_id || test.id),
      property_id: test.property_id,
      question: test.prompt || test.query || "Untitled prompt",
      prompt: test.prompt || test.query || "Untitled prompt",
      target_brand: test.target_brand,
      provider: test.provider,
      status: test.status,
      created_at: test.created_at,
      completed_at: test.last_run || test.tested_at,
      results: [result],
    });
  }

  return Array.from(groups.values());
}
