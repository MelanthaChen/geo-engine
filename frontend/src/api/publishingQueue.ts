import apiClient from "./client";

export type PublishingTask = {
  id: number;
  property_id: number | null;
  content_id: number;
  title: string;
  platform: string | null;
  account_handle: string | null;
  status: string;
  logs: string | null;
  error_message: string | null;
  formatted_title: string | null;
  formatted_body: string | null;
  formatter_name: string | null;
  formatter_version: string | null;
  created_at: string;
  updated_at: string;
};

export async function fetchPublishingTasks() {
  const response = await apiClient.get<{ tasks: PublishingTask[] }>(
    "/api/v1/publishing/tasks",
  );

  return response.data.tasks;
}
