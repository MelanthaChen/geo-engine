import { useEffect, useMemo, useState } from "react";
import { Download, FileText, Play } from "lucide-react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";
import { Input } from "../../@/components/ui/input";
import { Label } from "../../@/components/ui/label";
import {
  getOfficialReplication,
  listOfficialReplications,
  officialReplicationArtifactUrl,
  startOfficialReplication,
} from "@/api/experimentLab";
import type { OfficialReplicationRun } from "@/types/experimentLab";

type Stage = "stage1" | "stage2" | "stage3" | "full";

export function PrincetonReplicationPanel() {
  const [stage, setStage] = useState<Stage>("stage1");
  const [subjective, setSubjective] = useState(false);
  const [name, setName] = useState("");
  const [runs, setRuns] = useState<OfficialReplicationRun[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selected = runs.find((run) => run.id === selectedId) || runs[0];

  useEffect(() => {
    listOfficialReplications()
      .then((items) => {
        setRuns(items);
        setSelectedId((current) => current ?? items[0]?.id ?? null);
      })
      .catch((reason) => setError(message(reason)));
  }, []);

  useEffect(() => {
    if (!selected?.id || !["queued", "running"].includes(selected.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const updated = await getOfficialReplication(selected.id!);
        setRuns((items) => [updated, ...items.filter((item) => item.id !== updated.id)]);
      } catch (reason) {
        setError(message(reason));
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [selected?.id, selected?.status]);

  async function run() {
    setError(null);
    try {
      const created = await startOfficialReplication({
        stage,
        subjective,
        experimentName: name.trim() || undefined,
      });
      setRuns((items) => [created, ...items]);
      setSelectedId(created.id ?? null);
    } catch (reason) {
      setError(message(reason));
    }
  }

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-300">
              Princeton GEO Replication
            </p>
            <h2 className="mt-2 text-lg font-semibold text-white">Run the existing official pipeline</h2>
            <p className="mt-1 text-sm text-zinc-500">
              The same runner used by the CLI; progress and outputs come from the existing database and artifact files.
            </p>
          </div>
          {runs.length > 0 && (
            <select
              aria-label="Replication run"
              className="h-10 rounded-md border border-zinc-800 bg-black px-3 text-sm text-zinc-200"
              value={selected?.id ?? ""}
              onChange={(event) => setSelectedId(Number(event.target.value))}
            >
              {runs.map((item) => (
                <option key={item.id} value={item.id}>
                  #{item.id} · {item.name} · {item.status}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[220px_1fr_auto] lg:items-end">
          <div className="space-y-2">
            <Label htmlFor="replication-stage">Stage</Label>
            <select
              id="replication-stage"
              className="h-11 w-full rounded-md border border-zinc-800 bg-black px-3 text-sm"
              value={stage}
              onChange={(event) => setStage(event.target.value as Stage)}
            >
              <option value="stage1">Stage 1 · 30 queries</option>
              <option value="stage2">Stage 2 · 100 queries</option>
              <option value="stage3">Stage 3 · 300 queries</option>
              <option value="full">Full · 997 queries</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="replication-name">Experiment name (optional)</Label>
            <Input
              id="replication-name"
              className="h-11 border-zinc-800 bg-black"
              placeholder="Official Princeton GEO Replication"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="flex items-center gap-4 pb-0.5">
            <label className="flex items-center gap-2 whitespace-nowrap text-sm text-zinc-300">
              <input
                checked={subjective}
                className="h-4 w-4 accent-sky-500"
                type="checkbox"
                onChange={(event) => setSubjective(event.target.checked)}
              />
              Subjective evaluation
            </label>
            <Button disabled={selected?.status === "running" || selected?.status === "queued"} onClick={run}>
              <Play className="mr-2 h-4 w-4" />Run Experiment
            </Button>
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
        {selected && <ReplicationState run={selected} />}
      </CardContent>
    </Card>
  );
}

function ReplicationState({ run }: { run: OfficialReplicationRun }) {
  const progress = Math.round((run.completedQueries / Math.max(run.totalQueries, 1)) * 100);
  const figures = useMemo(
    () => run.replication.artifacts.filter((artifact) => artifact.kind === "figure" && artifact.path.endsWith(".png")),
    [run.replication.artifacts],
  );
  const primaryFigure = figures.find((artifact) => artifact.name === "Figure02_Paper_vs_Stage1.png")
    || figures.find((artifact) => artifact.name === "paper_objective_metrics.png")
    || figures[0];

  return (
    <div className="mt-6 border-t border-zinc-800 pt-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Datum label="Status" value={run.status} />
        <Datum label="Current query" value={run.currentQuery || "Not started"} />
        <Datum label="Current strategy" value={run.currentStrategy || "Not started"} />
        <Datum label="Completed queries" value={`${run.completedQueries} / ${run.totalQueries}`} />
        <Datum label="Elapsed" value={duration(run.replication.runtimeSeconds)} />
        <Datum label="Remaining" value={run.estimatedRemainingTime || "Not recorded"} />
        <Datum label="Answers" value={String(run.runCount ?? 0)} />
        <Datum label="API cost" value={run.replication.apiCost == null ? "Not recorded" : `$${run.replication.apiCost.toFixed(2)}`} />
      </div>
      <div className="mt-5 h-2 overflow-hidden rounded bg-zinc-800">
        <div className="h-full bg-sky-500" style={{ width: `${progress}%` }} />
      </div>

      {run.status === "completed" && (
        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div>
            <div className="grid gap-4 sm:grid-cols-4">
              <Datum label="Trend similarity" value={percent(run.replication.trendSimilarity)} />
              <Datum label="Claims passed" value={run.replication.claimsPassed == null ? "Not recorded" : `${run.replication.claimsPassed} / ${run.replication.claimsTested}`} />
              <Datum label="Stage decision" value={run.replication.stageDecision || "Not recorded"} />
              <Datum label="Strategies" value={String(run.replication.strategyCount)} />
            </div>
            {primaryFigure && run.id && (
              <img
                alt="Existing Princeton replication output"
                className="mt-5 max-h-[420px] w-full border border-zinc-800 bg-white object-contain"
                src={officialReplicationArtifactUrl(run.id, primaryFigure.path)}
              />
            )}
          </div>
          <div>
            <p className="mb-3 text-sm font-semibold">Existing outputs</p>
            <div className="max-h-[420px] space-y-2 overflow-auto">
              {run.replication.artifacts.map((artifact) => (
                <a
                  className="flex items-center justify-between rounded border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-300 hover:border-zinc-600"
                  href={officialReplicationArtifactUrl(run.id!, artifact.path)}
                  key={artifact.path}
                  target="_blank"
                  rel="noreferrer"
                >
                  <span className="min-w-0 truncate">
                    {artifact.kind === "report" ? <FileText className="mr-2 inline h-4 w-4" /> : <Download className="mr-2 inline h-4 w-4" />}
                    {artifact.name}
                  </span>
                  <span className="ml-2 text-[10px] uppercase text-zinc-600">{artifact.kind}</span>
                </a>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Datum({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs text-zinc-500">{label}</p><p className="mt-1 truncate text-sm font-medium text-zinc-100" title={value}>{value}</p></div>;
}

function duration(seconds: number | null) {
  if (seconds == null) return "Not recorded";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function percent(value: number | null) {
  return value == null ? "Not recorded" : `${(value * 100).toFixed(1)}%`;
}

function message(reason: unknown) {
  return reason instanceof Error ? reason.message : "Unable to load Princeton replication data.";
}
