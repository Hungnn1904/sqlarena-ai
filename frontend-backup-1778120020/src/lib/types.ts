/**
 * types.ts — TypeScript interfaces for SQLArena AI Backend API
 * Base URL: http://localhost:8000
 */

// ---------------------------------------------------------------------------
// Enums / string literals
// ---------------------------------------------------------------------------

export type QuestionStatus = "pending_review" | "approved" | "rejected" | "archived";

export type TaskStatus = "queued" | "running" | "done" | "failed";

// ---------------------------------------------------------------------------
// Question model (matches SQLite schema)
// ---------------------------------------------------------------------------

export interface Question {
  id: string;
  difficulty: string;
  topic: string;
  question_text: string;
  schema_sql: string;
  seed_sql: string;
  answer_sql: string;
  expected_output: string; // JSON stringified
  status: QuestionStatus;
  valid: number; // SQLite boolean (0/1)
  clarity_score: number | null;
  generation_attempt: number;
  review_notes: string;
  blueprint_json: string; // JSON stringified
  metadata_json: string; // JSON stringified
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

// ---------------------------------------------------------------------------
// API Request bodies
// ---------------------------------------------------------------------------

export interface GenerateRequest {
  specs: string[];
  questions_per_spec: number;
}

export interface StatusUpdateRequest {
  status: "approved" | "rejected" | "archived";
  review_notes?: string;
}

export interface VerifyRequest {
  ddl_sql: string;
  seed_sql: string;
  answer_sql: string;
}

// ---------------------------------------------------------------------------
// API Response payloads
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: "ok";
  version: string;
}

/** Sync generate (<= 3 questions) */
export interface GenerateSyncResponse {
  status: "done";
  result: unknown; // pipeline output shape varies
}

/** Async generate (> 3 questions) */
export interface GenerateAsyncResponse {
  task_id: string;
  status: "running";
  message: string;
}

export type GenerateResponse = GenerateSyncResponse | GenerateAsyncResponse;

export interface TaskResponse {
  status: TaskStatus;
  result?: unknown;
  error?: string;
}

export interface QuestionsListResponse {
  questions: Question[];
  total: number;
}

export interface UpdateStatusResponse {
  success: true;
}

export interface StatsResponse {
  total: number;
  by_status: Record<string, number>;
  by_difficulty: Record<string, number>;
  valid_rate: number;
}

export interface VerifyResponse {
  success: boolean;
  result?: unknown;
  error?: string;
  rows?: unknown[];
  columns?: string[];
  execution_time_ms?: number;
}

// ---------------------------------------------------------------------------
// Hook state types
// ---------------------------------------------------------------------------

export interface ApiState<T> {
  data: T | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
}

export interface ApiMutationState<T, V = void> {
  data: T | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  mutate: (variables: V) => Promise<T>;
  reset: () => void;
}
