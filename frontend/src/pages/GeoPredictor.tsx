import { useEffect, useState } from "react";
import {
  CheckCircle2,
  CircleDashed,
  Database,
  FlaskConical,
  Layers3,
  Sparkles,
} from "lucide-react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";
import { Input } from "../../@/components/ui/input";

import {
  fetchPredictorDataset,
  fetchPredictorStatus,
  downloadPredictorDataset,
  requestPrediction,
  requestPredictorTraining,
  type PredictorDataset,
  type PredictorStatus,
} from "@/api/predictor";
import {
  EmptyState,
  Page,
  PageHeader,
  SectionHeader,
  SummaryCard,
  SummaryGrid,
  fieldClassName,
} from "@/components/layout/PageLayout";

const pipelineSteps = [
  {
    name: "Collect experiment samples",
    description: "Transform completed GEO experiment runs into supervised rows.",
  },
  {
    name: "Build feature representation",
    description: "Create versioned document, query, and strategy embeddings.",
  },
  {
    name: "Train predictor",
    description: "Fit a scientifically approved model against selected targets.",
  },
  {
    name: "Validate and register",
    description: "Record evaluation metrics and publish a versioned artifact.",
  },
];

const initialTrainingConfiguration = {
  embedding_model: "not_configured",
  target_metric: "visibility_score",
  validation_split: 0.2,
  random_seed: 42,
};

