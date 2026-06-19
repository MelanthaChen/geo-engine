import apiClient from "./client";

export type Property = {
  id: number;
  name: string;
  domain: string;
  brand_name: string;
  created_at?: string;
  updated_at?: string;
};

export type PropertyMetrics = {
  property_id: number;
  generated_content: number;
  published_content: number;
  tracked_prompts: number;
  citation_count: number;
  visibility_score: number;
  clicks: number;
  impressions: number;
};

export async function fetchProperties() {
  const response = await apiClient.get<Property[]>("/api/v1/properties");

  return response.data;
}

export async function createProperty(
  property: Pick<Property, "name" | "domain" | "brand_name">,
) {
  const response = await apiClient.post<Property>(
    "/api/v1/properties",
    property,
  );

  return response.data;
}

export async function fetchPropertyMetrics(propertyId: number) {
  const response = await apiClient.get<PropertyMetrics>(
    `/api/v1/properties/${propertyId}/metrics`,
  );

  return response.data;
}
