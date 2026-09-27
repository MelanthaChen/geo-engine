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
    expect(recommendedStrategyForOpportunity({ category: "faq_opportunities" })).toBe("faq");
    expect(recommendedStrategyForOpportunity({ category: "statistics" })).toBe("statistics");
    expect(recommendedStrategyForOpportunity({ category: "citation" })).toBe("citation");
    expect(recommendedStrategyForOpportunity({ category: "authoritative" })).toBe("authoritative");
  });

  it("allows a user to select any supported treatment strategy", () => {
    for (const strategy of OPTIMIZATION_STRATEGIES) {
      expect(isOptimizationStrategy(strategy)).toBe(true);
    }
    expect(OPTIMIZATION_STRATEGIES).toContain("faq");
    expect(OPTIMIZATION_STRATEGIES).not.toContain("original");
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

  it("keeps FAQ manually selectable even when it is not the audit recommendation", () => {
    expect(recommendedStrategyForOpportunity({ category: "heading_structure" })).not.toBe("faq");
    expect(selectedValidationStrategy("faq")).toBe("faq");
  });
});
