const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
const developmentApiBase = import.meta.env.DEV
  ? "http://127.0.0.1:8000"
  : undefined;

if (!configuredApiBase && !import.meta.env.DEV) {
  throw new Error(
    "VITE_API_BASE_URL is required for a production frontend build",
  );
}

export const API_BASE_URL = (
  configuredApiBase || developmentApiBase!
).replace(/\/$/, "");
