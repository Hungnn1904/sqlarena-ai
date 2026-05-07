import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health
export const getHealth = () => api.get('/health').then((res) => res.data);

// Stats
export const getStats = () => api.get('/stats').then((res) => res.data);

// Generate
export interface GenerateRequest {
  specs: string[];
  questions_per_spec: number;
}

export const generateQuestions = (data: GenerateRequest) =>
  api.post('/generate', data).then((res) => res.data);

// Questions
export interface QuestionItem {
  id: string;
  topic: string;
  difficulty: 'easy' | 'medium' | 'hard';
  domain: string;
  status: 'pending_review' | 'approved' | 'rejected' | 'active' | 'archived';
  created_at?: string;
  question_text?: string;
  validation_status?: string;
}

export const listQuestions = (params?: {
  status?: string;
  difficulty?: string;
  limit?: number;
}) =>
  api
    .get('/questions', { params })
    .then((res) => res.data as { questions: QuestionItem[]; total: number });

export const getQuestion = (id: string) =>
  api.get(`/questions/${id}`).then((res) => res.data as QuestionItem);

export const updateQuestionStatus = (
  id: string,
  status: 'approved' | 'rejected' | 'archived',
  review_notes?: string
) =>
  api
    .put(`/questions/${id}/status`, { status, review_notes })
    .then((res) => res.data);

// Verify SQL
export interface VerifyRequest {
  ddl_sql: string;
  seed_sql: string;
  answer_sql: string;
}

export interface VerifyResult {
  status: 'pass' | 'fail';
  message?: string;
  details?: string;
  result_set?: unknown[];
  expected_set?: unknown[];
}

export const verifySQL = (data: VerifyRequest) =>
  api.post('/verify-sql', data).then((res) => res.data as VerifyResult);

// Tasks
export const getTask = (taskId: string) =>
  api.get(`/tasks/${taskId}`).then((res) => res.data);

export default api;
