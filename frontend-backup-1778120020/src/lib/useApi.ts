/**
 * useApi.ts — React Query hooks for SQLArena AI API
 *
 * All hooks expose { data, isLoading, isError, error } for reads,
 * and { mutate, isLoading, isError, error, data, reset } for writes.
 */

"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
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
import {
  getHealth,
  postGenerate,
  getQuestions,
  getQuestionById,
  putQuestionStatus,
  getStats,
  postVerifySQL,
  getTaskStatus,
  ApiError,
} from "./api";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const queryKeys = {
  health: ["health"] as const,
  generate: ["generate"] as const,
  questions: (filters?: {
    status?: string;
    difficulty?: string;
    limit?: number;
  }) => ["questions", filters ?? {}] as const,
  question: (id: string) => ["question", id] as const,
  stats: ["stats"] as const,
  verify: ["verify-sql"] as const,
  task: (taskId: string) => ["task", taskId] as const,
};

// ---------------------------------------------------------------------------
// Read hooks
// ---------------------------------------------------------------------------

/** GET /health */
export function useHealth(
  options?: Omit<UseQueryOptions<HealthResponse, ApiError>, "queryKey" | "queryFn">
) {
  return useQuery<HealthResponse, ApiError>({
    queryKey: queryKeys.health,
    queryFn: getHealth,
    refetchInterval: 30000,
    ...options,
  });
}

/** GET /questions */
export function useQuestions(
  filters?: {
    status?: string;
    difficulty?: string;
    limit?: number;
  },
  options?: Omit<
    UseQueryOptions<QuestionsListResponse, ApiError>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<QuestionsListResponse, ApiError>({
    queryKey: queryKeys.questions(filters),
    queryFn: () => getQuestions(filters),
    ...options,
  });
}

/** GET /questions/{id} */
export function useQuestion(
  questionId: string,
  options?: Omit<
    UseQueryOptions<Question, ApiError>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<Question, ApiError>({
    queryKey: queryKeys.question(questionId),
    queryFn: () => getQuestionById(questionId),
    enabled: !!questionId,
    ...options,
  });
}

/** GET /stats */
export function useStats(
  options?: Omit<UseQueryOptions<StatsResponse, ApiError>, "queryKey" | "queryFn">
) {
  return useQuery<StatsResponse, ApiError>({
    queryKey: queryKeys.stats,
    queryFn: getStats,
    refetchInterval: 60000,
    ...options,
  });
}

/** GET /tasks/{task_id} — polling enabled while running/queued */
export function useTaskStatus(
  taskId: string | null,
  options?: Omit<UseQueryOptions<TaskResponse, ApiError>, "queryKey" | "queryFn">
) {
  return useQuery<TaskResponse, ApiError>({
    queryKey: queryKeys.task(taskId ?? ""),
    queryFn: () => getTaskStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "running" || data?.status === "queued") {
        return 2000; // poll every 2s while active
      }
      return false; // stop polling when done/failed
    },
    ...options,
  });
}

// ---------------------------------------------------------------------------
// Write hooks
// ---------------------------------------------------------------------------

/** POST /generate */
export function useGenerate(
  options?: Omit<
    UseMutationOptions<GenerateResponse, ApiError, GenerateRequest>,
    "mutationKey" | "mutationFn"
  >
) {
  return useMutation<GenerateResponse, ApiError, GenerateRequest>({
    mutationKey: queryKeys.generate,
    mutationFn: postGenerate,
    ...options,
  });
}

/** PUT /questions/{id}/status */
export function useUpdateQuestionStatus(
  options?: Omit<
    UseMutationOptions<
      UpdateStatusResponse,
      ApiError,
      { questionId: string; payload: StatusUpdateRequest }
    >,
    "mutationKey" | "mutationFn"
  >
) {
  const queryClient = useQueryClient();

  return useMutation<
    UpdateStatusResponse,
    ApiError,
    { questionId: string; payload: StatusUpdateRequest }
  >({
    mutationFn: ({ questionId, payload }) => putQuestionStatus(questionId, payload),
    onSuccess: (_data, variables) => {
      // Invalidate exact question + list caches
      queryClient.invalidateQueries({
        queryKey: queryKeys.question(variables.questionId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.questions(),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.stats,
      });
    },
    ...options,
  });
}

/** POST /verify-sql */
export function useVerifySQL(
  options?: Omit<
    UseMutationOptions<VerifyResponse, ApiError, VerifyRequest>,
    "mutationKey" | "mutationFn"
  >
) {
  return useMutation<VerifyResponse, ApiError, VerifyRequest>({
    mutationKey: queryKeys.verify,
    mutationFn: postVerifySQL,
    ...options,
  });
}
