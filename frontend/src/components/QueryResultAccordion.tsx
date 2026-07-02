import { Card, CardContent } from "../../@/components/ui/card";

import { strategyOptions } from "@/data/experimentLabConfig";
import type {
  QueryExperimentResult,
  StrategyId,
} from "@/types/experimentLab";

type QueryResultAccordionProps = {
  queryResults: QueryExperimentResult[];
};

export function QueryResultAccordion({
  queryResults,
}: QueryResultAccordionProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <h2 className="text-lg font-semibold text-zinc-50">Query Results</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Per-query outputs for the original response and each paper strategy.
        </p>

        <div className="mt-5 space-y-3">
          {queryResults.map((queryResult) => (
            <details
              key={queryResult.id}
              className="group rounded-lg border border-zinc-800 bg-black"
            >
              <summary className="cursor-pointer list-none px-4 py-3">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-zinc-100">
                      {queryResult.query}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      Winner strategy:{" "}
                      <span className="text-blue-300">
                        {formatStrategy(queryResult.winnerStrategy)}
                      </span>
                    </p>
                  </div>
                  <span className="text-xs text-zinc-500 group-open:hidden">
                    Expand
                  </span>
                  <span className="hidden text-xs text-zinc-500 group-open:inline">
                    Collapse
                  </span>
                </div>
              </summary>

              <div className="border-t border-zinc-800 px-4 py-4">
                <div className="grid gap-3 lg:grid-cols-2">
                  {strategyOptions.map((strategy) => (
                    <ResponseBlock
                      key={strategy.id}
                      label={`${strategy.tableLabel} response`}
                      value={queryResult.responses[strategy.id]}
                    />
                  ))}
                </div>

                <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950 p-4">
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

          {queryResults.length === 0 && (
            <p className="rounded-lg border border-zinc-800 bg-black p-4 text-sm text-zinc-500">
              Run an experiment to inspect per-query outputs.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ResponseBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
        {label}
      </p>
      <p className="mt-2 text-sm leading-6 text-zinc-300">{value}</p>
    </div>
  );
}

function formatStrategy(strategy: StrategyId) {
  return (
    strategyOptions.find((option) => option.id === strategy)?.tableLabel ||
    strategy
  );
}
