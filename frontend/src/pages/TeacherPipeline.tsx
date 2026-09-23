import { useEffect, useState } from "react";
import { Database, Download, FlaskConical, GitBranch, ShieldCheck } from "lucide-react";

import { Card, CardContent } from "../../@/components/ui/card";
import { EmptyState, Page, PageHeader, SectionHeader, SummaryCard, SummaryGrid } from "@/components/layout/PageLayout";
import { fetchTeacherPipelineStatus, teacherDatasetExportUrl, type TeacherPipelineStatus } from "@/api/teacherPipeline";

export function TeacherPipelinePage() {
  const [status, setStatus] = useState<TeacherPipelineStatus | null>(null);
  const [error, setError] = useState("");

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
      <SectionHeader title="Recent Generated Samples" description="Each row is an immutable, provenance-hashed baseline/optimized pair." />
      <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-0">
        {status?.recent_samples.length ? <div className="divide-y divide-zinc-800">{status.recent_samples.map((sample) => <div key={sample.sample_id} className="grid gap-4 p-5 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-center">
          <div className="min-w-0"><div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-400" /><p className="truncate text-sm font-medium text-zinc-100">{sample.strategy}</p></div><p className="mt-1 truncate font-mono text-xs text-zinc-600">{sample.sample_id}</p></div>
          <div><p className="text-xs text-zinc-500">Teacher</p><p className="mt-1 text-sm text-zinc-300">{sample.teacher_model}</p></div>
          <div><p className="text-xs text-zinc-500">Provenance</p><p className="mt-1 truncate font-mono text-xs text-zinc-400" title={sample.provenance_hash}>{sample.provenance_hash.slice(0, 14)}…</p></div>
          <div className="text-right"><p className="text-xs text-zinc-500">Experiment #{sample.experiment_id}</p><p className="mt-1 text-xs text-zinc-600">{new Date(sample.created_at).toLocaleDateString()}</p></div>
        </div>)}</div> : <div className="p-6"><EmptyState>No valid teacher samples have been generated yet. The worker will process completed experiments that have matching audit and baseline evidence.</EmptyState></div>}
      </CardContent></Card>
    </section>

    <div className="rounded-xl border border-blue-950 bg-blue-950/20 px-5 py-4 text-sm leading-6 text-blue-200/80">The Teacher Pipeline records research evidence only. It does not train Qwen, Llama, or any other model, and it does not perform inference or impact prediction.</div>
  </Page>;
}

function InfoCard({ icon: Icon, title, value, detail }: { icon: typeof Database; title: string; value: string; detail: string }) {
  return <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-5"><div className="flex items-center gap-3"><div className="rounded-lg border border-zinc-800 bg-black p-2 text-zinc-400"><Icon className="h-4 w-4" /></div><p className="text-sm font-medium text-zinc-200">{title}</p></div><p className="mt-4 text-lg font-semibold text-zinc-50">{value}</p><p className="mt-1 text-xs leading-5 text-zinc-500">{detail}</p></CardContent></Card>;
}
