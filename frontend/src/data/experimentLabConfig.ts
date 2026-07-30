import type {
  EvaluationMetricId,
  ExperimentConfigurationValues,
  StrategyId,
} from "@/types/experimentLab";

export const strategyOptions: Array<{
  id: StrategyId;
  label: string;
  tableLabel: string;
}> = [
  { id: "original", label: "Original", tableLabel: "Original" },
  {
    id: "statistics",
    label: "Statistics Addition",
    tableLabel: "Statistics",
  },
  { id: "citation", label: "Cite Sources", tableLabel: "Cite Sources" },
  { id: "quotation", label: "Quotation Addition", tableLabel: "Quotation" },
  {
    id: "fluency",
    label: "Fluency Optimization",
    tableLabel: "Fluency",
  },
  {
    id: "authoritative",
    label: "Authoritative",
    tableLabel: "Authoritative",
  },
  {
    id: "easy_to_understand",
    label: "Easy-to-understand",
    tableLabel: "Easy-to-understand",
  },
  {
    id: "unique_words",
    label: "Unique Words",
    tableLabel: "Unique Words",
  },
  {
    id: "technical_terms",
    label: "Technical Terms",
    tableLabel: "Technical Terms",
  },
  {
    id: "keyword_stuffing",
    label: "Keyword Stuffing",
    tableLabel: "Keyword Stuffing",
  },
];

export const evaluationMetricOptions: Array<{
  id: EvaluationMetricId;
  label: string;
}> = [
  {
    id: "pawc",
    label: "Position-adjusted Word Count (PAWC)",
  },
  {
    id: "citation_count",
    label: "Citation Count",
  },
  {
    id: "visibility_score",
    label: "Visibility Score",
  },
];

export const defaultExperimentConfiguration: ExperimentConfigurationValues = {
  experimentName: "Princeton GEO Reproduction",
  description: "",
  provider: "chatgpt",
  llm: "gpt-3.5-turbo",
  dataset: "custom",
  benchmarkSource: "manual",
  manualQuery: "Best AI Resume Builder",
  uploadedQueries: [],
  uploadedDocuments: [],
  strategies: strategyOptions.map((strategy) => strategy.id),
  numberOfQueries: 1,
  randomSeed: 42,
  temperature: 0.7,
  evaluationMetrics: evaluationMetricOptions.map((metric) => metric.id),
};
