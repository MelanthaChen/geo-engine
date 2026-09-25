import { describe, expect, it } from "vitest";

import {
  isOptimizationStrategy,
  OPTIMIZATION_STRATEGIES,
  recommendedStrategyForOpportunity,
  selectedValidationStrategy,
} from "./predictorStrategies.ts";

describe("Predictor strategy selection", () => {
  it("defaults to the strategy mapped from the audit opportunity", () => {
    expect(recommendedStrategyForOpportunity({ category: "missing_geo_topics" })).toBe("authoritative");
    expect(recommendedStrategyForOpportunity({ category: "internal_linking_suggestions" })).toBe("citation");
    expect(recommendedStrategyForOpportunity({ category: "faq_opportunities" })).toBe("easy_to_understand");
  });

  it("allows a user to select any supported treatment strategy", () => {
    for (const strategy of OPTIMIZATION_STRATEGIES) {
      expect(isOptimizationStrategy(strategy)).toBe(true);
    }
  });

  it("passes the user-selected strategy to validation instead of the recommendation", () => {
    const recommended = recommendedStrategyForOpportunity({ category: "missing_geo_topics" });
    const selected = selectedValidationStrategy("citation");

    expect(recommended).toBe("authoritative");
    expect(selected).toBe("citation");
  });

  it("rejects the baseline and unsupported strategy values", () => {
    expect(isOptimizationStrategy("original")).toBe(false);
    expect(isOptimizationStrategy("unsupported")).toBe(false);
    expect(() => selectedValidationStrategy("original")).toThrow();
    expect(() => selectedValidationStrategy("unsupported")).toThrow();
  });
});
