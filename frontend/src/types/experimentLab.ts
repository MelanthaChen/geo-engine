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

export type ExperimentConfigurationValues = {
  experimentName: string;
  description: string;
  llm: "gpt-3.5-turbo";
  dataset: "custom";
  benchmarkSource: BenchmarkSource;
  manualQuery: string;
  uploadedQueries: string[];
  strategies: StrategyId[];
  numberOfQueries: number;
  randomSeed: number;
  temperature: number;
  evaluationMetrics: EvaluationMetricId[];
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

export type ExperimentRun = {
  id?: number;
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
  queryResults: QueryExperimentResult[];
  errorMessage?: string | null;
};
