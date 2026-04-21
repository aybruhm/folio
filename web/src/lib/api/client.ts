import axios from 'axios'
import type { AxiosInstance, AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8000'

export interface ApiResponse<T> {
  data?: T
  error?: { code: string; message: string; details?: Record<string, unknown> }
}

export interface ApiError {
  code: string
  message: string
  field?: string
  details?: Record<string, unknown>
}

// Create axios instance
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  validateStatus: () => true // Don't throw on any status code
})

// Response interceptor for error handling
axiosInstance.interceptors.response.use(response => {
  // Handle error responses from API
  if (response.status >= 400) {
    const errorData = response.data?.error || response.data
    const error = new Error(
      errorData?.message || `API error: ${response.status} ${response.statusText}`
    ) as Error & { code?: string; details?: Record<string, unknown> }
    error.code = errorData?.code
    error.details = errorData?.details
    throw error
  }
  return response
})

export const api = {
  /**
   * GET request
   */
  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const response = await axiosInstance.get<T>(path, {
      params
    })
    return response.data
  },

  /**
   * POST request
   */
  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await axiosInstance.post<T>(path, body)
    return response.data
  },

  /**
   * PUT request
   */
  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await axiosInstance.put<T>(path, body)
    return response.data
  },

  /**
   * PATCH request
   */
  async patch<T>(path: string, body?: unknown): Promise<T> {
    const response = await axiosInstance.patch<T>(path, body)
    return response.data
  },

  /**
   * DELETE request
   */
  async delete<T>(path: string): Promise<T> {
    const response = await axiosInstance.delete<T>(path)
    return response.data
  },

  /**
   * File upload with FormData
   */
  async upload<T>(path: string, formData: FormData): Promise<T> {
    const response = await axiosInstance.post<T>(path, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  /**
   * Get axios instance for advanced usage
   */
  getInstance(): AxiosInstance {
    return axiosInstance
  }
}
