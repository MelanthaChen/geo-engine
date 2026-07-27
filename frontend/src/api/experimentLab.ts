import apiClient from "@/api/client";
import type {
  ExperimentConfigurationValues,
  ExperimentCampaignRun,
  ExperimentRun,
} from "@/types/experimentLab";

function experimentPayload(configuration: ExperimentConfigurationValues) {
  const queries =
    configuration.benchmarkSource === "manual"
      ? [configuration.manualQuery]
      : configuration.benchmarkSource === "csv"
        ? configuration.uploadedQueries
        : null;
  const queryCount = Array.isArray(queries) ? queries.length : 0;

  return {
    experiment_name: configuration.experimentName,
    description: configuration.description || null,
    llm: configuration.llm,
    dataset:
      configuration.benchmarkSource === "geo_bench"
        ? "geo_bench"
        : configuration.dataset,
    queries,
    dataset_documents:
      configuration.benchmarkSource === "csv" &&
      configuration.uploadedDocuments.length > 0
        ? configuration.uploadedDocuments
        : null,
    strategies: configuration.strategies,
    number_of_queries: queryCount || configuration.numberOfQueries,
    random_seed: configuration.randomSeed,
    temperature: configuration.temperature,
    evaluation_metrics: configuration.evaluationMetrics,
  };
}

export async function startExperimentLab(
  configuration: ExperimentConfigurationValues,
) {
  const response = await apiClient.post<ExperimentRun>(
    "/api/v1/experiment-lab/run",
    experimentPayload(configuration),
  );

  return response.data;
}

export async function startExperimentCampaign(
  configuration: ExperimentConfigurationValues,
) {
  const response = await apiClient.post<ExperimentCampaignRun>(
    "/api/v1/experiment-lab/campaigns",
    experimentPayload(configuration),
  );

  return response.data;
}

export async function getExperimentLabRun(experimentId: number) {
  const response = await apiClient.get<ExperimentRun>(
    `/api/v1/experiment-lab/runs/${experimentId}`,
  );

  return response.data;
}

export async function getExperimentCampaign(campaignId: number) {
  const response = await apiClient.get<ExperimentCampaignRun>(
    `/api/v1/experiment-lab/campaigns/${campaignId}`,
  );

  return response.data;
}
