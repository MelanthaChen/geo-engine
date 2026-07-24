import { useState } from "react";
import {
  Check,
  ChevronDown,
  Circle,
  FileText,
  Play,
  Trophy,
  Upload,
} from "lucide-react";

import { Badge } from "../../@/components/ui/badge";
import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";
import { Input } from "../../@/components/ui/input";
import { Label } from "../../@/components/ui/label";
import {
  getExperimentLabRun,
  startExperimentLab,
} from "@/api/experimentLab";
import {
  defaultExperimentConfiguration,
  strategyOptions,
} from "@/data/experimentLabConfig";
import type {
  BenchmarkSource,
  ExperimentConfigurationValues,
  ExperimentRun,
  StrategyEvidence,
  StrategyId,
  StrategyResult,
  UploadedDatasetDocument,
} from "@/types/experimentLab";

export function ExperimentLab() {
  const [configuration, setConfiguration] =
    useState<ExperimentConfigurationValues>(defaultExperimentConfiguration);
  const [run, setRun] = useState<ExperimentRun | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [strategyAdvancedOpen, setStrategyAdvancedOpen] = useState(false);
  const [uploadLabel, setUploadLabel] = useState("No CSV selected");

  const isRunning = run?.status === "running" || run?.status === "queued";
  const isCompleted = run?.status === "completed";
  const isFailed = run?.status === "failed";

  async function handleRunExperiment() {
    setRun({
      status: "running",
      currentQuery: "Queued",
      currentStrategy: configuration.strategies[0] || "original",
      currentSample: 0,
      totalSamples: 5,
      completedQueries: 0,
      totalQueries: activeQueries(configuration).length || 1,
      estimatedRemainingTime: "Calculating",
      overall: {
        visibilityScore: 0,
        citationCount: 0,
        pawc: 0,
      },
      strategyResults: [],
      queryResults: [],
    });

    try {
      let result = await startExperimentLab(configuration);
      setRun(result);

      while (
        result.id &&
        (result.status === "queued" || result.status === "running")
      ) {
        await wait(2000);
        result = await getExperimentLabRun(result.id);
        setRun(result);
      }
    } catch (error) {
      setRun((currentRun) => ({
        ...(currentRun || {
          currentQuery: "",
          currentStrategy: "original",
          currentSample: 0,
          totalSamples: 5,
          completedQueries: 0,
          totalQueries: activeQueries(configuration).length || 1,
          estimatedRemainingTime: "Not available",
          overall: {
            visibilityScore: 0,
            citationCount: 0,
            pawc: 0,
          },
          strategyResults: [],
          queryResults: [],
        }),
        status: "failed",
        errorMessage:
          error instanceof Error
            ? error.message
            : "Experiment failed before completion.",
      }));
    }
  }

  function updateField<Key extends keyof ExperimentConfigurationValues>(
    key: Key,
    value: ExperimentConfigurationValues[Key],
  ) {
    setConfiguration((current) => ({
      ...current,
      [key]: value,
    }));
  }

  async function handleCsvUpload(file: File | undefined) {
    if (!file) {
      return;
    }

    const text = await file.text();
    const parsed = parseCsvBenchmark(text);
    updateField("uploadedQueries", parsed.queries);
    updateField("uploadedDocuments", parsed.documents);
    updateField("numberOfQueries", Math.max(parsed.queries.length, 1));
    setUploadLabel(
      parsed.documents.length > 0
        ? `${file.name} · ${parsed.queries.length} queries · ${parsed.documents.length} documents`
        : `${file.name} · ${parsed.queries.length} queries`,
    );
  }

  function toggleStrategy(strategy: StrategyId) {
    updateField(
      "strategies",
      configuration.strategies.includes(strategy)
        ? configuration.strategies.filter((item) => item !== strategy)
        : [...configuration.strategies, strategy],
    );
  }

  if (isRunning || isFailed) {
    return <RunningExperiment run={run} onReset={() => setRun(null)} />;
  }

  if (isCompleted && run) {
    return <ExperimentResults run={run} onReset={() => setRun(null)} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Research Benchmark"
        title="Experiment Lab"
        description="Run a faithful Princeton GEO paper reproduction experiment: one query, Google Top-5 retrieval, one randomly selected source, independent GEO strategies, five samples, and paper-style visibility evaluation."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-6">
            <StepHeader
              step="Step 1"
              title="Configure Experiment"
              description="Choose the query source. Paper defaults stay hidden unless you need them."
            />

            <div className="mt-6 space-y-6">
              <div className="space-y-2">
                <Label htmlFor="experiment-name">Experiment Name</Label>
                <Input
                  id="experiment-name"
                  className="h-auto border-zinc-800 bg-black p-3"
                  value={configuration.experimentName}
                  onChange={(event) =>
                    updateField("experimentName", event.target.value)
                  }
                />
              </div>

              <BenchmarkSelector
                value={configuration.benchmarkSource}
                onChange={(source) => updateField("benchmarkSource", source)}
              />

              {configuration.benchmarkSource === "manual" && (
                <div className="space-y-2 rounded-lg border border-zinc-800 bg-black p-4">
                  <Label htmlFor="manual-query">Query</Label>
                  <Input
                    id="manual-query"
                    className="h-auto border-zinc-800 bg-zinc-950 p-3"
                    placeholder="Best AI Resume Builder"
                    value={configuration.manualQuery}
                    onChange={(event) =>
                      updateField("manualQuery", event.target.value)
                    }
                  />
                </div>
              )}

              {configuration.benchmarkSource === "csv" && (
                <label className="flex cursor-pointer items-center gap-4 rounded-lg border border-dashed border-zinc-700 bg-black p-5 transition hover:border-blue-500 hover:bg-zinc-950">
                  <Upload className="h-5 w-5 text-blue-300" />
                  <div>
                    <p className="text-sm font-medium text-zinc-100">
                      Upload CSV
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {uploadLabel}
                    </p>
                  </div>
                  <input
                    accept=".csv,text/csv,text/plain"
                    className="hidden"
                    type="file"
                    onChange={(event) =>
                      void handleCsvUpload(event.target.files?.[0])
                    }
                  />
                </label>
              )}

              {configuration.benchmarkSource === "geo_bench" && (
                <div className="rounded-lg border border-zinc-800 bg-black p-4 text-sm text-zinc-500">
                  Official GEO-bench test split. The backend loads benchmark
                  queries and the five cleaned Google sources for each query.
                </div>
              )}

              <CollapsiblePanel
                open={advancedOpen}
                title="Advanced Settings"
                onToggle={() => setAdvancedOpen((value) => !value)}
              >
                <div className="grid gap-4 md:grid-cols-3">
                  <ReadOnlySetting label="Model" value="GPT-3.5 Turbo" />
                  <div className="space-y-2">
                    <Label htmlFor="temperature">Temperature</Label>
                    <Input
                      id="temperature"
                      className="h-auto border-zinc-800 bg-black p-3"
                      max={2}
                      min={0}
                      step={0.1}
                      type="number"
                      value={configuration.temperature}
                      onChange={(event) =>
                        updateField("temperature", Number(event.target.value))
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="random-seed">Random Seed</Label>
                    <Input
                      id="random-seed"
                      className="h-auto border-zinc-800 bg-black p-3"
                      type="number"
                      value={configuration.randomSeed}
                      onChange={(event) =>
                        updateField("randomSeed", Number(event.target.value))
                      }
                    />
                  </div>
                </div>
              </CollapsiblePanel>

              <div className="rounded-lg border border-zinc-800 bg-black p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-zinc-100">
                      Strategies
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      All Princeton GEO strategies are selected by default.
                    </p>
                  </div>
                  <button
                    className="text-xs font-medium text-blue-300 hover:text-blue-200"
                    type="button"
                    onClick={() =>
                      setStrategyAdvancedOpen((value) => !value)
                    }
                  >
                    Advanced
                  </button>
                </div>

                <div className="mt-4 grid gap-2 md:grid-cols-2">
                  {strategyOptions.map((strategy) => (
                    <label
                      key={strategy.id}
                      className="flex items-center gap-2 text-sm text-zinc-300"
                    >
                      {strategyAdvancedOpen ? (
                        <input
                          checked={configuration.strategies.includes(
                            strategy.id,
                          )}
                          className="h-4 w-4 accent-blue-500"
                          type="checkbox"
                          onChange={() => toggleStrategy(strategy.id)}
                        />
                      ) : (
                        <Check className="h-4 w-4 text-emerald-400" />
                      )}
                      {strategy.label}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <RunPanel
          disabled={!canRun(configuration)}
          queryCount={activeQueries(configuration).length}
          strategyCount={configuration.strategies.length}
          onRun={handleRunExperiment}
        />
      </div>
    </div>
  );
}

function RunningExperiment({
  onReset,
  run,
}: {
  onReset: () => void;
  run: ExperimentRun | null;
}) {
  const progress = run
    ? Math.round((run.completedQueries / Math.max(run.totalQueries, 1)) * 100)
    : 0;
  const failed = run?.status === "failed";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 3 · Running"
        title="Running Princeton GEO Reproduction"
        description="The benchmark is executing the paper workflow. Configuration is hidden until the run finishes or fails."
      />

      {failed && (
        <div className="rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-100">
          {run?.errorMessage || "Experiment failed before completion."}
          <Button className="ml-4" size="sm" onClick={onReset}>
            Back to Configure
          </Button>
        </div>
      )}

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <div className="grid gap-4 lg:grid-cols-4">
            <StatusTile label="Current Query" value={run?.currentQuery || "Queued"} />
            <StatusTile
              label="Current Stage"
              value={currentStage(run)}
            />
            <StatusTile
              label="Current Strategy"
              value={formatStrategy(run?.currentStrategy)}
            />
            <StatusTile
              label="Current Sample"
              value={`${run?.currentSample || 0} / ${run?.totalSamples || 5}`}
            />
          </div>

          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between text-xs text-zinc-500">
              <span>Overall Progress</span>
              <span>
                {run ? `${run.completedQueries}/${run.totalQueries}` : "0/0"}{" "}
                queries
              </span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-zinc-900">
              <div
                className="h-full rounded-full bg-blue-500 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-zinc-500">
              Estimated Remaining Time:{" "}
              {run?.estimatedRemainingTime || "Calculating"}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-zinc-50">
            Live Timeline
          </h2>
          <div className="mt-5 space-y-3">
            {timeline(run).map((item) => (
              <div
                key={item.label}
                className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-black px-4 py-3"
              >
                {item.state === "done" ? (
                  <Check className="h-4 w-4 text-emerald-400" />
                ) : item.state === "active" ? (
                  <Circle className="h-4 w-4 fill-blue-500 text-blue-500" />
                ) : (
                  <Circle className="h-4 w-4 text-zinc-700" />
                )}
                <span
                  className={
                    item.state === "active"
                      ? "text-sm font-medium text-blue-200"
                      : "text-sm text-zinc-400"
                  }
                >
                  {item.label}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ExperimentResults({
  onReset,
  run,
}: {
  onReset: () => void;
  run: ExperimentRun;
}) {
  const ranking = [...run.strategyResults].sort(
    (a, b) => b.visibility - a.visibility,
  );
  const winner = ranking[0];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          eyebrow="Step 4 · Completed"
          title="Experiment Results"
          description="Paper reproduction output with ranking, per-strategy details, and reproducibility evidence."
        />
        <Button variant="outline" onClick={onReset}>
          New Experiment
        </Button>
      </div>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <StepHeader
            step="Overall Summary"
            title={winner ? `${winner.label} wins` : "No winner"}
            description="Aggregate visibility metrics across generated samples."
          />
          <div className="mt-5 grid gap-4 md:grid-cols-4">
            <SummaryMetric
              label="Visibility"
              value={run.overall.visibilityScore.toFixed(4)}
            />
            <SummaryMetric
              label="Citation Count"
              value={String(run.overall.citationCount)}
            />
            <SummaryMetric label="PAWC" value={run.overall.pawc.toFixed(4)} />
            <SummaryMetric
              label="Winning Strategy"
              value={winner?.label || "None"}
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <StepHeader
            step="Strategy Ranking"
            title="Best to Worst"
            description="Ranked by paper-style visibility score."
          />
          <div className="mt-5 overflow-hidden rounded-lg border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-black text-xs uppercase tracking-[0.16em] text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Rank</th>
                  <th className="px-4 py-3 font-medium">Strategy</th>
                  <th className="px-4 py-3 font-medium">Visibility</th>
                  <th className="px-4 py-3 font-medium">PAWC</th>
                  <th className="px-4 py-3 font-medium">Citations</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {ranking.map((result, index) => (
                  <tr key={result.strategy} className="bg-zinc-950">
                    <td className="px-4 py-3 text-zinc-400">
                      {index === 0 ? (
                        <Trophy className="h-4 w-4 text-amber-300" />
                      ) : (
                        index + 1
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-zinc-100">
                      {result.label}
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {result.visibility.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {result.pawc.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 text-zinc-300">
                      {result.citationCount}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <PerStrategyDetails run={run} ranking={ranking} />
      <EvidencePanel run={run} />
    </div>
  );
}

function RunPanel({
  disabled,
  onRun,
  queryCount,
  strategyCount,
}: {
  disabled: boolean;
  onRun: () => void;
  queryCount: number;
  strategyCount: number;
}) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <StepHeader
          step="Step 2"
          title="Run Experiment"
          description={`${queryCount || 0} query · ${strategyCount} strategies · five samples per strategy`}
        />

        <Button
          className="mt-6 h-14 w-full text-sm font-semibold uppercase tracking-[0.14em]"
          disabled={disabled}
          onClick={onRun}
        >
          <Play className="mr-2 h-4 w-4" />
          Run Paper Reproduction
        </Button>

        <div className="mt-6 rounded-lg border border-zinc-800 bg-black p-4">
          <p className="text-sm font-medium text-zinc-100">
            This experiment will:
          </p>
          <ul className="mt-3 space-y-2 text-sm text-zinc-400">
            <li>• Retrieve the Top-5 Google search results</li>
            <li>• Randomly select one source</li>
            <li>• Apply every GEO strategy independently</li>
            <li>• Generate five responses per strategy</li>
            <li>• Evaluate visibility metrics</li>
            <li>• Compare all strategies</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

function PerStrategyDetails({
  ranking,
  run,
}: {
  ranking: StrategyResult[];
  run: ExperimentRun;
}) {
  const details = run.queryResults[0]?.evidence?.strategyDetails || [];

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <StepHeader
          step="Per Strategy Details"
          title="Representative Sample"
          description="Shows sample 1 for each strategy plus its stored metrics."
        />
        <div className="mt-5 space-y-3">
          {ranking.map((result) => {
            const detail = details.find(
              (item) => item.strategy === result.strategy,
            );

            return (
              <details
                key={result.strategy}
                className="rounded-lg border border-zinc-800 bg-black"
              >
                <summary className="cursor-pointer list-none px-4 py-3">
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-medium text-zinc-100">
                      {result.label}
                    </span>
                    <Badge className="border-zinc-700 bg-zinc-900 text-zinc-300">
                      visibility {result.visibility.toFixed(4)}
                    </Badge>
                  </div>
                </summary>
                <div className="space-y-4 border-t border-zinc-800 p-4">
                  <CodeBlock
                    label="Modified document"
                    value={detail?.modifiedDocument || "Not available"}
                  />
                  <CodeBlock
                    label="Generated response"
                    value={detail?.generatedAnswer || "Not available"}
                  />
                  <MetricStrip detail={detail} />
                </div>
              </details>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function EvidencePanel({ run }: { run: ExperimentRun }) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <StepHeader
          step="Evidence"
          title="Reproducibility Trace"
          description="Retrieved sources, selected source, prompts, answers, and evaluation outputs for each query."
        />

        <div className="mt-5 space-y-4">
          {run.queryResults.map((queryResult) => (
            <details
              key={queryResult.id}
              open
              className="rounded-lg border border-zinc-800 bg-black"
            >
              <summary className="cursor-pointer list-none px-4 py-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-zinc-100">
                      {queryResult.query}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      Winner: {formatStrategy(queryResult.winnerStrategy)}
                    </p>
                  </div>
                  <FileText className="h-4 w-4 text-zinc-500" />
                </div>
              </summary>

              <div className="space-y-4 border-t border-zinc-800 p-4">
                <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
                    Top-5 Retrieved URLs
                  </p>
                  <div className="mt-3 space-y-2">
                    {(queryResult.evidence?.topDocuments || []).map(
                      (document) => (
                        <div
                          key={document.rank}
                          className="flex items-start gap-3 text-sm"
                        >
                          <Badge
                            className={
                              document.isSelected
                                ? "border-blue-700 bg-blue-950 text-blue-100"
                                : "border-zinc-700 bg-zinc-900 text-zinc-300"
                            }
                          >
                            {document.rank}
                          </Badge>
                          <div className="min-w-0">
                            <p className="truncate text-zinc-200">
                              {document.title || document.url}
                            </p>
                            <p className="break-all text-xs text-zinc-500">
                              {document.url}
                            </p>
                          </div>
                        </div>
                      ),
                    )}
                  </div>
                </div>

                <CodeBlock
                  label={`Original selected document · rank ${
                    queryResult.evidence?.selectedDocumentRank || "unknown"
                  }`}
                  value={
                    queryResult.evidence?.originalDocument || "Not available"
                  }
                />

                {(queryResult.evidence?.strategyDetails || []).map(
                  (detail) => (
                    <details
                      key={`${queryResult.id}-${detail.strategy}`}
                      className="rounded-lg border border-zinc-800 bg-zinc-950"
                    >
                      <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-zinc-100">
                        {formatStrategy(detail.strategy)} evidence
                      </summary>
                      <div className="space-y-4 border-t border-zinc-800 p-4">
                        <CodeBlock
                          label="Modified document"
                          value={detail.modifiedDocument}
                        />
                        <CodeBlock
                          label="Final prompt sent to GPT"
                          value={detail.finalPrompt}
                        />
                        <CodeBlock
                          label="Generated answer"
                          value={detail.generatedAnswer}
                        />
                        <MetricStrip detail={detail} />
                      </div>
                    </details>
                  ),
                )}

                <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
                    Evaluation result
                  </p>
                  <p className="mt-2 text-sm text-zinc-300">
                    {queryResult.evaluationResult}
                  </p>
                </div>
              </div>
            </details>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function BenchmarkSelector({
  onChange,
  value,
}: {
  value: BenchmarkSource;
  onChange: (value: BenchmarkSource) => void;
}) {
  const options: Array<{
    id: BenchmarkSource;
    label: string;
    description: string;
  }> = [
    {
      id: "manual",
      label: "Manual Query",
      description: "Run one query through the paper pipeline.",
    },
    {
      id: "csv",
      label: "Upload CSV",
      description: "Upload query-only rows or query/rank/title/url/content documents.",
    },
    {
      id: "geo_bench",
      label: "GEO-bench (Official)",
      description: "Use the official paper test split.",
    },
  ];

  return (
    <div className="space-y-3">
      <Label>Benchmark Source</Label>
      <div className="grid gap-3 md:grid-cols-3">
        {options.map((option) => (
          <button
            key={option.id}
            className={`rounded-lg border p-4 text-left transition ${
              value === option.id
                ? "border-blue-600 bg-blue-950/30"
                : "border-zinc-800 bg-black hover:border-zinc-700"
            }`}
            type="button"
            onClick={() => onChange(option.id)}
          >
            <div className="flex items-center gap-2">
              <Circle
                className={`h-3 w-3 ${
                  value === option.id
                    ? "fill-blue-400 text-blue-400"
                    : "text-zinc-600"
                }`}
              />
              <span className="text-sm font-medium text-zinc-100">
                {option.label}
              </span>
            </div>
            <p className="mt-2 text-xs text-zinc-500">
              {option.description}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

function CollapsiblePanel({
  children,
  onToggle,
  open,
  title,
}: {
  children: React.ReactNode;
  onToggle: () => void;
  open: boolean;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        type="button"
        onClick={onToggle}
      >
        <span className="text-sm font-medium text-zinc-100">{title}</span>
        <ChevronDown
          className={`h-4 w-4 text-zinc-500 transition ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && <div className="border-t border-zinc-800 p-4">{children}</div>}
    </div>
  );
}

function PageHeader({
  description,
  eyebrow,
  title,
}: {
  description: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
        {eyebrow}
      </p>
      <h1 className="mt-2 text-3xl font-semibold text-zinc-50">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm text-zinc-500">{description}</p>
    </div>
  );
}

function StepHeader({
  description,
  step,
  title,
}: {
  description: string;
  step: string;
  title: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-blue-300">
        {step}
      </p>
      <h2 className="mt-1 text-lg font-semibold text-zinc-50">{title}</h2>
      <p className="mt-1 text-sm text-zinc-500">{description}</p>
    </div>
  );
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
        {label}
      </p>
      <p className="mt-2 line-clamp-3 text-sm font-medium text-zinc-100">
        {value}
      </p>
    </div>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-5">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="mt-3 text-xl font-semibold text-zinc-50">{value}</p>
    </div>
  );
}

function ReadOnlySetting({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-3">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-zinc-100">{value}</p>
    </div>
  );
}

function CodeBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
        {label}
      </p>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-xs leading-5 text-zinc-300">
        {value}
      </pre>
    </div>
  );
}

function MetricStrip({ detail }: { detail?: StrategyEvidence }) {
  if (!detail) {
    return null;
  }

  return (
    <div className="grid gap-3 md:grid-cols-5">
      <ReadOnlySetting
        label="Word Count"
        value={String(detail.metrics.wordCount)}
      />
      <ReadOnlySetting
        label="Position"
        value={detail.metrics.position?.toString() || "None"}
      />
      <ReadOnlySetting label="PAWC" value={detail.metrics.pawc.toFixed(4)} />
      <ReadOnlySetting
        label="Citations"
        value={String(detail.metrics.citationCount)}
      />
      <ReadOnlySetting
        label="Visibility"
        value={detail.metrics.visibilityScore.toFixed(4)}
      />
    </div>
  );
}

function activeQueries(configuration: ExperimentConfigurationValues) {
  if (configuration.benchmarkSource === "manual") {
    return configuration.manualQuery.trim() ? [configuration.manualQuery] : [];
  }

  if (configuration.benchmarkSource === "csv") {
    return configuration.uploadedQueries;
  }

  if (configuration.benchmarkSource === "geo_bench") {
    return Array.from(
      { length: Math.max(configuration.numberOfQueries, 1) },
      (_, index) => `GEO-bench query ${index + 1}`,
    );
  }

  return [];
}

function canRun(configuration: ExperimentConfigurationValues) {
  return (
    activeQueries(configuration).length > 0 &&
    configuration.strategies.length > 0
  );
}

function parseCsvBenchmark(text: string): {
  queries: string[];
  documents: UploadedDatasetDocument[];
} {
  const rows = parseCsvRows(text).filter((row) =>
    row.some((cell) => cell.trim()),
  );

  if (rows.length === 0) {
    return {
      queries: [],
      documents: [],
    };
  }

  const headers = rows[0].map(normalizeHeader);
  const queryIndex = headers.indexOf("query");
  const rankIndex = headers.indexOf("rank");
  const titleIndex = headers.indexOf("title");
  const urlIndex = headers.indexOf("url");
  const contentIndex = firstHeaderIndex(headers, [
    "content",
    "cleaned_content",
    "plain_text",
    "document",
    "body",
  ]);

  if (queryIndex >= 0 && contentIndex >= 0) {
    const rankByQuery = new Map<string, number>();
    const documents = rows
      .slice(1)
      .map((row) => {
        const query = (row[queryIndex] || "").trim();
        const content = (row[contentIndex] || "").trim();

        if (!query || !content) {
          return null;
        }

        const nextRank = (rankByQuery.get(query) || 0) + 1;
        rankByQuery.set(query, nextRank);

        return {
          query,
          rank: Number(row[rankIndex]) || nextRank,
          title: titleIndex >= 0 ? (row[titleIndex] || "").trim() : "",
          url: urlIndex >= 0 ? (row[urlIndex] || "").trim() : "",
          content,
        };
      })
      .filter((document): document is UploadedDatasetDocument => Boolean(document));

    return {
      queries: uniqueInOrder(documents.map((document) => document.query)),
      documents,
    };
  }

  const queryRows =
    queryIndex >= 0
      ? rows.slice(1).map((row) => row[queryIndex])
      : rows.map((row) => row[0]);

  return {
    queries: queryRows
      .map((query) => query?.trim())
      .filter((query): query is string => Boolean(query)),
    documents: [],
  };
}

function parseCsvRows(text: string) {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const nextChar = text[index + 1];

    if (char === '"' && inQuotes && nextChar === '"') {
      field += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && nextChar === "\n") {
        index += 1;
      }
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += char;
  }

  row.push(field);
  rows.push(row);
  return rows;
}

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function firstHeaderIndex(headers: string[], candidates: string[]) {
  return candidates.reduce((foundIndex, candidate) => {
    if (foundIndex >= 0) {
      return foundIndex;
    }

    return headers.indexOf(candidate);
  }, -1);
}

function uniqueInOrder(values: string[]) {
  return values.filter((value, index) => values.indexOf(value) === index);
}

function currentStage(run: ExperimentRun | null) {
  if (!run || run.status === "queued") {
    return "Queued";
  }

  if (!run.currentQuery || run.currentQuery === "Queued") {
    return "Retrieving Google Top-5";
  }

  if (run.currentSample > 0) {
    return "Generating responses";
  }

  return "Applying GEO strategy";
}

function timeline(run: ExperimentRun | null) {
  const activeStrategy = run?.currentStrategy;

  return [
    {
      label: "Retrieve Sources",
      state: run?.currentQuery && run.currentQuery !== "Queued" ? "done" : "active",
    },
    {
      label: "Clean Documents",
      state: run?.currentQuery && run.currentQuery !== "Queued" ? "done" : "pending",
    },
    ...strategyOptions.map((strategy) => ({
      label: strategy.label,
      state:
        strategy.id === activeStrategy
          ? "active"
          : run?.status === "completed"
            ? "done"
            : "pending",
    })),
    {
      label: "Evaluation",
      state: run?.status === "completed" ? "done" : "pending",
    },
  ];
}

function formatStrategy(strategyId?: StrategyId) {
  if (!strategyId) {
    return "Not started";
  }

  return (
    strategyOptions.find((strategy) => strategy.id === strategyId)?.label ||
    strategyId
  );
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
