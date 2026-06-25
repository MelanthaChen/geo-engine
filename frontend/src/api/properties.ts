import apiClient from "./client";

export type Property = {
  id: number;
  name: string;
  domain: string;
  brand_name: string | null;
  description?: string | null;
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

export type PropertyPayload = {
  name: string;
  domain: string;
  brand_name?: string | null;
  description?: string | null;
};

export async function fetchProperties() {
  const response = await apiClient.get<Property[] | { properties: Property[] }>(
    "/api/v1/properties",
  );

  if (Array.isArray(response.data)) {
    return response.data;
  }

  return response.data.properties || [];
}

export async function createProperty(
  property: PropertyPayload,
) {
  const response = await apiClient.post<Property>(
    "/api/v1/properties",
    property,
  );

  return response.data;
}

export async function updateProperty(
  propertyId: number,
  property: Partial<PropertyPayload>,
) {
  const response = await apiClient.patch<Property>(
    `/api/v1/properties/${propertyId}`,
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
