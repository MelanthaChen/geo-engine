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
  const [isStarting, setIsStarting] = useState(false);
  const selected = runs.find((run) => run.id === selectedId) || runs[0];
  const activeRun = runs.find((run) => ["queued", "running"].includes(run.status));

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
    setIsStarting(true);
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
    } finally {
      setIsStarting(false);
    }
  }

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-300">
            Princeton GEO Replication
          </p>
          <h2 className="mt-2 text-lg font-semibold text-white">Run the existing official pipeline</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">
            Configure a staged run, monitor its stored progress, and open the artifacts produced by the existing runner.
          </p>
        </div>

        <div className="mt-6 rounded-lg border border-zinc-800 bg-black/40 p-4">
          <p className="mb-4 text-xs font-medium uppercase tracking-wider text-zinc-500">New experiment</p>
          <div className="grid gap-4 lg:grid-cols-[220px_minmax(260px,1fr)_auto] lg:items-end">
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
          <div className="flex flex-wrap items-center gap-4 pb-0.5 lg:justify-end">
            <label className="flex items-center gap-2 whitespace-nowrap text-sm text-zinc-300">
              <input
                checked={subjective}
                className="h-4 w-4 accent-sky-500"
                type="checkbox"
                onChange={(event) => setSubjective(event.target.checked)}
              />
              Subjective evaluation
            </label>
            <Button disabled={Boolean(activeRun) || isStarting} onClick={run}>
              <Play className="mr-2 h-4 w-4" />{isStarting ? "Starting…" : "Run Experiment"}
            </Button>
          </div>
          </div>
          {activeRun && (
            <p className="mt-3 text-xs text-zinc-500">
              A replication is already {activeRun.status}. Open it below to monitor progress.
            </p>
          )}
        </div>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
        {selected && <ReplicationState run={selected} />}
        {runs.length > 0 && (
          <ReplicationHistory
            runs={runs}
            selectedId={selected?.id ?? null}
            onOpen={setSelectedId}
          />
        )}
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
  const featuredFigures = [
    "Figure02_Paper_vs_Stage1.png",
    "Figure03_Strategy_Ranking.png",
    "Figure04_Claim_Summary.png",
    "Figure08_Trend_Similarity.png",
  ]
    .map((name) => figures.find((artifact) => artifact.name === name))
    .filter((artifact) => artifact !== undefined);
  if (featuredFigures.length === 0 && figures[0]) featuredFigures.push(figures[0]);

  return (
    <div className="mt-6 border-t border-zinc-800 pt-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Selected experiment</p>
          <h3 className="mt-1 truncate text-base font-semibold text-white">{run.name}</h3>
        </div>
        <span className={statusClass(run.status)}>{run.status}</span>
      </div>

      <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-4">
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
        <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div>
            <h4 className="text-sm font-semibold text-white">Scientific summary</h4>
            <div className="mt-4 grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-4">
              <Datum label="Trend similarity" value={percent(run.replication.trendSimilarity)} />
              <Datum label="Claims passed" value={recorded(run.replication.claimsPassed)} />
              <Datum label="Claims failed" value={recorded(run.replication.claimsFailed)} />
              <Datum label="Stage decision" value={run.replication.stageDecision || "Not recorded"} />
              <Datum label="Strategies" value={String(run.replication.strategyCount)} />
              <Datum label="Method fidelity" value={percent(run.replication.methodFidelity)} />
              <Datum label="Implementation fidelity" value={percent(run.replication.implementationFidelity)} />
            </div>
            <ExistingIndicators run={run} />
            {featuredFigures.length > 0 && run.id && (
              <div className="mt-7">
                <h4 className="mb-3 text-sm font-semibold text-white">Generated figures</h4>
                <div className="grid gap-4 2xl:grid-cols-2">
                {featuredFigures.map((figure) => (
                  <a href={officialReplicationArtifactUrl(run.id!, figure.path)} key={figure.path} target="_blank" rel="noreferrer">
                    <img
                      alt={figure.name}
                      className="max-h-[360px] w-full border border-zinc-800 bg-white object-contain"
                      src={officialReplicationArtifactUrl(run.id!, figure.path)}
                    />
                  </a>
                ))}
                </div>
              </div>
            )}
          </div>
          <div>
            <p className="mb-3 text-sm font-semibold text-white">Existing outputs</p>
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

function ExistingIndicators({ run }: { run: OfficialReplicationRun }) {
  const passed = run.replication.claimsPassed;
  const failed = run.replication.claimsFailed;
  const total = (passed ?? 0) + (failed ?? 0);
  return (
    <div className="mt-5 grid gap-4 sm:grid-cols-2">
      <div className="border border-zinc-800 bg-black p-4">
        <div className="flex justify-between text-xs text-zinc-500"><span>Trend similarity</span><span>{percent(run.replication.trendSimilarity)}</span></div>
        <div className="mt-3 h-2 bg-zinc-800"><div className="h-full bg-sky-500" style={{ width: `${Math.max(0, Math.min(100, (run.replication.trendSimilarity ?? 0) * 100))}%` }} /></div>
      </div>
      <div className="border border-zinc-800 bg-black p-4">
        <div className="flex justify-between text-xs text-zinc-500"><span>Testable claims</span><span>{total || "Not recorded"}</span></div>
        <div className="mt-3 flex h-2 bg-zinc-800">
          {total > 0 && <><div className="h-full bg-emerald-500" style={{ width: `${((passed ?? 0) / total) * 100}%` }} /><div className="h-full bg-red-500" style={{ width: `${((failed ?? 0) / total) * 100}%` }} /></>}
        </div>
        {total > 0 && <p className="mt-2 text-xs text-zinc-500"><span className="text-emerald-400">PASS {passed}</span> · <span className="text-red-400">FAIL {failed}</span></p>}
      </div>
    </div>
  );
}

function ReplicationHistory({ runs, selectedId, onOpen }: { runs: OfficialReplicationRun[]; selectedId: number | null; onOpen: (id: number) => void }) {
  return (
    <div className="mt-8 border-t border-zinc-800 pt-6">
      <h3 className="text-sm font-semibold">Experiment history</h3>
      <div className="mt-3 overflow-x-auto rounded border border-zinc-800">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="bg-black text-xs text-zinc-500"><tr><th className="p-3">Experiment</th><th className="p-3">Stage</th><th className="p-3">Created</th><th className="p-3">Status</th><th className="p-3">Runtime</th><th className="p-3">Trend</th><th className="p-3">Decision</th><th className="p-3" /></tr></thead>
          <tbody className="divide-y divide-zinc-800">
            {runs.map((item) => <tr className={item.id === selectedId ? "bg-zinc-900" : "bg-zinc-950"} key={item.id}><td className="max-w-[260px] truncate p-3">{item.name}</td><td className="p-3 uppercase">{item.replication.stage}</td><td className="p-3 text-zinc-500">{date(item.createdAt)}</td><td className="p-3 capitalize">{item.status}</td><td className="p-3">{duration(item.replication.runtimeSeconds)}</td><td className="p-3">{percent(item.replication.trendSimilarity)}</td><td className="p-3">{item.replication.stageDecision || "Not recorded"}</td><td className="p-3 text-right"><button className="text-sky-300 hover:underline" onClick={() => item.id && onOpen(item.id)}>Open Result</button></td></tr>)}
          </tbody>
        </table>
      </div>
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

function recorded(value: number | null) {
  return value == null ? "Not recorded" : String(value);
}

function date(value?: string | null) {
  if (!value) return "Not recorded";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Not recorded" : parsed.toLocaleString();
}

function statusClass(status: OfficialReplicationRun["status"]) {
  const tone = status === "completed"
    ? "border-emerald-800 bg-emerald-950/40 text-emerald-300"
    : status === "failed"
      ? "border-red-800 bg-red-950/40 text-red-300"
      : "border-sky-800 bg-sky-950/40 text-sky-300";
  return `rounded-full border px-3 py-1 text-xs font-medium capitalize ${tone}`;
}

function message(reason: unknown) {
  return reason instanceof Error ? reason.message : "Unable to load Princeton replication data.";
}
