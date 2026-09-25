import { useEffect, useState } from "react";
import { Database, Download, FlaskConical, GitBranch, ShieldCheck } from "lucide-react";

import { Card, CardContent } from "../../@/components/ui/card";
import { EmptyState, Page, PageHeader, SectionHeader, SummaryCard, SummaryGrid } from "@/components/layout/PageLayout";
import { fetchTeacherPipelineStatus, teacherDatasetExportUrl, type TeacherPipelineStatus } from "@/api/teacherPipeline";
import { groupTeacherSamples, type TeacherExperimentGroup } from "@/lib/teacherExperimentGroups";

export function TeacherPipelinePage() {
  const [status, setStatus] = useState<TeacherPipelineStatus | null>(null);
  const [error, setError] = useState("");
  const experimentGroups = groupTeacherSamples(status?.recent_samples || []);

  useEffect(() => {
    let mounted = true;
    let timer: number | undefined;
    const refresh = () => fetchTeacherPipelineStatus()
      .then((result) => {
        if (!mounted) return;
        setStatus(result);
        setError("");
        timer = window.setTimeout(refresh, 3000);
      })
      .catch((reason) => {
        console.error(reason);
        if (mounted) {
          setError("Teacher Pipeline status could not be loaded.");
          timer = window.setTimeout(refresh, 3000);
        }
      });
    void refresh();
    return () => { mounted = false; if (timer) window.clearTimeout(timer); };
  }, []);

  return <Page>
    <PageHeader
      eyebrow="Research transparency"
      title="Teacher Pipeline"
      description="Trace how completed Princeton GEO experiments become immutable supervised research samples. This page exposes dataset provenance only; model training and prediction are disabled."
      actions={status?.dataset_version ? <div className="flex gap-2"><a href={teacherDatasetExportUrl("jsonl")} className="inline-flex h-10 items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-4 text-sm font-medium text-zinc-200 hover:bg-zinc-800"><Download className="h-4 w-4" />Export JSONL</a><a href={teacherDatasetExportUrl("csv")} className="inline-flex h-10 items-center gap-2 rounded-lg bg-zinc-100 px-4 text-sm font-medium text-zinc-950 hover:bg-white"><Download className="h-4 w-4" />Export CSV</a></div> : undefined}
    />

    {error && <div className="rounded-lg border border-red-900 bg-red-950/30 px-5 py-4 text-sm text-red-300">{error}</div>}

    <SummaryGrid>
      <SummaryCard label="Pipeline Status" value={status?.status === "ready" ? "Ready" : "Awaiting samples"} detail="Collection only; training disabled" />
      <SummaryCard label="Training Samples" value={String(status?.generated_samples ?? 0)} detail={`${status?.processed_experiments ?? 0} experiments represented`} />
      <SummaryCard label="Dataset Version" value={status?.dataset_version || "Not created"} detail="Immutable snapshot identifier" />
      <SummaryCard label="Last Experiment" value={status?.last_experiment_processed ? `#${status.last_experiment_processed}` : "Not processed"} detail={status?.last_processed_at ? new Date(status.last_processed_at).toLocaleString() : "No completed sample yet"} />
    </SummaryGrid>

    <section className="grid gap-4 lg:grid-cols-3">
      <InfoCard icon={FlaskConical} title="Teacher model" value={status?.teacher_models.join(", ") || "No teacher recorded"} detail="Exact model identifiers captured from experiment runs." />
      <InfoCard icon={Database} title="Dataset manifest" value={status?.dataset ? `${status.dataset.sample_count} samples` : "No manifest"} detail={status?.dataset ? `${status.dataset.experiment_count} experiments • ${status.dataset.metric_version}` : "Created when the first valid pair is processed."} />
      <InfoCard icon={GitBranch} title="Pending experiments" value={String(status?.completed_experiments_pending ?? 0)} detail="Completed experiments without generated samples in this property scope." />
    </section>

    <section>
      <SectionHeader title="Recent Teacher Experiments" description="Controlled baseline-versus-treatment results used to generate Teacher training samples." />
      {experimentGroups.length ? <div className="space-y-4">{experimentGroups.map((group) => <ExperimentResultCard key={group.key} group={group} />)}</div> : <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-6"><EmptyState>No valid teacher samples have been generated yet. The worker will process completed experiments that have matching audit and baseline evidence.</EmptyState></CardContent></Card>}
    </section>

    <div className="rounded-xl border border-blue-950 bg-blue-950/20 px-5 py-4 text-sm leading-6 text-blue-200/80">The Teacher Pipeline records research evidence only. It does not train Qwen, Llama, or any other model, and it does not perform inference or impact prediction.</div>
  </Page>;
}

function ExperimentResultCard({ group }: { group: TeacherExperimentGroup }) {
  const baselineVisibility = group.originalMetrics.visibility_score;
  const optimizedVisibility = group.optimizedMetrics.visibility_score;
  const visibilityDelta = group.deltaMetrics.visibility_score;

  return <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-0">
    <div className="p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-400" /><p className="text-lg font-semibold text-zinc-100">{formatStrategy(group.strategy)}</p></div>
          <p className="mt-1 text-sm text-zinc-500">Experiment #{group.experimentId} • Audit #{group.auditId}</p>
          <p className="mt-2 text-sm font-medium text-blue-300">{group.samples.length} training {group.samples.length === 1 ? "sample" : "samples"} generated</p>
        </div>
        <dl className="grid gap-x-6 gap-y-2 text-sm sm:text-right">
          <div><dt className="text-xs text-zinc-500">Teacher</dt><dd className="mt-1 text-zinc-300">{group.teacherModel}</dd></div>
          <div><dt className="text-xs text-zinc-500">Date</dt><dd className="mt-1 text-zinc-300">{new Date(group.createdAt).toLocaleDateString()}</dd></div>
        </dl>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <MetricCard label="Baseline Visibility" value={formatMetric(baselineVisibility)} />
        <MetricCard label="Optimized Visibility" value={formatMetric(optimizedVisibility)} />
        <MetricCard label="Δ Visibility" value={formatMetric(visibilityDelta, true)} highlight />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <MetricCard label="Δ PAWC" value={formatMetric(group.deltaMetrics.pawc, true)} />
        <MetricCard label="Δ Citations" value={formatMetric(group.deltaMetrics.citation_count, true)} />
        <MetricCard label="Δ Word Contribution" value={formatMetric(group.deltaMetrics.word_count, true)} />
      </div>
    </div>

    <details className="group border-t border-zinc-800">
      <summary className="cursor-pointer list-none px-6 py-4 text-sm font-medium text-zinc-300 hover:bg-zinc-900/60">View {group.samples.length} {group.samples.length === 1 ? "sample" : "samples"}</summary>
      <div className="divide-y divide-zinc-800 border-t border-zinc-800">{group.samples.map((sample, index) => <div key={sample.sample_id} className="grid gap-3 px-6 py-4 text-sm md:grid-cols-[auto_minmax(0,1.3fr)_repeat(3,minmax(0,0.7fr))_minmax(0,1fr)] md:items-center">
        <p className="font-medium text-zinc-200">#{index + 1}</p>
        <div className="min-w-0"><p className="text-xs text-zinc-500">Sample UUID</p><p className="truncate font-mono text-xs text-zinc-400" title={sample.sample_id}>{sample.sample_id}</p></div>
        <SampleMetric label="Baseline" value={sample.original_metrics.visibility_score} />
        <SampleMetric label="Optimized" value={sample.optimized_metrics.visibility_score} />
        <SampleMetric label="Delta" value={sample.delta_metrics.visibility_score} signed />
        <div className="min-w-0"><p className="text-xs text-zinc-500">Provenance hash</p><p className="truncate font-mono text-xs text-zinc-400" title={sample.provenance_hash}>{sample.provenance_hash}</p></div>
      </div>)}</div>
    </details>
  </CardContent></Card>;
}

function MetricCard({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return <div className={`rounded-lg border p-4 ${highlight ? "border-emerald-900 bg-emerald-950/30" : "border-zinc-800 bg-black"}`}><p className="text-xs text-zinc-500">{label}</p><p className={`mt-2 text-xl font-semibold ${highlight ? "text-emerald-300" : "text-zinc-100"}`}>{value}</p></div>;
}

function SampleMetric({ label, value, signed = false }: { label: string; value?: number | null; signed?: boolean }) {
  return <div><p className="text-xs text-zinc-500">{label}</p><p className="mt-1 font-medium text-zinc-300">{formatMetric(value, signed)}</p></div>;
}

function formatMetric(value?: number | null, signed = false) {
  if (typeof value !== "number") return "Not recorded";
  const formatted = Number.isInteger(value) ? value.toFixed(0) : value.toFixed(3);
  return signed && value > 0 ? `+${formatted}` : formatted;
}

function formatStrategy(strategy: string) {
  return strategy.split("_").map((word) => word[0]?.toUpperCase() + word.slice(1)).join(" ");
}

function InfoCard({ icon: Icon, title, value, detail }: { icon: typeof Database; title: string; value: string; detail: string }) {
  return <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-5"><div className="flex items-center gap-3"><div className="rounded-lg border border-zinc-800 bg-black p-2 text-zinc-400"><Icon className="h-4 w-4" /></div><p className="text-sm font-medium text-zinc-200">{title}</p></div><p className="mt-4 text-lg font-semibold text-zinc-50">{value}</p><p className="mt-1 text-xs leading-5 text-zinc-500">{detail}</p></CardContent></Card>;
}
