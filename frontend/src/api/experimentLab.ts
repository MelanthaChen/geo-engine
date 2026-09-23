import apiClient from "@/api/client";
import type {
  ExperimentConfigurationValues,
  ExperimentCampaignRun,
  ExperimentRun,
  OfficialReplicationRun,
  StrategyId,
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
    provider: configuration.provider,
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

export async function startAuditValidation(values: {
  websiteId: number;
  auditId: number;
  propertyName: string;
  websiteUrl: string;
  opportunityTitle: string;
  opportunityDirection: string;
  strategy: StrategyId;
}) {
  const query = `What information does ${values.propertyName} provide about ${values.opportunityTitle}?`;
  const response = await apiClient.post<ExperimentRun>(
    "/api/v1/experiment-lab/run",
    {
      property_id: values.websiteId,
      experiment_name: `Audit #${values.auditId} teacher validation`,
      description: `${values.opportunityDirection} Source website: ${values.websiteUrl}`,
      provider: "chatgpt",
      llm: "gpt-3.5-turbo",
      dataset: "custom",
      queries: [query],
      dataset_documents: null,
      strategies: ["original", values.strategy],
      number_of_queries: 1,
      random_seed: 42,
      temperature: 0.7,
      evaluation_metrics: ["pawc", "citation_count", "visibility_score"],
    },
  );
  return response.data;
}

export async function getExperimentCampaign(campaignId: number) {
  const response = await apiClient.get<ExperimentCampaignRun>(
    `/api/v1/experiment-lab/campaigns/${campaignId}`,
  );

  return response.data;
}

export async function startOfficialReplication(values: {
  stage: "stage1" | "stage2" | "stage3" | "full";
  subjective: boolean;
  experimentName?: string;
}) {
  const response = await apiClient.post<OfficialReplicationRun>(
    "/api/v1/experiment-lab/official-replications",
    {
      stage: values.stage,
      subjective: values.subjective,
      experiment_name: values.experimentName || null,
    },
  );
  return response.data;
}

export async function getOfficialReplication(experimentId: number) {
  const response = await apiClient.get<OfficialReplicationRun>(
    `/api/v1/experiment-lab/official-replications/${experimentId}`,
  );
  return response.data;
}

export async function listOfficialReplications() {
  const response = await apiClient.get<{ experiments: OfficialReplicationRun[] }>(
    "/api/v1/experiment-lab/official-replications",
  );
  return response.data.experiments;
}

export function officialReplicationArtifactUrl(
  experimentId: number,
  artifactPath: string,
) {
  const base = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
  return `${base}/api/v1/experiment-lab/official-replications/${experimentId}/artifacts/${artifactPath
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
}
