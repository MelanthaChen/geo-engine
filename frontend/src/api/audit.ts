import apiClient from "./client";

export type AuditSection = {
  status?: string;
  items?: string[];
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
