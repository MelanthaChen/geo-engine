import { describe, expect, it } from "vitest";

import { validationRepetitionLabel } from "./experimentProgress";

describe("Teacher Validation progress terminology", () => {
  it("labels repeated generations as repetitions rather than training samples", () => {
    const label = validationRepetitionLabel("faq", 0, 5);

    expect(label).toBe("FAQ / Q&A Structure • repetition 0/5");
    expect(label).not.toContain("sample");
  });
});
