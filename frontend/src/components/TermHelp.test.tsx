// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import { ExperimentSummary } from "@/components/ExperimentSummary";
import { TermHelp } from "@/components/TermHelp";
import { strategyTermKey, terminology } from "@/data/terminology";

beforeAll(() => {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverMock;
});

afterEach(cleanup);

describe("TermHelp", () => {
  it("renders its registry label and a labelled help control", () => {
    render(<TermHelp term="visibility" />);

    expect(screen.getByText("Visibility")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Help for Visibility" })).toBeTruthy();
  });

  it("exposes the same central description on hover and keyboard focus", async () => {
    const user = userEvent.setup();
    render(<TermHelp term="visibility" />);
    const trigger = screen.getByRole("button", { name: "Help for Visibility" });

    await user.hover(trigger);
    expect((await screen.findByRole("tooltip")).textContent).toContain(terminology.visibility.description);

    await user.unhover(trigger);
    trigger.focus();
    expect((await screen.findByRole("tooltip")).textContent).toContain(terminology.visibility.description);
  });

  it("opens on click for touch and pointer users", async () => {
    const user = userEvent.setup();
    render(<TermHelp term="training_sample" />);

    await user.click(screen.getByRole("button", { name: "Help for Training Sample" }));
    expect((await screen.findByRole("tooltip")).textContent).toContain(terminology.training_sample.description);
  });

  it("adds help to research metrics without decorating ordinary headings", () => {
    render(<ExperimentSummary run={null} />);

    expect(screen.getByRole("button", { name: "Help for Visibility" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Help for Citation Count" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Help for PAWC" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Help for Experiment Result" })).toBeNull();
  });
});

describe("terminology registry", () => {
  it("expands PAWC correctly", () => {
    expect(terminology.pawc.description).toContain("Position-Adjusted Word Count");
  });

  it("keeps a Training Sample distinct from a Repetition", () => {
    expect(terminology.training_sample.description).not.toBe(terminology.repetition.description);
    expect(terminology.training_sample.description).toContain("distinct query/context experiment");
    expect(terminology.repetition.description).toContain("same experimental context");
  });

  it("maps every supported treatment strategy to one shared definition", () => {
    const strategies = [
      "statistics", "citation", "quotation", "authoritative", "easy_to_understand",
      "fluency", "unique_words", "technical_terms", "keyword_stuffing", "faq",
    ];

    for (const strategy of strategies) {
      const term = strategyTermKey(strategy);
      expect(term).toBeDefined();
      expect(terminology[term!].description.length).toBeGreaterThan(20);
    }
  });
});
