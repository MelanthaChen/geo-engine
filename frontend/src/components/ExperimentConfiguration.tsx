import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";
import { Input } from "../../@/components/ui/input";
import { Label } from "../../@/components/ui/label";
import type { ReactNode } from "react";

import {
  evaluationMetricOptions,
  strategyOptions,
} from "@/data/experimentLabConfig";
import type {
  EvaluationMetricId,
  ExperimentConfigurationValues,
  StrategyId,
} from "@/types/experimentLab";

type ExperimentConfigurationProps = {
  value: ExperimentConfigurationValues;
  onChange: (value: ExperimentConfigurationValues) => void;
  onRunExperiment: () => void;
  isRunning?: boolean;
};

export function ExperimentConfiguration({
  isRunning = false,
  onChange,
  onRunExperiment,
  value,
}: ExperimentConfigurationProps) {
  function updateField<Key extends keyof ExperimentConfigurationValues>(
    key: Key,
    fieldValue: ExperimentConfigurationValues[Key],
  ) {
    onChange({
      ...value,
      [key]: fieldValue,
    });
  }

  function toggleStrategy(strategy: StrategyId) {
    const nextStrategies = value.strategies.includes(strategy)
      ? value.strategies.filter((current) => current !== strategy)
      : [...value.strategies, strategy];

    updateField("strategies", nextStrategies);
  }

  function toggleMetric(metric: EvaluationMetricId) {
    const nextMetrics = value.evaluationMetrics.includes(metric)
      ? value.evaluationMetrics.filter((current) => current !== metric)
      : [...value.evaluationMetrics, metric];

    updateField("evaluationMetrics", nextMetrics);
  }

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">
              Experiment Configuration
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              Configure the Princeton GEO paper reproduction pipeline.
            </p>
          </div>
          <div className="rounded-md border border-zinc-800 bg-black px-3 py-1.5 text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
            Paper Workflow
          </div>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="experiment-name">Experiment Name</Label>
            <Input
              id="experiment-name"
              className="h-auto border-zinc-800 bg-black p-3"
              value={value.experimentName}
              onChange={(event) =>
                updateField("experimentName", event.target.value)
              }
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="experiment-description">Description</Label>
            <Input
              id="experiment-description"
              className="h-auto border-zinc-800 bg-black p-3"
              placeholder="Optional"
              value={value.description}
              onChange={(event) =>
                updateField("description", event.target.value)
              }
            />
          </div>

          <SelectField
            id="experiment-llm"
            label="LLM"
            value={value.llm}
            onChange={() => updateField("llm", "gpt-5.5")}
          >
            <option value="gpt-5.5">GPT-5.5</option>
          </SelectField>

          <SelectField
            id="experiment-dataset"
            label="Dataset"
            value={value.dataset}
            onChange={() => updateField("dataset", "custom")}
          >
            <option value="custom">Custom Dataset</option>
          </SelectField>

          <div className="space-y-2">
            <Label htmlFor="number-of-queries">Number of Queries</Label>
            <Input
              id="number-of-queries"
              className="h-auto border-zinc-800 bg-black p-3"
              min={1}
              type="number"
              value={value.numberOfQueries}
              onChange={(event) =>
                updateField("numberOfQueries", Number(event.target.value))
              }
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="random-seed">Random Seed</Label>
            <Input
              id="random-seed"
              className="h-auto border-zinc-800 bg-black p-3"
              type="number"
              value={value.randomSeed}
              onChange={(event) =>
                updateField("randomSeed", Number(event.target.value))
              }
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="temperature">Temperature</Label>
            <Input
              id="temperature"
              className="h-auto border-zinc-800 bg-black p-3"
              max={2}
              min={0}
              step={0.1}
              type="number"
              value={value.temperature}
              onChange={(event) =>
                updateField("temperature", Number(event.target.value))
              }
            />
          </div>
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          <Checklist
            label="Strategies"
            items={strategyOptions.map((strategy) => ({
              id: strategy.id,
              label: strategy.label,
              checked: value.strategies.includes(strategy.id),
              onChange: () => toggleStrategy(strategy.id),
            }))}
          />

          <Checklist
            label="Evaluation Metrics"
            items={evaluationMetricOptions.map((metric) => ({
              id: metric.id,
              label: metric.label,
              checked: value.evaluationMetrics.includes(metric.id),
              onChange: () => toggleMetric(metric.id),
            }))}
          />
        </div>

        <div className="mt-6 flex justify-end">
          <Button
            disabled={
              isRunning ||
              value.strategies.length === 0 ||
              value.evaluationMetrics.length === 0
            }
            onClick={onRunExperiment}
          >
            {isRunning ? "Running..." : "Run Experiment"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SelectField({
  children,
  id,
  label,
  onChange,
  value,
}: {
  children: ReactNode;
  id: string;
  label: string;
  onChange: () => void;
  value: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <select
        id={id}
        className="h-auto w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm text-zinc-100 outline-none transition focus:border-blue-500"
        value={value}
        onChange={onChange}
      >
        {children}
      </select>
    </div>
  );
}

function Checklist({
  items,
  label,
}: {
  label: string;
  items: Array<{
    id: string;
    label: string;
    checked: boolean;
    onChange: () => void;
  }>;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <p className="text-sm font-medium text-zinc-100">{label}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <label
            key={item.id}
            className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 text-sm text-zinc-300 transition hover:bg-zinc-900/70"
          >
            <input
              checked={item.checked}
              className="h-4 w-4 accent-blue-500"
              type="checkbox"
              onChange={item.onChange}
            />
            {item.label}
          </label>
        ))}
      </div>
    </div>
  );
}
