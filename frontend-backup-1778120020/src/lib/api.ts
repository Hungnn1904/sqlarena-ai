/**
 * api.ts — Axios instance with interceptors, error handling & retry logic
 * Base URL: http://localhost:8000
 */

import axios, {
  AxiosInstance,
  AxiosError,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Retry configuration
// ---------------------------------------------------------------------------

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 500;

/** HTTP status codes safe to retry */
const RETRYABLE_STATUS_CODES = new Set([
  408, // Request Timeout
  429, // Too Many Requests
  500, // Internal Server Error
  502, // Bad Gateway
  503, // Service Unavailable
  504, // Gateway Timeout
]);

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// Request interceptor
// ---------------------------------------------------------------------------

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Attach retry counter on first send
    if (config.headers && !(config as any).__retryCount) {
      (config as any).__retryCount = 0;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// ---------------------------------------------------------------------------
// Response interceptor — retry + error normalization
// ---------------------------------------------------------------------------

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalConfig = error.config as InternalAxiosRequestConfig & {
      __retryCount?: number;
    };

    if (!originalConfig) {
      return Promise.reject(normalizeError(error));
    }

    // Retry logic
    const status = error.response?.status;
    const canRetry =
      status !== undefined &&
      RETRYABLE_STATUS_CODES.has(status) &&
      (originalConfig.__retryCount ?? 0) < MAX_RETRIES;

    if (canRetry) {
      originalConfig.__retryCount = (originalConfig.__retryCount ?? 0) + 1;
      const delay = RETRY_DELAY_MS * originalConfig.__retryCount;

      await sleep(delay);
      return api(originalConfig);
    }

    return Promise.reject(normalizeError(error));
  }
);

// ---------------------------------------------------------------------------
// Error helpers
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  public readonly status?: number;
  public readonly code?: string;
  public readonly detail?: unknown;

  constructor(message: string, status?: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function normalizeError(error: AxiosError): ApiError {
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data as any;
    const message =
      data?.detail ?? data?.message ?? error.message ?? `HTTP ${status}`;
    return new ApiError(message, status, data);
  }

  if (error.request) {
    return new ApiError(
      "Network error: unable to reach the server.",
      undefined,
      error.request
    );
  }

  return new ApiError(error.message);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Typed API methods
// ---------------------------------------------------------------------------

import {
  HealthResponse,
  GenerateRequest,
  GenerateResponse,
  QuestionsListResponse,
  Question,
  StatusUpdateRequest,
  UpdateStatusResponse,
  StatsResponse,
  VerifyRequest,
  VerifyResponse,
  TaskResponse,
} from "./types";

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export async function postGenerate(
  payload: GenerateRequest
): Promise<GenerateResponse> {
  const { data } = await api.post<GenerateResponse>("/generate", payload);
  return data;
}

export async function getQuestions(
  params?: {
    status?: string;
    difficulty?: string;
    limit?: number;
  }
): Promise<QuestionsListResponse> {
  const { data } = await api.get<QuestionsListResponse>("/questions", { params });
  return data;
}

export async function getQuestionById(questionId: string): Promise<Question> {
  const { data } = await api.get<Question>(`/questions/${questionId}`);
  return data;
}

export async function putQuestionStatus(
  questionId: string,
  payload: StatusUpdateRequest
): Promise<UpdateStatusResponse> {
  const { data } = await api.put<UpdateStatusResponse>(
    `/questions/${questionId}/status`,
    payload
  );
  return data;
}

export async function getStats(): Promise<StatsResponse> {
  const { data } = await api.get<StatsResponse>("/stats");
  return data;
}

export async function postVerifySQL(
  payload: VerifyRequest
): Promise<VerifyResponse> {
  const { data } = await api.post<VerifyResponse>("/verify-sql", payload);
  return data;
}

export async function getTaskStatus(taskId: string): Promise<TaskResponse> {
  const { data } = await api.get<TaskResponse>(`/tasks/${taskId}`);
  return data;
}
