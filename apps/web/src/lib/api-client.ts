import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from "axios";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});


apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    if (typeof window !== "undefined") {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      if (session?.user?.api_key) {
        config.headers["X-API-Key"] = session.user.api_key;
      }
    }
    return config;
  }
);

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;


export function createServerApiClient(): AxiosInstance {
  return axios.create({
    baseURL: process.env.API_URL ?? "http://localhost:8000/api/v1",
    timeout: 30_000,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": process.env.API_KEY_PRIMARY ?? "",
    },
  });
}