import { describe, expect, it } from "vitest";

import type { TeacherSample } from "@/api/teacherPipeline";
import { groupTeacherSamples } from "./teacherExperimentGroups";

function sample(overrides: Partial<TeacherSample>): TeacherSample {
  return {
    sample_id: crypto.randomUUID(),
    website_id: 3,
    experiment_id: 3,
    experiment_run_id: 1,
    audit_id: 11,
    audit_version: "v1",
    strategy: "authoritative",
    teacher_provider: "chatgpt",
    teacher_model: "gpt-3.5-turbo",
    teacher_model_version: "gpt-3.5-turbo",
    prompt_version: "v1",
    evaluation_version: "v1",
    original_metrics: { visibility_score: 0.1 },
    optimized_metrics: { visibility_score: 0.5 },
    delta_metrics: { visibility_score: 0.4 },
    baseline_metrics: { visibility_score: 0.1 },
    treatment_metrics: { visibility_score: 0.5 },
    metric_deltas: { visibility_score: 0.4 },
    provenance: {},
    context_fingerprint: null,
    query: null,
    query_source: null,
    query_intent: null,
    target_url: null,
    target_page_id: null,
    originating_page_id: null,
    originating_page_url: null,
    target_snapshot_hash: null,
    reference_urls: [],
    reference_snapshot_hashes: [],
    reference_order: [],
    baseline_answer: null,
    treatment_answer: null,
    repetitions: [],
    repetition_count: 1,
    source_mode: "live_retrieval",
    training_eligible: true,
    dataset_version: "teacher-dataset-v1",
    provenance_hash: "abc",
    created_at: "2026-09-24T12:00:00Z",
    ...overrides,
  };
}

describe("groupTeacherSamples", () => {
  it("groups only samples sharing an experiment and strategy", () => {
    const groups = groupTeacherSamples([
      sample({ sample_id: "a" }),
      sample({ sample_id: "b" }),
      sample({ sample_id: "c", strategy: "citation" }),
      sample({ sample_id: "d", experiment_id: 4 }),
    ]);

    expect(groups).toHaveLength(3);
    expect(groups[0].samples.map((item) => item.sample_id)).toEqual(["a", "b"]);
    expect(groups[0].trainingEligibleCount).toBe(2);
    expect(groups[0].repetitionCount).toBe(2);
  });

  it("counts nested repetitions separately from unique contexts", () => {
    const groups = groupTeacherSamples([sample({
      context_fingerprint: "one-context",
      repetition_count: 5,
      repetitions: Array.from({ length: 5 }, (_, index) => ({ repetition_index: index })),
    })]);

    expect(groups[0].samples).toHaveLength(1);
    expect(groups[0].trainingEligibleCount).toBe(1);
    expect(groups[0].repetitionCount).toBe(5);
  });

  it("uses stored experiment aggregates rather than fabricating values", () => {
    const groups = groupTeacherSamples([sample({
      provenance: {
        aggregate_metrics: {
          original: { visibility_score: 0.021 },
          optimized: { visibility_score: 0.51 },
          delta: { visibility_score: 0.489 },
        },
      },
    })]);

    expect(groups[0].originalMetrics.visibility_score).toBe(0.021);
    expect(groups[0].optimizedMetrics.visibility_score).toBe(0.51);
    expect(groups[0].deltaMetrics.visibility_score).toBe(0.489);
  });

  it("aggregates sample metrics across genuinely distinct contexts", () => {
    const groups = groupTeacherSamples([
      sample({
        context_fingerprint: "context-a",
        original_metrics: { visibility_score: 0.1 },
        optimized_metrics: { visibility_score: 0.3 },
        delta_metrics: { visibility_score: 0.2 },
        provenance: { aggregate_metrics: { original: { visibility_score: 0.1 } } },
      }),
      sample({
        context_fingerprint: "context-b",
        original_metrics: { visibility_score: 0.3 },
        optimized_metrics: { visibility_score: 0.9 },
        delta_metrics: { visibility_score: 0.6 },
      }),
    ]);

    expect(groups[0].originalMetrics.visibility_score).toBeCloseTo(0.2);
    expect(groups[0].optimizedMetrics.visibility_score).toBeCloseTo(0.6);
    expect(groups[0].deltaMetrics.visibility_score).toBeCloseTo(0.4);
  });
});
