import apiClient from "./client";

export type AuditSection = {
  status?: string;
  items?: string[];
};

export type AuditResult = {
  property_id: number;
  property_name: string;
  website_url: string;
  last_audit: string;
  overall_geo_score: number | null;
  brand_understanding: AuditSection;
  missing_pages: string[];
  missing_geo_topics: string[];
  internal_linking_suggestions: string[];
  faq_opportunities: string[];
  content_recommendations: string[];
};

export async function runWebsiteAudit(propertyId: number) {
  const response = await apiClient.post<AuditResult>("/api/v1/audit/run", {
    property_id: propertyId,
  });

  return response.data;
}
