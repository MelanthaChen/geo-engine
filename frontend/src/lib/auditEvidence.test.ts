import { describe, expect, it } from "vitest";

import type { AuditResult, WebsitePageAudit } from "@/api/audit";
import { buildAuditEvidence, formatAbsentSignal, pageExclusionReason } from "./auditEvidence";

function page(overrides: Partial<WebsitePageAudit> = {}): WebsitePageAudit {
  return {
    id: 1,
    url: "https://example.com/guide",
    page_title: "Security Guide",
    meta_description: "Customer help and privacy guidance",
    h1: "Guide",
    status_code: 200,
    word_count: 200,
    internal_link_count: 4,
    external_link_count: 2,
    content_sha256: "abc",
    is_duplicate: false,
    duplicate_of_url: null,
    ...overrides,
  };
}

function audit(pages: WebsitePageAudit[]): AuditResult {
  return {
    id: 1,
    property_id: 2,
    property_name: "Example",
    website_url: "https://example.com",
    last_audit: "2026-09-25T12:00:00Z",
    overall_geo_score: 99,
    brand_understanding: {},
    pages,
    missing_pages: [],
    missing_geo_topics: [],
    internal_linking_suggestions: [],
    faq_opportunities: [],
    content_recommendations: [],
  };
}

describe("buildAuditEvidence", () => {
  it("builds the presentation model without exposing heuristic score fields", () => {
    const evidence = buildAuditEvidence(audit([page()]));

    expect(evidence).not.toHaveProperty("websiteHealth");
    expect(evidence).not.toHaveProperty("contentQuality");
    expect(evidence).not.toHaveProperty("technicalQuality");
    expect(evidence).not.toHaveProperty("authority");
    expect(evidence).not.toHaveProperty("readability");
  });

  it("reports factual content, structure, and detected trust signals from unique pages", () => {
    const evidence = buildAuditEvidence(audit([
      page(),
      page({ id: 2, url: "https://example.com/privacy", page_title: null, h1: null, meta_description: null, word_count: 100, internal_link_count: 2, external_link_count: 0 }),
      page({ id: 3, is_duplicate: true, duplicate_of_url: "https://example.com/guide" }),
    ]));

    expect(evidence.pages).toHaveLength(2);
    expect(evidence.totalWords).toBe(300);
    expect(evidence.averageWords).toBe(150);
    expect(evidence.pagesWithTitle).toBe(1);
    expect(evidence.internalLinks).toBe(6);
    expect(evidence.pathCategories.find((item) => item.label === "Guide / resource")?.detected).toBe(true);
    expect(evidence.trustSignals.find((item) => item.label === "Privacy-related content")?.detected).toBe(true);
  });

  it("states why duplicate and empty responses are excluded", () => {
    expect(pageExclusionReason(page({ is_duplicate: true, duplicate_of_url: "https://example.com/" }))).toContain("Duplicate content");
    expect(pageExclusionReason(page({ word_count: 0 }))).toContain("No analyzable extracted text");
  });

  it("qualifies absent signals as limited to analyzed evidence", () => {
    expect(formatAbsentSignal("Security-related content", "Not detected in analyzed evidence"))
      .toBe("Security-related content — Not detected in analyzed evidence");
  });
});
