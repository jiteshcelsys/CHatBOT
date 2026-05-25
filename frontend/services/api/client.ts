import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from "axios";
import { getIdToken } from "@/lib/firebase/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ─── Request interceptor: attach Firebase JWT ─────────────────────────────
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const token = await getIdToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // unauthenticated calls are fine for public routes
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response interceptor: unwrap envelope + normalise errors ─────────────
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ error?: { message: string } }>) => {
    const message =
      error.response?.data?.error?.message ??
      error.message ??
      "Unknown error";

    // Token expired — force refresh and retry once
    if (error.response?.status === 401) {
      try {
        await getIdToken(true);
        return apiClient.request(error.config!);
      } catch {
        // refresh failed — let caller handle
      }
    }
    return Promise.reject(new Error(message));
  }
);

export default apiClient;
