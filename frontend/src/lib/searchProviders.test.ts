import { describe, expect, it } from "vitest";

import { searchProviderLabel } from "./searchProviders";

describe("search provider terminology", () => {
  it("shows the active Exa provider without other-provider wording", () => {
    expect(searchProviderLabel("Exa")).toBe("Exa");
    expect(searchProviderLabel("Exa")).not.toContain("Brave");
    expect(searchProviderLabel("Exa")).not.toContain("Google");
  });

  it("continues to support the Brave provider label", () => {
    expect(searchProviderLabel("Brave Search")).toBe("Brave Search");
  });
});
