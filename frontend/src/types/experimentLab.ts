export type ExperimentStatus = "queued" | "running" | "completed" | "failed";

export type StrategyId =
  | "original"
  | "statistics"
  | "citation"
  | "quotation"
  | "fluency"
  | "authoritative"
  | "easy_to_understand"
  | "unique_words"
  | "technical_terms"
  | "keyword_stuffing";

export type EvaluationMetricId = "pawc" | "citation_count" | "visibility_score";
export type BenchmarkSource = "manual" | "csv" | "geo_bench";
export type LlmProvider = "chatgpt" | "perplexity";

export type ExperimentConfigurationValues = {
  experimentName: string;
  description: string;
  provider: LlmProvider;
  llm: "gpt-3.5-turbo";
  dataset: "custom" | "geo_bench";
  benchmarkSource: BenchmarkSource;
  manualQuery: string;
  uploadedQueries: string[];
  uploadedDocuments: UploadedDatasetDocument[];
  strategies: StrategyId[];
  numberOfQueries: number;
  randomSeed: number;
  temperature: number;
  evaluationMetrics: EvaluationMetricId[];
};

export type UploadedDatasetDocument = {
  query: string;
  rank: number;
  title: string;
  url: string;
  content: string;
};

export type StrategyResult = {
  strategy: StrategyId;
  label: string;
  visibility: number;
  pawc: number;
  citationCount: number;
};

export type QueryExperimentResult = {
  id: string;
  query: string;
  seedValue?: number | null;
  responses: Record<StrategyId, string>;
  evaluationResult: string;
  winnerStrategy: StrategyId;
  evidence?: QueryEvidence;
};

export type QueryEvidence = {
  topDocuments: Array<{
    rank: number;
    title: string | null;
    url: string;
    isSelected: boolean;
  }>;
  selectedDocumentRank: number | null;
  originalDocument: string;
  strategyDetails: StrategyEvidence[];
};

export type StrategyEvidence = {
  strategy: StrategyId;
  sampleIndex: number;
  modifiedDocument: string;
  finalPrompt: string;
  generatedAnswer: string;
  metrics: {
    wordCount: number;
    position: number | null;
    pawc: number;
    citationCount: number;
    visibilityScore: number;
  };
};

export type PaperAggregateResult = {
  strategy: StrategyId;
  label: string;
  runs: number;
  visibilityMean: number;
  visibilityStd: number;
  pawcMean: number;
  pawcStd: number;
  citationCountMean: number;
  citationCountStd: number;
  baselineVisibilityMean: number;
  baselinePawcMean: number;
  baselineCitationCountMean: number;
  visibilityImprovementMean: number;
  visibilityImprovementStd: number;
  pawcImprovementMean: number;
  pawcImprovementStd: number;
  citationCountImprovementMean: number;
  citationCountImprovementStd: number;
};

export type ExperimentRun = {
  id?: number;
  provider?: LlmProvider | null;
  status: ExperimentStatus;
  currentQuery: string;
  currentStrategy: StrategyId;
  currentSample: number;
  totalSamples: number;
  completedQueries: number;
  totalQueries: number;
  estimatedRemainingTime: string;
  overall: {
    visibilityScore: number;
    citationCount: number;
    pawc: number;
  };
  strategyResults: StrategyResult[];
  paperAggregates?: PaperAggregateResult[];
  queryResults: QueryExperimentResult[];
  errorMessage?: string | null;
  name?: string;
  description?: string | null;
  datasetName?: string | null;
  model?: string | null;
  runCount?: number;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt?: string | null;
  statistics?: ExperimentStatistic[];
  timeline?: ExperimentTimelineEvent[];
};

export type ExperimentStatistic = {
  strategy: StrategyId;
  metric: string;
  sampleCount: number;
  mean: number | null;
  median: number | null;
  variance: number | null;
  stddev: number | null;
  min: number | null;
  max: number | null;
  confidenceLevel: number | null;
  confidenceLow: number | null;
  confidenceHigh: number | null;
};

export type ExperimentTimelineEvent = {
  type: string;
  status?: string | null;
  message?: string | null;
  metadata?: Record<string, unknown>;
  createdAt?: string | null;
};

export type CampaignExperimentSummary = {
  id: number;
  status: ExperimentStatus;
  query: string;
  errorMessage?: string | null;
  paperAggregates: PaperAggregateResult[];
};

export type ExperimentCampaignRun = {
  id?: number;
  status: ExperimentStatus;
  name: string;
  description?: string | null;
  datasetName?: string | null;
  provider?: LlmProvider | null;
  model?: string | null;
  queryCount: number;
  seedCount: number;
  strategies: StrategyId[];
  metrics: EvaluationMetricId[];
  currentQuery: string;
  currentStrategy: StrategyId;
  currentSeed?: number | null;
  queriesCompleted: number;
  queriesRemaining: number;
  successCount: number;
  failureCount: number;
  estimatedRemainingTime: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt?: string | null;
  errorMessage?: string | null;
  paperAggregates: PaperAggregateResult[];
  strategyResults: StrategyResult[];
  experiments: CampaignExperimentSummary[];
  queryResults: QueryExperimentResult[];
};
