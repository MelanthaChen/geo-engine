import apiClient from "./client";
import { API_BASE_URL } from "./config";

export type TeacherSample = {
  sample_id: string;
  website_id: number | null;
  experiment_id: number;
  experiment_run_id: number;
  audit_id: number;
  audit_version: string;
  strategy: string;
  teacher_provider: string;
  teacher_model: string;
  teacher_model_version: string;
  prompt_version: string;
  evaluation_version: string;
  original_metrics: Record<string, number | null>;
  optimized_metrics: Record<string, number | null>;
  delta_metrics: Record<string, number | null>;
  baseline_metrics: Record<string, number | null>;
  treatment_metrics: Record<string, number | null>;
  metric_deltas: Record<string, number | null>;
  provenance: Record<string, unknown>;
  context_fingerprint: string | null;
  query: string | null;
  query_source: string | null;
  query_intent: string | null;
  target_url: string | null;
  target_page_id: number | null;
  originating_page_id: number | null;
  originating_page_url: string | null;
  target_snapshot_hash: string | null;
  reference_urls: Array<string | null>;
  reference_snapshot_hashes: Array<string | null>;
  reference_order: Array<number | null>;
  baseline_answer: string | null;
  treatment_answer: string | null;
  repetitions: Array<Record<string, unknown>>;
  repetition_count: number;
  source_mode: string;
  training_eligible: boolean;
  dataset_version: string;
  provenance_hash: string;
  created_at: string;
};

export type TeacherDataset = {
  dataset_version: string;
  creation_time: string;
  teacher_model: string;
  metric_version: string;
  experiment_count: number;
  sample_count: number;
  manifest_hash: string;
};

export type TeacherPipelineStatus = {
  module: "teacher_pipeline";
  status: "ready" | "empty";
  training_enabled: false;
  generated_samples: number;
  unique_training_contexts: number;
  repetitions: number;
  generated_answer_pairs: number;
  processed_experiments: number;
  completed_experiments_pending: number;
  teacher_models: string[];
  dataset_version: string | null;
  last_experiment_processed: number | null;
  last_processed_at: string | null;
  recent_samples: TeacherSample[];
  dataset: TeacherDataset | null;
  unique_queries: number;
  representative_target_pages: number;
  query_intents_covered: number;
  strategies_covered: number;
  reference_source_sets: number;
  generation: {
    experiment_id: number;
    status: string;
    training_sample_count: number;
    repetitions_per_context: number;
    queries_prepared: number;
    experiments_completed: number;
    training_samples_ready: number;
    current_query: string | null;
    error_message: string | null;
  } | null;
};

export type DatasetGenerationRequest = {
  property_id: number;
  audit_id: number;
  strategy: string;
  training_sample_count: number;
  repetitions_per_context: number;
  provider: string;
  llm: string;
  random_seed: number;
  temperature: number;
  confirmed: boolean;
};

export type DatasetGenerationPreview = {
  training_sample_count: number;
  repetitions_per_context: number;
  unique_queries: number;
  representative_target_pages: number;
  query_intents: string[];
  strategy: string;
  expected_baseline_calls: number;
  expected_strategy_rewrite_calls: number;
  expected_treatment_calls: number;
  expected_teacher_evaluations: number;
  pricing_estimate: null;
};

export async function fetchTeacherPipelineStatus() {
  const response = await apiClient.get<TeacherPipelineStatus>("/api/v1/teacher-pipeline/status");
  return response.data;
}

export async function fetchTeacherSamples(propertyId?: number, limit = 1000) {
  const response = await apiClient.get<TeacherSample[]>("/api/v1/teacher-pipeline/samples", {
    params: { property_id: propertyId || undefined, limit },
  });
  return response.data;
}

export function teacherDatasetExportUrl(format: "jsonl" | "csv") {
  return `${API_BASE_URL}/api/v1/teacher-pipeline/dataset/export?format=${format}`;
}

export async function previewDatasetGeneration(request: DatasetGenerationRequest) {
  const response = await apiClient.post<DatasetGenerationPreview>(
    "/api/v1/teacher-pipeline/dataset-generation/preview",
    { ...request, confirmed: false },
  );
  return response.data;
}

export async function startDatasetGeneration(request: DatasetGenerationRequest) {
  const response = await apiClient.post<{ id: number; status: string }>(
    "/api/v1/teacher-pipeline/dataset-generation/start",
    { ...request, confirmed: true },
  );
  return response.data;
}
