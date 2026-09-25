import type { TeacherSample } from "@/api/teacherPipeline";

type MetricSet = Record<string, number | null>;

export type TeacherExperimentGroup = {
  key: string;
  experimentId: number;
  strategy: string;
  auditId: number;
  teacherModel: string;
  createdAt: string;
  samples: TeacherSample[];
  originalMetrics: MetricSet;
  optimizedMetrics: MetricSet;
  deltaMetrics: MetricSet;
};

type StoredAggregates = {
  original?: MetricSet;
  optimized?: MetricSet;
  delta?: MetricSet;
};

export function groupTeacherSamples(samples: TeacherSample[]): TeacherExperimentGroup[] {
  const groups = new Map<string, TeacherSample[]>();
  for (const sample of samples) {
    const key = `${sample.experiment_id}:${sample.strategy}`;
    groups.set(key, [...(groups.get(key) || []), sample]);
  }

  return Array.from(groups, ([key, groupedSamples]) => {
    const first = groupedSamples[0];
    const stored = readStoredAggregates(first.provenance);
    return {
      key,
      experimentId: first.experiment_id,
      strategy: first.strategy,
      auditId: first.audit_id,
      teacherModel: first.teacher_model,
      createdAt: first.created_at,
      samples: groupedSamples,
      originalMetrics: stored?.original || averageMetrics(groupedSamples, "original_metrics"),
      optimizedMetrics: stored?.optimized || averageMetrics(groupedSamples, "optimized_metrics"),
      deltaMetrics: stored?.delta || averageMetrics(groupedSamples, "delta_metrics"),
    };
  });
}

function readStoredAggregates(provenance: Record<string, unknown>): StoredAggregates | null {
  const value = provenance.aggregate_metrics;
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as StoredAggregates;
}

function averageMetrics(
  samples: TeacherSample[],
  field: "original_metrics" | "optimized_metrics" | "delta_metrics",
): MetricSet {
  const names = new Set(samples.flatMap((sample) => Object.keys(sample[field])));
  return Object.fromEntries(Array.from(names, (name) => {
    const values = samples
      .map((sample) => sample[field][name])
      .filter((value): value is number => typeof value === "number");
    return [name, values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null];
  }));
}
