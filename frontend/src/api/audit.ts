import apiClient from "./client";

export type AuditSection = {
  status?: string;
  items?: string[];
};

export type AuditFinding = {
  label: string;
  evidence: string;
  feature_key: string;
};

export type WebsiteFeature = {
  label: string;
  value: number | string | boolean | null;
  unit: string | null;
  availability: "available" | "unavailable";
  evidence: string;
};

export type OptimizationOpportunity = {
  id: number;
  category: string;
  title: string;
  direction: string;
  priority: string;
  evidence: string;
  observed_evidence: string;
  affected_page_count: number;
  evaluated_page_count: number;
  why_it_matters: string;
  evidence_url: string | null;
  basis: "objective_audit_finding";
  validation_status: "not_validated";
  predicted_gain: null;
};

export type WebsiteProfile = {
  website_health_score: number | null;
  content_quality_score: number | null;
  technical_quality_score: number | null;
  authority_score: number | null;
  readability_score: number | null;
  pages_crawled: number;
  successful_pages: number;
  total_word_count: number;
  internal_references: number;
  external_references: number;
  measurement_notes: Record<string, string>;
};

export type AuditCrawlCoverage = {
  inventory_source: "sitemap" | "recursive_links" | "legacy";
  crawl_limit: number | null;
  sample_page_limit: number | null;
  discovered_urls: number;
  selected_urls: number;
  not_selected_due_to_sampling: number;
  requested_urls: number;
  successful_responses: number;
  accepted_html_responses: number | null;
  robots_txt_detected: boolean | null;
  sitemap_detected: boolean | null;
  sitemap_url_count: number | null;
  successful_extractions: number | null;
  unique_content_pages: number;
  duplicate_fallback_responses: number;
  skipped_due_to_limit: number;
  truncated: boolean;
  sampling_applied: boolean;
  analysis_status: string;
};

export type AuditResult = {
  id: number;
  property_id: number;
  property_name: string;
  website_url: string;
  last_audit: string;
  status?: string;
  overall_geo_score: number | null;
  subscores?: {
    content_coverage: number | null;
    faq_coverage: number | null;
    internal_linking: number | null;
    website_structure: number | null;
    brand_clarity: number | null;
    trust_signals: number | null;
  };
  brand_understanding: AuditSection;
  website_profile?: WebsiteProfile;
  crawl_coverage?: AuditCrawlCoverage;
  strengths?: AuditFinding[];
  weaknesses?: AuditFinding[];
  website_features?: Record<string, WebsiteFeature>;
  optimization_opportunities?: OptimizationOpportunity[];
  pages?: WebsitePageAudit[];
  missing_pages: string[];
  missing_geo_topics: string[];
  internal_linking_suggestions: string[];
  faq_opportunities: string[];
  content_recommendations: string[];
};

export type WebsitePageAudit = {
  id: number;
  url: string;
  page_title: string | null;
  meta_description: string | null;
  h1: string | null;
  status_code: number | null;
  word_count: number;
  internal_link_count: number;
  external_link_count: number;
  content_sha256?: string | null;
  is_duplicate?: boolean;
  duplicate_of_url?: string | null;
};

export async function runWebsiteAudit(propertyId: number) {
  const response = await apiClient.post<AuditResult>("/api/v1/audit/run", {
    property_id: propertyId,
  });

  return response.data;
}

export async function fetchLatestWebsiteAudit(propertyId: number) {
  const response = await apiClient.get<AuditResult | null>("/api/v1/audit/latest", {
    params: {
      property_id: propertyId,
    },
  });

  return response.data;
}

export async function fetchWebsiteAudit(propertyId: number, auditId: number) {
  const response = await apiClient.get<AuditResult>(
    `/api/v1/audit/${auditId}`,
    {
      params: {
        property_id: propertyId,
      },
    },
  );

  return response.data;
}
