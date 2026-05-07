'use client';

import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import {
  getHealth,
  getStats,
  generateQuestions,
  listQuestions,
  getQuestion,
  updateQuestionStatus,
  verifySQL,
  getTask,
  type GenerateRequest,
  type VerifyRequest,
} from './api';

// Health
export const useHealth = () =>
  useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000,
  });

// Stats
export const useStats = () =>
  useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 15000,
  });

// Generate
export const useGenerate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: generateQuestions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
};

// Questions
export const useQuestions = (params?: {
  status?: string;
  difficulty?: string;
  limit?: number;
}) =>
  useQuery({
    queryKey: ['questions', params],
    queryFn: () => listQuestions(params),
  });

export const useQuestion = (id: string) =>
  useQuery({
    queryKey: ['question', id],
    queryFn: () => getQuestion(id),
    enabled: !!id,
  });

export const useUpdateQuestionStatus = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      status,
      review_notes,
    }: {
      id: string;
      status: 'approved' | 'rejected' | 'archived';
      review_notes?: string;
    }) => updateQuestionStatus(id, status, review_notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
};

// Verify SQL
export const useVerifySQL = () =>
  useMutation({
    mutationFn: verifySQL,
  });

// Tasks
export const useTask = (taskId: string) =>
  useQuery({
    queryKey: ['task', taskId],
    queryFn: () => getTask(taskId),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data as { status?: string } | undefined;
      if (data?.status === 'done' || data?.status === 'failed') return false;
      return 2000;
    },
  });
