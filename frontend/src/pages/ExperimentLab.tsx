import { useState } from "react";

import { ExperimentConfiguration } from "@/components/ExperimentConfiguration";
import { ExperimentProgress } from "@/components/ExperimentProgress";
import { ExperimentSummary } from "@/components/ExperimentSummary";
import { QueryResultAccordion } from "@/components/QueryResultAccordion";
import { StrategyComparisonTable } from "@/components/StrategyComparisonTable";
import {
  createMockExperimentRun,
  defaultExperimentConfiguration,
} from "@/data/experimentLabMock";
import type {
  ExperimentConfigurationValues,
  ExperimentRun,
} from "@/types/experimentLab";

export function ExperimentLab() {
  const [configuration, setConfiguration] =
    useState<ExperimentConfigurationValues>(defaultExperimentConfiguration);
  const [run, setRun] = useState<ExperimentRun | null>(null);

  function handleRunExperiment() {
    const mockRun = createMockExperimentRun(configuration);

    setRun({
      ...mockRun,
      status: "running",
      completedQueries: Math.max(1, Math.floor(configuration.numberOfQueries / 3)),
      estimatedRemainingTime: "4 min",
    });

    window.setTimeout(() => {
      setRun(mockRun);
    }, 900);
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
        value={configuration}
        onChange={setConfiguration}
        onRunExperiment={handleRunExperiment}
      />

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
