import { Badge } from "../../@/components/ui/badge";
import { Card, CardContent } from "../../@/components/ui/card";

import { strategyOptions } from "@/data/experimentLabConfig";
import type { ExperimentRun, ExperimentStatus } from "@/types/experimentLab";

type ExperimentProgressProps = {
  run: ExperimentRun | null;
};

export function ExperimentProgress({ run }: ExperimentProgressProps) {
  const progress = run
    ? Math.round((run.completedQueries / run.totalQueries) * 100)
    : 0;

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-zinc-50">
              Running Status
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              Execution state for the configured paper reproduction run.
            </p>
          </div>
          <StatusBadge status={run?.status || "queued"} />
        </div>

        <div className="mt-6">
          <div className="h-2 overflow-hidden rounded-full bg-zinc-900">
            <div
              className="h-full rounded-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-xs text-zinc-500">
            <span>{progress}% complete</span>
            <span>
              {run ? `${run.completedQueries}/${run.totalQueries}` : "0/0"}{" "}
              queries
            </span>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatusFact
            label="Current query"
            value={run?.currentQuery || "Not started"}
          />
          <StatusFact
            label="Current strategy"
            value={formatStrategy(run?.currentStrategy)}
          />
          <StatusFact
            label="Completed queries"
            value={run ? String(run.completedQueries) : "0"}
          />
          <StatusFact
            label="Estimated remaining time"
            value={run?.estimatedRemainingTime || "Not available"}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: ExperimentStatus }) {
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  const className =
    status === "completed"
      ? "border-emerald-700 bg-emerald-950 text-emerald-100"
      : status === "failed"
        ? "border-red-700 bg-red-950 text-red-100"
        : status === "running"
          ? "border-blue-700 bg-blue-950 text-blue-200"
          : "border-zinc-700 bg-zinc-900 text-zinc-300";

  return <Badge className={className}>{label}</Badge>;
}

function StatusFact({ label, value }: { label: string; value: string }) {
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

function formatStrategy(strategyId?: string) {
  if (!strategyId) {
    return "Not started";
  }

  return (
    strategyOptions.find((strategy) => strategy.id === strategyId)?.label ||
    strategyId
  );
}
