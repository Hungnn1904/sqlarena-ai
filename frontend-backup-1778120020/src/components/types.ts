export type Difficulty = 'easy' | 'medium' | 'hard';
export type Topic = 'SELECT' | 'JOIN' | 'WHERE' | 'GROUP BY' | 'HAVING' | 'SUBQUERY' | 'CTE' | 'WINDOW FUNCTION';
export type QuestionStatus = 'pending_review' | 'approved' | 'rejected' | 'active';
export type PipelineStatus = 'idle' | 'running' | 'completed' | 'failed';
export type StepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface Question {
  id: string;
  topic: Topic;
  difficulty: Difficulty;
  domain: string;
  status: QuestionStatus;
  createdAt: string;
  questionText: string;
  validationStatus?: string;
}

export interface StatItem {
  label: string;
  value: string | number;
  color?: 'cyan' | 'green' | 'amber' | 'rose' | 'purple';
}

export interface PipelineStep {
  id: number;
  title: string;
  badges: { label: string; variant: BadgeVariant }[];
  content: React.ReactNode;
  status?: StepStatus;
}

export type BadgeVariant = 'llm' | 'rule' | 'db' | 'new' | 'free';

export interface NavItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
}
