import apiClient from "@/api/client";
import type {
  ExperimentConfigurationValues,
  ExperimentRun,
} from "@/types/experimentLab";

export async function startExperimentLab(
  configuration: ExperimentConfigurationValues,
) {
  const queries =
    configuration.benchmarkSource === "manual"
      ? [configuration.manualQuery]
      : configuration.benchmarkSource === "csv"
        ? configuration.uploadedQueries
        : null;
  const queryCount = Array.isArray(queries) ? queries.length : 0;

  const response = await apiClient.post<ExperimentRun>(
    "/api/v1/experiment-lab/run",
    {
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
    },
  );

  return response.data;
}

export async function getExperimentLabRun(experimentId: number) {
  const response = await apiClient.get<ExperimentRun>(
    `/api/v1/experiment-lab/runs/${experimentId}`,
  );

  return response.data;
}
