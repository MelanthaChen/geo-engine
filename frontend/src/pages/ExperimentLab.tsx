import { useState } from "react";

import { ExperimentConfiguration } from "@/components/ExperimentConfiguration";
import { ExperimentProgress } from "@/components/ExperimentProgress";
import { ExperimentSummary } from "@/components/ExperimentSummary";
import { QueryResultAccordion } from "@/components/QueryResultAccordion";
import { StrategyComparisonTable } from "@/components/StrategyComparisonTable";
import {
  getExperimentLabRun,
  startExperimentLab,
} from "@/api/experimentLab";
import { defaultExperimentConfiguration } from "@/data/experimentLabConfig";
import type {
  ExperimentConfigurationValues,
  ExperimentRun,
} from "@/types/experimentLab";

export function ExperimentLab() {
  const [configuration, setConfiguration] =
    useState<ExperimentConfigurationValues>(defaultExperimentConfiguration);
  const [run, setRun] = useState<ExperimentRun | null>(null);
  const isRunning = run?.status === "running" || run?.status === "queued";

  async function handleRunExperiment() {
    setRun({
      status: "running",
      currentQuery: "Queued",
      currentStrategy: configuration.strategies[0] || "original",
      completedQueries: 0,
      totalQueries: configuration.numberOfQueries,
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
          completedQueries: 0,
          totalQueries: configuration.numberOfQueries,
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

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Research Benchmark
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Experiment Lab
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Reproduce the experimental workflow from the Princeton Generative
          Engine Optimization paper using controlled strategies, query-level
          outputs, and paper-aligned evaluation metrics.
        </p>
      </div>

      <ExperimentConfiguration
        isRunning={isRunning}
        value={configuration}
        onChange={setConfiguration}
        onRunExperiment={handleRunExperiment}
      />

      {run?.status === "failed" && (
        <div className="rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-100">
          {run.errorMessage || "Experiment failed before completion."}
        </div>
      )}

      <ExperimentProgress run={run} />

      <ExperimentSummary run={run?.status === "completed" ? run : null} />

      <StrategyComparisonTable
        results={run?.status === "completed" ? run.strategyResults : []}
      />

      <QueryResultAccordion
        queryResults={run?.status === "completed" ? run.queryResults : []}
      />
    </div>
  );
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
