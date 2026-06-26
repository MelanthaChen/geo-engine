import apiClient from "./client"

export type HistoryItem = {
  id: number | string;
  history_item_id?: number | string;
  history_item_type?: string;
  event_id?: number | string;
  title?: string;
  target_persona?: string | null;
  strategy_type?: string | null;
  content_type?: string | null;
  faq_source?: string | null;
  generation_mode?: string | null;
  publish_status?: string | null;
  visibility_score?: number | null;
  citation_count?: number | null;
  event_type?: string;
  event_summary?: string | null;
  publishing_job_id?: number | null;
  citation_test_run_id?: number | null;
  published_account?: string | null;
  published_platform?: string | null;
  published_url?: string | null;
  preview_url?: string | null;
  content_id?: number | string | null;
  body?: string | null;
  created_at?: string;
};

export async function fetchContentHistory() {

  const response = await apiClient.get(
    "/api/v1/content/history"
  )

  return response.data as { history: HistoryItem[] }
}

export async function deleteFaqHistory(
  id: number
) {
  const response = await apiClient.delete(
    `/api/v1/history/faqs/${id}`
  )

  return response.data
}

export async function deleteGeneratedContentHistory(
  id: number
) {
  const response = await apiClient.delete(
    `/api/v1/history/content/${id}`
  )

  return response.data
}

export async function deleteHistoryItem(
  itemType: string,
  id: number
) {
  const response = await apiClient.delete(
    `/api/v1/history/items/${encodeURIComponent(itemType)}/${id}`
  )

  return response.data
}
