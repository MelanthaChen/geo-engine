import axios from "axios"

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
})

apiClient.interceptors.request.use((config) => {
  const propertyId = localStorage.getItem("geo_engine_active_property_id");

  if (
    !propertyId ||
    config.url?.startsWith("/api/v1/properties")
  ) {
    return config;
  }

  const method = config.method?.toLowerCase();

  if (method === "get" || method === "delete") {
    config.params = {
      ...config.params,
      property_id: propertyId,
    };

    return config;
  }

  if (
    config.data &&
    typeof config.data === "object" &&
    !(config.data instanceof FormData)
  ) {
    config.data = {
      ...config.data,
      property_id: Number(propertyId),
    };
  } else {
    config.params = {
      ...config.params,
      property_id: propertyId,
    };
  }

  return config;
});

export default apiClient
