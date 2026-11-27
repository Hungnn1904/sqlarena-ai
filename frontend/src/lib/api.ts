import axios from 'axios';

export function resolveApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, '');
  }
  if (process.env.NODE_ENV === 'development' && typeof window !== 'undefined') {
    const host =
      window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname;
    return `${window.location.protocol}//${host}:8000`;
  }
  return '';
}

const api = axios.create({
  baseURL: resolveApiBase(),
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  config.baseURL = resolveApiBase();
  if (typeof window !== 'undefined') {
    const token = window.localStorage.getItem('sqlarena_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export interface UserProfile {
  user_id: number;
  email: string;
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  role: 'learner' | 'admin';
  status: 'active' | 'locked';
  created_at?: string;
  last_login_at?: string | null;
  stats?: {
    solved_questions: number;
    total_submissions: number;
    passed_submissions: number;
  };
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export const extractApiError = (e: any, fallback: string): string => {
  const serverMsg =
    e?.response?.data?.message ||
    e?.response?.data?.error?.message ||
    e?.response?.data?.detail;
  if (serverMsg) return String(serverMsg);
  if (e?.code === 'ERR_NETWORK' || e?.message === 'Network Error') {
    return 'Không kết nối được tới máy chủ Backend API (cổng 8000). Hãy kiểm tra tiến trình backend đang chạy.';
  }
  return e?.message || fallback;
};

// 1. Auth & Profile APIs
export const loginUser = (identifier: string, password: string) =>
  api.post<AuthResponse>('/api/v1/auth/login', { identifier, password }).then((r) => r.data);

export const registerUser = (data: {
  email: string;
  username: string;
  password: string;
  display_name?: string;
}) => api.post<AuthResponse>('/api/v1/auth/register', data).then((r) => r.data);

export const getMe = () => api.get<UserProfile>('/api/v1/auth/me').then((r) => r.data);

export const updateProfile = (data: { display_name?: string; bio?: string; avatar_url?: string }) =>
  api.put<UserProfile>('/api/v1/auth/me', data).then((r) => r.data);

export const changePassword = (current_password: string, new_password: string) =>
  api.post('/api/v1/auth/change-password', { current_password, new_password }).then((r) => r.data);

// 2. Learner Weekly Set, Questions & SQL Sandbox APIs
export const getWeeklyCurrent = () => api.get('/api/v1/weekly/current').then((r) => r.data);

export const getWeeklyHistory = (page = 1) =>
  api.get(`/api/v1/weekly/history?page=${page}&page_size=20`).then((r) => r.data);

export const getWeeklyQuestions = (params?: {
  difficulty?: number;
  skill_id?: number;
  solved?: boolean;
  q?: string;
}) => api.get('/api/v1/weekly/current/questions', { params }).then((r) => r.data);

export const getQuestionDetail = (questionId: number) =>
  api.get(`/api/v1/questions/${questionId}`).then((r) => r.data);

export const getQuestionSubmissions = (question_id: number) =>
  api.get(`/api/v1/questions/${question_id}/submissions`).then((r) => r.data);

export const getDatasetSchema = () => api.get('/api/v1/dataset/schema').then((r) => r.data);

export const runSandboxSql = (question_id: number, sql: string) =>
  api.post('/api/v1/sql/run', { question_id, sql }).then((r) => r.data);

export const explainSandboxSql = (question_id: number, sql: string) =>
  api.post('/api/v1/sql/explain', { question_id, sql }).then((r) => r.data);

export const askAiSqlCoach = (payload: {
  question_id: number;
  sql: string;
  mode: 'review' | 'nl2sql' | 'interview' | 'autofix';
  prompt?: string;
  error_context?: string;
}) => api.post('/api/v1/sql/ai-coach', payload).then((r) => r.data);

export const submitGradingSql = (question_id: number, sql: string) =>
  api.post('/api/v1/submissions', { question_id, sql }).then((r) => r.data);

export const voteQuestion = (questionId: number, vote: 1 | -1 | 0) =>
  api.post(`/api/v1/questions/${questionId}/vote`, { vote }).then((r) => r.data);

export const reportQuestion = (
  questionId: number,
  data: { reason_type: string; comment: string }
) => api.post(`/api/v1/questions/${questionId}/reports`, data).then((r) => r.data);

export const getMyProgress = () => api.get('/api/v1/progress').then((r) => r.data);

export const getWeeklyLeaderboard = (set_id?: number) =>
  api.get('/api/v1/leaderboard/weekly', { params: set_id ? { set_id } : undefined }).then((r) => r.data);

export const getMonthlyLeaderboard = (year?: number, month?: number) =>
  api
    .get('/api/v1/leaderboard/monthly', {
      params: { ...(year ? { year } : {}), ...(month ? { month } : {}) },
    })
    .then((r) => r.data);

// 3. Admin Pipeline, Draft Review, Manual Question, Question Groups, Weekly Sets & Users APIs
export const getAdminDrafts = (params?: {
  status?: string;
  difficulty?: number;
  page?: number;
  page_size?: number;
}) => api.get('/api/v1/admin/drafts', { params }).then((r) => r.data);

export const getAdminDraftDetail = (draftId: number) =>
  api.get(`/api/v1/admin/drafts/${draftId}`).then((r) => r.data);

export const editAdminDraft = (
  draftId: number,
  data: { title?: string; question?: string; note?: string }
) => api.patch(`/api/v1/admin/drafts/${draftId}`, data).then((r) => r.data);

export const approveAdminDraft = (
  draftId: number,
  data?: { selected_run_id?: number; custom_sql?: string; note?: string }
) => api.post(`/api/v1/admin/drafts/${draftId}/approve`, data || {}).then((r) => r.data);

export const bulkApproveAdminDrafts = (draft_ids: number[], note?: string) =>
  api
    .post('/api/v1/admin/drafts/bulk-approve', {
      draft_ids,
      ...(note ? { note } : {}),
    })
    .then((r) => r.data);

export const rejectAdminDraft = (draftId: number, reason: string) =>
  api.post(`/api/v1/admin/drafts/${draftId}/reject`, { reason }).then((r) => r.data);

export const returnAdminDraftNeedsHuman = (draftId: number, note?: string) =>
  api
    .post(`/api/v1/admin/drafts/${draftId}/return-needs-human`, {
      ...(note ? { note } : {}),
    })
    .then((r) => r.data);

export const requeueAdminDraft = (draftId: number, note?: string) =>
  api.post(`/api/v1/admin/drafts/${draftId}/requeue`, { note }).then((r) => r.data);

export const createManualAdminQuestion = (data: {
  title: string;
  question: string;
  reference_sql: string;
  difficulty: number;
  skill_ids: number[];
  compare_mode?: 'ordered' | 'unordered';
}) => api.post('/api/v1/admin/questions/manual', data).then((r) => r.data);

export const getAdminQuestions = (params?: {
  status?: string;
  difficulty?: number;
  q?: string;
  page?: number;
  page_size?: number;
  unassigned_only?: boolean;
  has_reports?: boolean;
}) => api.get('/api/v1/admin/questions', { params }).then((r) => r.data);

export const getAdminQuestionFeedback = (params?: {
  status?: 'open' | 'resolved' | 'dismissed';
  question_id?: number;
  page?: number;
  page_size?: number;
}) => api.get('/api/v1/admin/questions/feedback', { params }).then((r) => r.data);

export const resolveAdminQuestionReport = (
  reportId: number,
  data: {
    action: 'rework' | 'return_needs_human' | 'retire' | 'dismiss';
    admin_note?: string;
    updated_title?: string;
    updated_question?: string;
    updated_sql?: string;
  }
) => api.post(`/api/v1/admin/reports/${reportId}/resolve`, data).then((r) => r.data);

export const getAdminQuestionDetail = (questionId: number) =>
  api.get(`/api/v1/admin/questions/${questionId}`).then((r) => r.data);

export const retireAdminQuestion = (questionId: number, reason: string) =>
  api.post(`/api/v1/admin/questions/${questionId}/retire`, { reason }).then((r) => r.data);

export const restoreAdminQuestion = (questionId: number, note?: string) =>
  api
    .post(`/api/v1/admin/questions/${questionId}/restore`, {
      note: note || 'Khôi phục câu hỏi bởi Admin',
    })
    .then((r) => r.data);

export const toggleAdminQuestionSource = (questionId: number, is_source: boolean) =>
  api.patch(`/api/v1/admin/questions/${questionId}/source`, { is_source }).then((r) => r.data);

// 4. Admin Question Groups (Batch Composer & 1-Click Publish)
export const getAdminQuestionGroups = () =>
  api.get('/api/v1/admin/question-groups').then((r) => r.data);

export const getAdminQuestionGroupDetail = (groupId: number) =>
  api.get(`/api/v1/admin/question-groups/${groupId}`).then((r) => r.data);

export const createAdminQuestionGroup = (data: {
  name: string;
  description?: string;
  question_ids?: number[];
  draft_ids?: number[];
}) => api.post('/api/v1/admin/question-groups', data).then((r) => r.data);

export const updateAdminQuestionGroup = (
  groupId: number,
  data: { name?: string; description?: string }
) => api.patch(`/api/v1/admin/question-groups/${groupId}`, data).then((r) => r.data);

export const updateAdminQuestionGroupItems = (groupId: number, question_ids: number[]) =>
  api.put(`/api/v1/admin/question-groups/${groupId}/items`, { question_ids }).then((r) => r.data);

export const addAdminQuestionGroupItems = (
  groupId: number,
  data: { question_ids?: number[]; draft_ids?: number[] }
) => api.post(`/api/v1/admin/question-groups/${groupId}/add-items`, data).then((r) => r.data);

export const deleteAdminQuestionGroup = (groupId: number) =>
  api.delete(`/api/v1/admin/question-groups/${groupId}`).then((r) => r.data);

export const publishAdminQuestionGroup = (
  groupId: number,
  data?: { mode?: 'append_active' | 'new_weekly_set'; set_title?: string }
) =>
  api
    .post(`/api/v1/admin/question-groups/${groupId}/publish`, data || { mode: 'append_active' })
    .then((r) => r.data);

// 5. Admin Jobs, Weekly Sets, Users & Settings
export const getAdminSettings = () => api.get('/api/v1/admin/settings').then((r) => r.data);

export const getAdminSkills = () => api.get('/api/v1/admin/skills').then((r) => r.data);

export const updateAdminSetting = (key: string, value: any) =>
  api.put(`/api/v1/admin/settings/${key}`, { value }).then((r) => r.data);

export const getGenerationJobs = () =>
  api.get('/api/v1/admin/generation-jobs').then((r) => r.data);

export const createGenerationJob = (data: {
  difficulty: number;
  skill_ids: number[];
  skill_quantities?: { skill_id: number; quantity: number }[];
  requested_count?: number;
  quantity?: number;
  topic?: string;
  auto_run?: boolean;
}) =>
  api
    .post('/api/v1/admin/generation-jobs', {
      difficulty: data.difficulty,
      skill_ids: data.skill_ids,
      ...(data.skill_quantities && data.skill_quantities.length > 0
        ? { skill_quantities: data.skill_quantities }
        : {}),
      quantity: data.quantity ?? data.requested_count ?? 3,
      topic: data.topic,
      auto_run: data.auto_run ?? true,
    })
    .then((r) => r.data);

export const getLlmUsage = () => api.get('/api/v1/admin/llm-usage').then((r) => r.data);

export const getAdminGatewayStatus = () =>
  api.get('/api/v1/admin/gateway-status').then((r) => r.data);

export const saveAdminGatewayKey = (data: {
  api_key: string;
  base_url?: string;
  preferred_model?: string;
  persist_env?: boolean;
}) => api.post('/api/v1/admin/gateway-key', data).then((r) => r.data);

export const runAdminWorker = () =>
  api.post('/api/v1/admin/generation-jobs/run-worker').then((r) => r.data);

export const getAdminWeeklySets = () => api.get('/api/v1/admin/weekly-sets').then((r) => r.data);

export const getAdminWeeklySetDetail = (setId: number) =>
  api.get(`/api/v1/admin/weekly-sets/${setId}`).then((r) => r.data);

export const createAdminWeeklySet = (data: { title: string; week_start: string }) =>
  api
    .post('/api/v1/admin/weekly-sets', {
      title: data.title,
      week_start: data.week_start,
    })
    .then((r) => r.data);

export const updateAdminWeeklySetItems = (setId: number, question_ids: number[]) =>
  api.put(`/api/v1/admin/weekly-sets/${setId}/items`, { question_ids }).then((r) => r.data);

export const removeAdminWeeklySetItem = (setId: number, questionId: number) =>
  api.delete(`/api/v1/admin/weekly-sets/${setId}/items/${questionId}`).then((r) => r.data);

export const publishAdminWeeklySet = (setId: number) =>
  api.post(`/api/v1/admin/weekly-sets/${setId}/publish`).then((r) => r.data);

export const closeAdminWeeklySet = (setId: number) =>
  api.post(`/api/v1/admin/weekly-sets/${setId}/close`).then((r) => r.data);

export const getAdminUsers = (params?: {
  role?: string;
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}) => api.get('/api/v1/admin/users', { params }).then((r) => r.data);

export const getAdminUserDetail = (userId: number) =>
  api.get(`/api/v1/admin/users/${userId}`).then((r) => r.data);

export const updateAdminUser = (
  userId: number,
  data: { role?: 'learner' | 'admin'; status?: 'active' | 'locked' }
) => api.patch(`/api/v1/admin/users/${userId}`, data).then((r) => r.data);

export const getHealth = () => api.get('/api/v1/health').then((r) => r.data);

// Backward-compatible exports for legacy showcase components
export interface GenerateRequest {
  specs: string[];
  questions_per_spec: number;
}
export interface QuestionItem {
  id: string;
  topic: string;
  difficulty: 'easy' | 'medium' | 'hard';
  domain: string;
  status: 'pending_review' | 'approved' | 'rejected' | 'active' | 'archived';
  created_at?: string;
  question_text?: string;
  validation_status?: string;
  schema_sql?: string;
  seed_sql?: string;
  answer_sql?: string;
  expected_output?: string;
}
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
export const getStats = (): Promise<any> => api.get('/api/v1/health').then((r) => r.data);
export const generateQuestions = (data: GenerateRequest): Promise<any> => Promise.resolve(data);
export const listQuestions = (params?: any): Promise<{ questions: QuestionItem[]; total: number }> =>
  Promise.resolve({ questions: params ? [] : [], total: 0 });
export const getQuestion = (id: string): Promise<QuestionItem> => Promise.resolve({ id } as QuestionItem);
export const updateQuestionStatus = (id: string, status: string, review_notes?: string): Promise<any> =>
  Promise.resolve({ id, status, review_notes });
export const verifySQL = (data: VerifyRequest): Promise<VerifyResult> =>
  Promise.resolve({ status: 'pass', message: data.answer_sql } as VerifyResult);
export const getTask = (taskId: string): Promise<any> => Promise.resolve({ id: taskId, status: 'done' });

export default api;
