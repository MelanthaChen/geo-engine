export type ExperimentStatus = "queued" | "running" | "completed" | "failed";

export type StrategyId =
  | "original"
  | "statistics"
  | "citation"
  | "quotation"
  | "fluency"
  | "authority";

export type EvaluationMetricId = "pawc" | "citation_count" | "visibility_score";

export type ExperimentConfigurationValues = {
  experimentName: string;
  description: string;
  llm: "gpt-5.5";
  dataset: "custom";
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
};

export type ExperimentRun = {
  status: ExperimentStatus;
  currentQuery: string;
  currentStrategy: StrategyId;
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
};
