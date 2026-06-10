import apiClient from "./client";

export async function fetchAccounts() {
  const response = await apiClient.get("/api/v1/accounts");

  return response.data;
}

export async function updateAccountStage(
  accountId: number,
  lifecycleStage: string,
) {
  const response = await apiClient.patch(
    `/api/v1/accounts/${accountId}/stage`,
    {
      lifecycle_stage: lifecycleStage,
    },
  );

  return response.data;
}
