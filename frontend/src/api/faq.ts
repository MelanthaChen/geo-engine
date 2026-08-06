import apiClient from "./client"
import type { LlmProvider } from "@/types/experimentLab";

export type PlatformQuestion = {
  id: number;
  property_id: number | null;
  platform: string;
  title: string;
  body: string | null;
  url: string | null;
  author: string | null;
  hashtags?: string[];
  score: number | null;
  engagement_metrics?: Record<string, unknown>;
  retrieval_method?: string | null;
  raw_metadata?: Record<string, unknown>;
  created_at: string | null;
  discovered_at: string | null;
  content_hash: string;
};

export type GenerateFaqsResponse = {
  target: string;
  mode: string;
  status?: "retrieving";
  retrieval_task_id?: number;
  faqs: string;
  faq_set_id: number | null;
  faq_set: {
    id: number;
    category: string;
    faq_source: string;
    provider?: LlmProvider | null;
    questions: string[];
  } | null;
  platform_questions: PlatformQuestion[];
  result_type?: "faq" | "platform_posts";
};

export type RetrievalTaskResponse = {
  task: {
    id: number;
    property_id: number | null;
    account_id: number | null;
    platform: string;
    category: string;
    content_type: string | null;
    status: "queued" | "processing" | "completed" | "failed";
    result_count: number | null;
    error_message: string | null;
    created_at: string | null;
    updated_at: string | null;
    completed_at: string | null;
    platform_questions: PlatformQuestion[];
  };
};

export async function generateFaqs(
  target: string,
  mode: string,
  contentType: string = "comparison",
  publishPlatform: string = "reddit",
  propertyId?: number | null,
  provider: LlmProvider = "chatgpt",
  accountId?: number | null,
): Promise<GenerateFaqsResponse> {
  const params = new URLSearchParams({
    mode,
    content_type: contentType,
    publish_platform: publishPlatform,
    provider,
  });

  if (propertyId) {
    params.set("property_id", String(propertyId));
  }

  if (accountId) {
    params.set("account_id", String(accountId));
  }

  const response = await apiClient.get(
    `/api/v1/content/faqs/${encodeURIComponent(target)}?${params.toString()}`
  )

  return response.data
}

export async function getRetrievalTask(
  taskId: number,
): Promise<RetrievalTaskResponse> {
  const response = await apiClient.get(
    `/api/v1/content/retrieval-tasks/${taskId}`,
  );

  return response.data;
}
