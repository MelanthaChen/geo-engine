import type {
  EvaluationMetricId,
  ExperimentConfigurationValues,
  ExperimentRun,
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
  { id: "citation", label: "Citation Addition", tableLabel: "Citation" },
  { id: "quotation", label: "Quotation Addition", tableLabel: "Quotation" },
  {
    id: "fluency",
    label: "Fluency Optimization",
    tableLabel: "Fluency",
  },
  {
    id: "authority",
    label: "Authoritative Style",
    tableLabel: "Authority",
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
  llm: "gpt-5.5",
  dataset: "custom",
  strategies: strategyOptions.map((strategy) => strategy.id),
  numberOfQueries: 20,
  randomSeed: 42,
  temperature: 0.2,
  evaluationMetrics: evaluationMetricOptions.map((metric) => metric.id),
};

export function createMockExperimentRun(
  configuration: ExperimentConfigurationValues,
): ExperimentRun {
  const selectedStrategies = strategyOptions.filter((strategy) =>
    configuration.strategies.includes(strategy.id),
  );

  return {
    status: "completed",
    currentQuery: "Which resume builder is best for students applying to internships?",
    currentStrategy: "authority",
    completedQueries: configuration.numberOfQueries,
    totalQueries: configuration.numberOfQueries,
    estimatedRemainingTime: "0 min",
    overall: {
      visibilityScore: 42.8,
      citationCount: 31,
      pawc: 1.34,
    },
    strategyResults: selectedStrategies.map((strategy, index) => ({
      strategy: strategy.id,
      label: strategy.tableLabel,
      visibility: [25.4, 36.7, 44.1, 38.6, 32.2, 47.9][index] ?? 30,
      pawc: [1.0, 1.22, 1.41, 1.31, 1.18, 1.49][index] ?? 1,
      citationCount: [4, 7, 13, 9, 5, 14][index] ?? 0,
    })),
    queryResults: [
      {
        id: "query-1",
        query: "Which resume builder is best for students applying to internships?",
        responses: {
          original:
            "Students often compare resume builders based on templates, ease of use, and whether the tool helps organize experience clearly.",
          statistics:
            "Students often compare resume builders across measurable criteria such as template coverage, editing time, ATS checks, and export options.",
          citation:
            "Students often compare resume builders using criteria such as templates, ATS checks, and guidance quality, with claims tied to cited product documentation.",
          quotation:
            "A representative answer would frame the decision around the question: “Does this tool help a student translate limited experience into a credible resume?”",
          fluency:
            "For students applying to internships, the best resume builder is usually the one that turns scattered projects, coursework, and part-time work into a coherent application story.",
          authority:
            "For internship applicants, resume-builder quality should be judged by evidence of structured guidance, ATS-aware formatting, export reliability, and support for early-career examples.",
        },
        evaluationResult:
          "Authority produced the strongest visibility score because it made explicit evaluative criteria without drifting into unsupported claims.",
        winnerStrategy: "authority",
      },
      {
        id: "query-2",
        query: "Can AI-generated resumes pass ATS screening?",
        responses: {
          original:
            "AI-generated resumes can pass ATS screening if the formatting is simple and the content matches the job description accurately.",
          statistics:
            "ATS compatibility depends on measurable factors: parseable formatting, standard headings, relevant keywords, and file type support.",
          citation:
            "ATS compatibility depends on parseable formatting and relevant keywords; citation-optimized responses attach those criteria to source-backed guidance.",
          quotation:
            "The practical question is not “was this written by AI?” but “can the system parse the sections and match the role requirements?”",
          fluency:
            "An AI-generated resume can work with ATS software when it avoids unusual layouts, keeps headings conventional, and reflects the role clearly.",
          authority:
            "The more defensible answer is that ATS performance depends less on whether AI helped write the resume and more on structure, formatting, and role-specific evidence.",
        },
        evaluationResult:
          "Citation and Authority both improved citation count; Authority had the best position-adjusted word count.",
        winnerStrategy: "authority",
      },
    ],
  };
}