export function GeoPredictor() {
  const [status, setStatus] = useState<PredictorStatus | null>(null);
  const [dataset, setDataset] = useState<PredictorDataset | null>(null);
  const [configuration, setConfiguration] = useState(initialTrainingConfiguration);
  const [trainingMessage, setTrainingMessage] = useState("");
  const [predictionMessage, setPredictionMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState<"train" | "predict" | null>(null);
  const [demo, setDemo] = useState({
    query: "How can this page become more visible in AI-generated answers?",
    strategy: "citation",
    original_document: "",
    modified_document: "",
  });

  useEffect(() => {
    let mounted = true;

    async function loadFoundation() {
      try {
        const [predictorStatus, datasetOverview] = await Promise.all([
          fetchPredictorStatus(),
          fetchPredictorDataset(),
        ]);
        if (mounted) {
          setStatus(predictorStatus);
          setDataset(datasetOverview);
        }
      } catch (error) {
        console.error(error);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    void loadFoundation();
    return () => {
      mounted = false;
    };
  }, []);

  async function handleTrain() {
    try {
      setSubmitting("train");
      const result = await requestPredictorTraining(configuration);
      setTrainingMessage(result.message);
    } catch (error) {
      console.error(error);
      setTrainingMessage("The predictor service is unavailable.");
    } finally {
      setSubmitting(null);
    }
  }

  async function handlePredict() {
    try {
      setSubmitting("predict");
      const result = await requestPrediction(demo);
      setPredictionMessage(result.message);
    } catch (error) {
      console.error(error);
      setPredictionMessage("The predictor service is unavailable.");
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Research"
        title="GEO Predictor"
        description="Prepare experiment-derived datasets and configuration for a future GEO prediction system. No training or prediction model is active yet."
      />

      <SummaryGrid>
        <SummaryCard
          label="Total Samples"
          value={loading ? "Loading" : String(dataset?.total_samples || 0)}
          detail={`${dataset?.valid_samples || 0} valid for export`}
        />
        <SummaryCard
          label="Strategies Covered"
          value={String(dataset?.strategies_covered || 0)}
          detail="Distinct GEO strategies"
        />
        <SummaryCard
          label="Experiments Included"
          value={String(dataset?.experiments_included || 0)}
          detail="Traceable completed experiments"
        />
        <SummaryCard
          label="Latest Sample"
          value={formatSampleTime(dataset?.latest_sample_time)}
          detail={status ? `Dataset API ${status.version}` : "Collection status"}
        />
      </SummaryGrid>

      <section>
        <SectionHeader
          title="Dataset Overview"
          description="Immutable supervised records automatically collected from completed GEO experiments."
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => void downloadPredictorDataset("jsonl")}>Export JSONL</Button>
              <Button onClick={() => void downloadPredictorDataset("csv")}>Export Dataset</Button>
            </div>
          }
        />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <Card className="border-zinc-800 bg-zinc-950">
            <CardContent className="p-6">
              <div className="flex items-start justify-between gap-5">
                <div>
                  <p className="text-sm font-medium text-zinc-100">Training sample repository</p>
                  <p className="mt-1 text-sm leading-6 text-zinc-500">
                    {dataset?.message || (
                      loading
                        ? "Checking the predictor dataset boundary."
                        : "Dataset summary is unavailable from the current backend."
                    )}
                  </p>
                </div>
                <Database className="h-5 w-5 text-blue-400" />
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <FieldList title="Input features" fields={dataset?.feature_fields || []} />
                <FieldList title="Prediction targets" fields={dataset?.target_fields || []} />
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-950">
            <CardContent className="p-6">
              <p className="text-sm font-medium text-zinc-100">Dataset provenance</p>
              <dl className="mt-5 space-y-4 text-sm">
                <InfoRow label="Source" value="Completed GEO experiments" />
                <InfoRow label="Storage" value="training_samples" />
                <InfoRow label="Valid samples" value={String(dataset?.valid_samples || 0)} />
                <InfoRow label="Invalid samples" value={String(dataset?.invalid_samples || 0)} />
              </dl>
            </CardContent>
          </Card>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <DistributionCard title="Samples by strategy" values={dataset?.samples_by_strategy || {}} />
          <DistributionCard title="Samples by provider" values={dataset?.samples_by_provider || {}} />
          <DistributionCard title="Samples by model" values={dataset?.samples_by_model || {}} />
        </div>

        <Card className="mt-4 border-zinc-800 bg-zinc-950">
          <CardContent className="p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-base font-semibold text-zinc-100">Dataset Health</h3>
                <p className="mt-1 text-sm text-zinc-500">Only complete, validated samples are included in exports.</p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-xs font-medium ${
                (dataset?.invalid_samples || 0) === 0
                  ? "border-emerald-900 bg-emerald-950/40 text-emerald-300"
                  : "border-amber-900 bg-amber-950/40 text-amber-300"
              }`}>
                {(dataset?.invalid_samples || 0) === 0 ? "Healthy" : "Needs review"}
              </span>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <HealthMetric label="Valid" value={dataset?.valid_samples || 0} />
              <HealthMetric label="Invalid" value={dataset?.invalid_samples || 0} />
              <HealthMetric label="Missing fields" value={sumValues(dataset?.missing_fields)} />
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <SectionHeader
          title="Predictor Configuration"
          description="Reserve the model inputs and reproducibility settings without starting training."
        />
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="grid gap-5 p-6 md:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-2">
              <span className="text-sm text-zinc-400">Embedding Model</span>
              <select
                className={fieldClassName}
                value={configuration.embedding_model}
                onChange={(event) => setConfiguration((current) => ({ ...current, embedding_model: event.target.value }))}
              >
                <option value="not_configured">Not configured</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm text-zinc-400">Target Metric</span>
              <select
                className={fieldClassName}
                value={configuration.target_metric}
                onChange={(event) => setConfiguration((current) => ({ ...current, target_metric: event.target.value }))}
              >
                <option value="visibility_score">Visibility score</option>
                <option value="citation_count">Citation count</option>
                <option value="subjective_score">Subjective score</option>
                <option value="pawc">PAWC</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm text-zinc-400">Validation Split</span>
              <Input
                type="number"
                min="0.05"
                max="0.95"
                step="0.05"
                className="border-zinc-800 bg-black"
                value={configuration.validation_split}
                onChange={(event) => setConfiguration((current) => ({ ...current, validation_split: Number(event.target.value) }))}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm text-zinc-400">Random Seed</span>
              <Input
                type="number"
                className="border-zinc-800 bg-black"
                value={configuration.random_seed}
                onChange={(event) => setConfiguration((current) => ({ ...current, random_seed: Number(event.target.value) }))}
              />
            </label>
          </CardContent>
        </Card>
      </section>

      <section>
        <SectionHeader
          title="Training Pipeline"
          description="The execution stages are defined as interfaces; all model operations remain disabled."
          actions={
            <Button onClick={handleTrain} disabled={submitting !== null}>
              <FlaskConical />
              {submitting === "train" ? "Validating..." : "Validate Configuration"}
            </Button>
          }
        />
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-6">
            <div className="grid gap-3 lg:grid-cols-4">
              {pipelineSteps.map((step, index) => (
                <div key={step.name} className="relative rounded-lg border border-zinc-800 bg-black p-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-400">
                      Step {index + 1}
                    </span>
                    {index === 0 ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <CircleDashed className="h-4 w-4 text-zinc-600" />
                    )}
                  </div>
                  <p className="mt-3 text-sm font-medium text-zinc-100">{step.name}</p>
                  <p className="mt-2 text-xs leading-5 text-zinc-500">{step.description}</p>
                </div>
              ))}
            </div>
            {trainingMessage && (
              <p className="mt-4 rounded-lg border border-blue-900/70 bg-blue-950/30 px-4 py-3 text-sm text-blue-200">
                {trainingMessage}
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      <section>
        <SectionHeader
          title="Prediction Demo"
          description="Exercise the future API contract. The current endpoint will never return a fabricated prediction."
        />
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
          <Card className="border-zinc-800 bg-zinc-950">
            <CardContent className="space-y-4 p-6">
              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
                <label className="space-y-2">
                  <span className="text-sm text-zinc-400">Query</span>
                  <Input
                    className="border-zinc-800 bg-black"
                    value={demo.query}
                    onChange={(event) => setDemo((current) => ({ ...current, query: event.target.value }))}
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-sm text-zinc-400">Strategy</span>
                  <Input
                    className="border-zinc-800 bg-black"
                    value={demo.strategy}
                    onChange={(event) => setDemo((current) => ({ ...current, strategy: event.target.value }))}
                  />
                </label>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <DocumentInput
                  label="Original Document"
                  value={demo.original_document}
                  onChange={(value) => setDemo((current) => ({ ...current, original_document: value }))}
                />
                <DocumentInput
                  label="Modified Document"
                  value={demo.modified_document}
                  onChange={(value) => setDemo((current) => ({ ...current, modified_document: value }))}
                />
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handlePredict}
                  disabled={submitting !== null || !demo.query || !demo.original_document || !demo.modified_document}
                >
                  <Sparkles />
                  {submitting === "predict" ? "Checking..." : "Request Prediction"}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-950">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <Layers3 className="h-5 w-5 text-blue-400" />
                <h3 className="text-base font-semibold text-zinc-100">Prediction output</h3>
              </div>
              <EmptyState className="mt-5 min-h-48">
                <div>
                  <p>{predictionMessage || "No prediction is available."}</p>
                  <p className="mt-2 text-xs text-zinc-600">A trained, versioned model will populate this panel in a future phase.</p>
                </div>
              </EmptyState>
            </CardContent>
          </Card>
        </div>
      </section>
    </Page>
  );
}

function FieldList({ title, fields }: { title: string; fields: string[] }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">{title}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {fields.length ? fields.map((field) => (
          <span key={field} className="rounded-md border border-zinc-800 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-300">
            {field}
          </span>
        )) : <span className="text-xs text-zinc-600">Awaiting schema</span>}
      </div>
    </div>
  );
}

function DistributionCard({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values);
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <h3 className="text-sm font-medium text-zinc-100">{title}</h3>
        <div className="mt-4 space-y-2">
          {entries.length ? entries.map(([label, count]) => (
            <div key={label} className="flex items-center justify-between gap-4 rounded-lg border border-zinc-800 bg-black px-3 py-2">
              <span className="truncate text-sm text-zinc-400">{label}</span>
              <span className="text-sm font-semibold text-zinc-100">{count}</span>
            </div>
          )) : (
            <EmptyState className="min-h-20 py-4">No samples collected.</EmptyState>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function HealthMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <p className="text-xs uppercase tracking-[0.14em] text-zinc-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-zinc-100">{value}</p>
    </div>
  );
}

function sumValues(values?: Record<string, number>) {
  return Object.values(values || {}).reduce((total, value) => total + value, 0);
}

function formatSampleTime(value?: string | null) {
  if (!value) return "No samples";
  return new Date(value).toLocaleDateString();
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-zinc-900 pb-3 last:border-0 last:pb-0">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-right font-medium text-zinc-200">{value}</dd>
    </div>
  );
}

function DocumentInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="space-y-2">
      <span className="text-sm text-zinc-400">{label}</span>
      <textarea
        className={`${fieldClassName} min-h-36 resize-y py-3`}
        placeholder={`Paste the ${label.toLowerCase()} here.`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
