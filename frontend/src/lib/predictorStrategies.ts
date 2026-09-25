import type { OptimizationOpportunity } from "@/api/audit";
import type { StrategyId } from "@/types/experimentLab";

export const OPTIMIZATION_STRATEGIES = [
  "statistics",
  "citation",
  "quotation",
  "authoritative",
  "easy_to_understand",
  "fluency",
  "unique_words",
  "technical_terms",
  "keyword_stuffing",
] as const satisfies readonly StrategyId[];

export type OptimizationStrategy = (typeof OPTIMIZATION_STRATEGIES)[number];

export const STRATEGY_LABELS: Record<OptimizationStrategy, string> = {
  statistics: "Statistics Addition",
  citation: "Cite Sources",
  quotation: "Quotation Addition",
  authoritative: "Authoritative",
  easy_to_understand: "Easy to Understand",
  fluency: "Fluency Optimization",
  unique_words: "Unique Words",
  technical_terms: "Technical Terms",
  keyword_stuffing: "Keyword Stuffing",
};

export function recommendedStrategyForOpportunity(
  opportunity: Pick<OptimizationOpportunity, "category">,
): OptimizationStrategy {
  const strategies: Record<string, OptimizationStrategy> = {
    faq_opportunities: "easy_to_understand",
    internal_linking_suggestions: "citation",
    missing_geo_topics: "authoritative",
    missing_pages: "fluency",
    content_recommendations: "authoritative",
  };
  return strategies[opportunity.category] || "fluency";
}

export function isOptimizationStrategy(value: string): value is OptimizationStrategy {
  return (OPTIMIZATION_STRATEGIES as readonly string[]).includes(value);
}

export function selectedValidationStrategy(value: string): OptimizationStrategy {
  if (!isOptimizationStrategy(value)) {
    throw new Error(`Unsupported optimization strategy: ${value}`);
  }
  return value;
}
