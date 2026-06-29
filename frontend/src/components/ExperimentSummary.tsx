import { Card, CardContent } from "../../@/components/ui/card";

import type { ExperimentRun } from "@/types/experimentLab";

type ExperimentSummaryProps = {
  run: ExperimentRun | null;
};

export function ExperimentSummary({ run }: ExperimentSummaryProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <h2 className="text-lg font-semibold text-zinc-50">
          Experiment Result
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Overall performance for the completed reproduction run.
        </p>

        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <SummaryMetric
            label="Visibility Score"
            value={run ? run.overall.visibilityScore.toFixed(1) : "No result"}
          />
          <SummaryMetric
            label="Citation Count"
            value={run ? String(run.overall.citationCount) : "No result"}
          />
          <SummaryMetric
            label="PAWC"
            value={run ? run.overall.pawc.toFixed(2) : "No result"}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-5">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-zinc-50">{value}</p>
    </div>
  );
}
