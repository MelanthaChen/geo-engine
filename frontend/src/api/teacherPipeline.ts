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
  provenance: Record<string, unknown>;
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
  processed_experiments: number;
  completed_experiments_pending: number;
  teacher_models: string[];
  dataset_version: string | null;
  last_experiment_processed: number | null;
  last_processed_at: string | null;
  recent_samples: TeacherSample[];
  dataset: TeacherDataset | null;
};

export async function fetchTeacherPipelineStatus() {
  const response = await apiClient.get<TeacherPipelineStatus>("/api/v1/teacher-pipeline/status");
  return response.data;
}

export function teacherDatasetExportUrl(format: "jsonl" | "csv") {
  return `${API_BASE_URL}/api/v1/teacher-pipeline/dataset/export?format=${format}`;
}
