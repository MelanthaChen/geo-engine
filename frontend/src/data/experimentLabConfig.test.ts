import { describe, expect, it } from "vitest";

import { strategyOptions, treatmentStrategyOptions } from "./experimentLabConfig";

describe("experiment treatment strategies", () => {
  it("offers FAQ but keeps Original as a non-selectable baseline", () => {
    expect(treatmentStrategyOptions.map((strategy) => strategy.id)).toContain("faq");
    expect(treatmentStrategyOptions.map((strategy) => strategy.id)).not.toContain("original");
    expect(strategyOptions.find((strategy) => strategy.id === "faq")?.label).toBe("FAQ / Q&A Structure");
  });
});
