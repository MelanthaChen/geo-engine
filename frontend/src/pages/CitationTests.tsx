import { Fragment, useCallback, useEffect, useState } from "react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import {
  fetchCitationTests,
  type CitationTestRow,
} from "@/api/citationTests";
import { useProperty } from "@/contexts/PropertyContext";

const models = ["ChatGPT", "Claude", "Gemini", "Perplexity"];

export function CitationTests() {
  const { activeProperty } = useProperty();
  const [tests, setTests] = useState<CitationTestRow[]>([]);
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("ChatGPT");
  const [expandedTestId, setExpandedTestId] = useState<number | null>(null);
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

  function handleRunTest() {
    setRunMessage(
      "TODO: backend endpoint missing for prompt + model citation tests. Current backend only supports POST /api/v1/citation-tests/run/{content_id}.",
    );
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
        <CardContent className="grid gap-4 p-6 lg:grid-cols-[1fr_220px_auto]">
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
            <span className="text-sm text-zinc-400">Model</span>
            <select
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
              value={model}
              onChange={(event) => setModel(event.target.value)}
            >
              {models.map((modelName) => (
                <option key={modelName}>{modelName}</option>
              ))}
            </select>
          </label>

          <div className="flex items-end">
            <Button
              disabled={!activeProperty || !prompt.trim()}
              onClick={handleRunTest}
            >
              Run Test
            </Button>
          </div>

          {runMessage && (
            <div className="rounded-lg border border-amber-800 bg-amber-950/50 p-3 text-sm text-amber-200 lg:col-span-3">
              {runMessage}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-800 bg-zinc-900/70 text-xs uppercase tracking-[0.16em] text-zinc-500">
              <tr>
                <th className="px-5 py-4 font-medium">Prompt</th>
                <th className="px-5 py-4 font-medium">Time</th>
                <th className="px-5 py-4 font-medium">Model</th>
                <th className="px-5 py-4 font-medium">Mentioned</th>
                <th className="px-5 py-4 font-medium">Rank</th>
                <th className="px-5 py-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {tests.map((test) => (
                <Fragment key={test.id}>
                  <tr
                    className="cursor-pointer transition hover:bg-zinc-900/50"
                    onClick={() =>
                      setExpandedTestId((currentId) =>
                        currentId === test.id ? null : test.id,
                      )
                    }
                  >
                    <td className="px-5 py-4 font-medium text-zinc-100">
                      {test.prompt || test.query || "Untitled prompt"}
                    </td>
                    <td className="px-5 py-4 text-zinc-500">
                      {test.last_run || test.tested_at
                        ? new Date(
                            test.last_run || test.tested_at || "",
                          ).toLocaleString()
                        : "-"}
                    </td>
                    <td className="px-5 py-4 text-zinc-400">
                      {test.platform || "Unknown"}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={
                          test.mentioned
                            ? "text-emerald-300"
                            : "text-zinc-500"
                        }
                      >
                        {test.mentioned ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-zinc-300">
                      {test.confidence_score || "-"}
                    </td>
                    <td className="px-5 py-4 text-zinc-400">
                      {test.status || "unknown"}
                    </td>
                  </tr>
                  {expandedTestId === test.id && (
                    <tr>
                      <td className="bg-black px-5 py-4" colSpan={6}>
                        <p className="mb-2 text-xs uppercase tracking-[0.16em] text-zinc-500">
                          Full LLM Response
                        </p>
                        <div className="whitespace-pre-wrap rounded-lg border border-zinc-800 bg-zinc-950 p-4 text-sm leading-6 text-zinc-300">
                          {test.ai_response || "No response stored."}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>

          {tests.length === 0 && (
            <div className="border-t border-zinc-800 px-5 py-8 text-sm text-zinc-500">
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
