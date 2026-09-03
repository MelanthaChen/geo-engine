import apiClient from "./client";

export type PredictorComponentStatus = {
  name: string;
  status: "available" | "planned";
  detail: string;
};

export type PredictorStatus = {
  module: string;
  status: "foundation_ready";
  model_ready: boolean;
  version: string;
  components: PredictorComponentStatus[];
};

export type PredictorDataset = {
  status: "empty" | "available";
  total_samples: number;
  valid_samples: number;
  invalid_samples: number;
  strategies_covered: number;
  experiments_included: number;
  latest_sample_time: string | null;
  samples_by_strategy: Record<string, number>;
  samples_by_model: Record<string, number>;
  samples_by_provider: Record<string, number>;
  samples_by_experiment: Record<string, number>;
  missing_fields: Record<string, number>;
  source: string;
  feature_fields: string[];
  target_fields: string[];
  message: string;
};

export type PredictorTrainRequest = {
  embedding_model: string;
  target_metric: string;
  validation_split: number;
  random_seed: number;
};

export type PredictorPlaceholderResponse = {
  status: "not_implemented";
  message: string;
};

export async function fetchPredictorStatus() {
  const response = await apiClient.get<PredictorStatus>("/predictor/status");
  return response.data;
}

export async function fetchPredictorDataset() {
  const response = await apiClient.get<PredictorDataset>("/predictor/dataset");
  return response.data;
}

export async function downloadPredictorDataset(format: "csv" | "jsonl") {
  const response = await apiClient.get<Blob>("/predictor/dataset/export", {
    params: { format },
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `geo_predictor_dataset.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function requestPredictorTraining(request: PredictorTrainRequest) {
  const response = await apiClient.post<PredictorPlaceholderResponse>(
    "/predictor/train",
    request,
  );
  return response.data;
}

export async function requestPrediction(request: {
  query: string;
  strategy: string;
  original_document: string;
  modified_document: string;
}) {
  const response = await apiClient.post<PredictorPlaceholderResponse>(
    "/predictor/predict",
    request,
  );
  return response.data;
}
