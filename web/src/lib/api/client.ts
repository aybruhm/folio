import axios from "axios";
import type { AxiosRequestConfig } from "axios";
import { envUtils } from "@/utils/env";
import { queueRequest } from "$lib/stores/offline";
import type { SyncQueueItem } from "$lib/stores/offline";
import { clearAuthToken, getAuthToken, storeAuthToken } from "$lib/stores/offlineAuth";
import { goto } from "$app/navigation";

const API_BASE_URL = envUtils.getBaseUrl();

export interface ApiResponse<T> {
    data?: T;
    error?: {
        code: string;
        message: string;
        details?: Record<string, unknown>;
    };
}

export interface ApiError {
    code: string;
    message: string;
    field?: string;
    details?: Record<string, unknown>;
}

// Create axios instance for token refresh (without response interceptor to avoid recursion)
const refreshAxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
  validateStatus: () => true,
});

// Create axios instance
const axiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
    validateStatus: () => true, // Don't throw on any status code
});

function normalizeHeaders(
    headers: AxiosRequestConfig["headers"],
): Record<string, string> {
    if (!headers) return {};
    const resolved =
        typeof (headers as { toJSON?: () => Record<string, unknown> }).toJSON ===
        "function"
            ? (headers as { toJSON: () => Record<string, unknown> }).toJSON()
            : (headers as Record<string, unknown>);
    const normalized: Record<string, string> = {};
    for (const [key, value] of Object.entries(resolved)) {
        if (typeof value === "string") {
            normalized[key] = value;
        } else if (Array.isArray(value)) {
            normalized[key] = value.join(",");
        }
    }
    return normalized;
}

axiosInstance.interceptors.request.use(async (config) => {
    if (typeof window === "undefined") return config;

    const method = (config.method ?? "get").toUpperCase();
    if (method === "GET") return config;
    if (navigator.onLine) return config;

    const url = config.url ?? "";
    if (url.startsWith("/auth/")) return config;

    const data = config.data;
    if (typeof FormData !== "undefined" && data instanceof FormData) {
        throw new Error("Offline uploads require an active connection.");
    }

    const baseURL = config.baseURL ?? API_BASE_URL ?? window.location.origin;
    const fullUrl = url.startsWith("http")
        ? url
        : new URL(url, baseURL).toString();
    const headers = normalizeHeaders(config.headers);

    await queueRequest(
        fullUrl,
        method as SyncQueueItem["method"],
        data,
        headers,
    );

    return {
        ...config,
        adapter: async () => ({
            data: { queued: true },
            status: 202,
            statusText: "Accepted",
            headers: {},
            config,
        }),
    };
});

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => {
    // Handle error responses from API
    if (response.status >= 400) {
      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401) {
        const currentToken = getAuthToken();
        if (currentToken?.refreshToken) {
          // Try to refresh the token with retry logic
          return attemptTokenRefresh(currentToken.refreshToken, 3)
            .then((newToken) => {
              storeAuthToken(newToken);
              // Retry the original request with the new token
              const retryConfig = {
                ...response.config,
              };
              return axiosInstance(retryConfig);
            })
            .catch(() => {
              // If all refresh attempts fail, clear auth and redirect to login
              clearAuthToken();
              if (typeof window !== 'undefined') {
                goto('/login');
              }
              const errorData = response.data?.error || response.data;
              const error = new Error(
                errorData?.message || `API error: ${response.status} ${response.statusText}`,
              ) as Error & { code?: string; details?: Record<string, unknown> };
              error.code = errorData?.code;
              error.details = errorData?.details;
              throw error;
            });
        } else {
          // No refresh token available, clear auth and redirect to login
          clearAuthToken();
          if (typeof window !== 'undefined') {
            goto('/login');
          }
        }
      }

      const errorData = response.data?.error || response.data;
      const error = new Error(
        errorData?.message ||
          `API error: ${response.status} ${response.statusText}`,
      ) as Error & { code?: string; details?: Record<string, unknown> };
      error.code = errorData?.code;
      error.details = errorData?.details;
      throw error;
    }
    return response;
  }
);

/**
 * Attempt to refresh access token with retry logic
 */
async function attemptTokenRefresh(
  refreshToken: string,
  retriesLeft: number = 3,
): Promise<any> {
  try {
    return await refreshAccessToken(refreshToken);
  } catch (error) {
    if (retriesLeft > 1) {
      // Wait a bit before retrying (exponential backoff)
      const delay = 100 * (4 - retriesLeft);
      await new Promise(resolve => setTimeout(resolve, delay));
      return attemptTokenRefresh(refreshToken, retriesLeft - 1);
    }
    throw error;
  }
}

/**
 * Refresh access token using refresh token
 */
async function refreshAccessToken(
  refreshToken: string,
): Promise<any> {
  try {
    const response = await refreshAxiosInstance.post('/auth/refresh', {
      refresh_token: refreshToken,
    });

    if (response.status >= 400) {
      throw new Error('Token refresh failed');
    }

    return response.data;
  } catch (error) {
    throw new Error('Failed to refresh access token');
  }
}

export const api = {
    /**
     * GET request
     */
    async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
        const response = await axiosInstance.get<T>(path, {
            params,
        });
        return response.data;
    },

    /**
     * POST request
     */
    async post<T>(path: string, body?: unknown): Promise<T> {
        const response = await axiosInstance.post<T>(path, body);
        return response.data;
    },

    /**
     * PUT request
     */
    async put<T>(path: string, body?: unknown): Promise<T> {
        const response = await axiosInstance.put<T>(path, body);
        return response.data;
    },

    /**
     * PATCH request
     */
    async patch<T>(path: string, body?: unknown): Promise<T> {
        const response = await axiosInstance.patch<T>(path, body);
        return response.data;
    },

    /**
     * DELETE request
     */
    async delete<T>(path: string): Promise<T> {
        const response = await axiosInstance.delete<T>(path);
        return response.data;
    },

    /**
     * File upload with FormData
     */
    async upload<T>(path: string, formData: FormData): Promise<T> {
        const response = await axiosInstance.post<T>(path, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
        });
        return response.data;
    },

    /**
     * Get axios instance for advanced usage
     */
    getInstance() {
        return axiosInstance;
    },
};
