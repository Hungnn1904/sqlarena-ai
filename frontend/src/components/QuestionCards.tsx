'use client';

import React from 'react';
import { useQuestions } from '@/lib/hooks';
import { Search, ChevronDown, Database, FileCode, MessageSquare, CheckCircle } from 'lucide-react';

type Difficulty = 'easy' | 'medium' | 'hard';
type Status = 'pending_review' | 'approved' | 'rejected' | 'active' | 'archived';

const difficultyStyles: Record<Difficulty, string> = {
  easy: 'badge-easy',
  medium: 'badge-medium',
  hard: 'badge-hard',
};

const statusStyles: Record<Status, string> = {
  pending_review: 'badge-medium',
  approved: 'badge-easy',
  rejected: 'badge-hard',
  active: 'badge-info',
  archived: 'badge-neutral',
};

const statusLabel: Record<Status, string> = {
  pending_review: 'Chờ duyệt',
  approved: 'Đã duyệt',
  rejected: 'Đã từ chối',
  active: 'Đang mở',
  archived: 'Lưu trữ',
};

interface DetailBlockProps {
  icon: React.ReactNode;
  label: string;
  content: string | undefined;
}

function DetailBlock({ icon, label, content }: DetailBlockProps) {
  if (!content) return null;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-semibold text-muted">
        {icon}
        <span>{label}</span>
      </div>
      <pre className="bg-canvas border border-line rounded-lg p-3 overflow-auto text-xs leading-relaxed text-ink max-h-[280px]">
        <code>{content}</code>
      </pre>
    </div>
  );
}

export default function QuestionCards() {
  const { data, isLoading, isError } = useQuestions({ limit: 200 });
  const [search, setSearch] = React.useState('');
  const [currentPage, setCurrentPage] = React.useState(1);
  const [filterDifficulty, setFilterDifficulty] = React.useState<Difficulty | 'all'>('all');
  const [filterTopic, setFilterTopic] = React.useState<string>('all');
  const [filterStatus, setFilterStatus] = React.useState<Status | 'all'>('all');
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());

  const itemsPerPage = 9;
  const questions = React.useMemo(() => data?.questions ?? [], [data]);
  const allTopics = React.useMemo(
    () => Array.from(new Set(questions.map((q) => q.topic))).sort(),
    [questions]
  );
  const allStatuses = React.useMemo(
    () => Array.from(new Set(questions.map((q) => q.status))).sort() as Status[],
    [questions]
  );

  const filtered = React.useMemo(() => {
    return questions.filter((q) => {
      const s = search.toLowerCase();
      const domain = (q as any).metadata_json
        ? JSON.parse((q as any).metadata_json)?.domain
        : (q as any).domain || '';
      const matchesSearch =
        (q.question_text?.toLowerCase() ?? '').includes(s) ||
        q.id.toLowerCase().includes(s) ||
        (domain?.toLowerCase() ?? '').includes(s) ||
        (q.topic?.toLowerCase() ?? '').includes(s);
      const matchesDifficulty = filterDifficulty === 'all' || q.difficulty === filterDifficulty;
      const matchesTopic = filterTopic === 'all' || q.topic === filterTopic;
      const matchesStatus = filterStatus === 'all' || q.status === filterStatus;
      return matchesSearch && matchesDifficulty && matchesTopic && matchesStatus;
    });
  }, [questions, search, filterDifficulty, filterTopic, filterStatus]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / itemsPerPage));
  const pageItems = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  React.useEffect(() => {
    setCurrentPage(1);
  }, [search, filterDifficulty, filterTopic, filterStatus]);

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="p-8 text-center text-sm text-muted bg-surface border border-line rounded-xl">
        Đang tải danh sách câu hỏi...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 text-danger text-sm">
        Không tải được danh sách câu hỏi.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[240px]">
          <input
            type="text"
            placeholder="Tìm kiếm câu hỏi..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface border border-line rounded-lg px-4 min-h-10 pl-10 text-sm text-ink placeholder:text-muted"
          />
          <Search className="absolute left-3 top-3 w-4 h-4 text-muted" />
        </div>

        <select
          value={filterTopic}
          onChange={(e) => setFilterTopic(e.target.value)}
          className="bg-surface border border-line rounded-lg px-3 min-h-10 text-sm text-ink"
        >
          <option value="all">Mọi chủ đề</option>
          {allTopics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <select
          value={filterDifficulty}
          onChange={(e) => setFilterDifficulty(e.target.value as Difficulty | 'all')}
          className="bg-surface border border-line rounded-lg px-3 min-h-10 text-sm text-ink"
        >
          <option value="all">Mọi độ khó</option>
          <option value="easy">Dễ</option>
          <option value="medium">Trung bình</option>
          <option value="hard">Khó</option>
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as Status | 'all')}
          className="bg-surface border border-line rounded-lg px-3 min-h-10 text-sm text-ink"
        >
          <option value="all">Mọi trạng thái</option>
          {allStatuses.map((s) => (
            <option key={s} value={s}>
              {statusLabel[s]}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {pageItems.map((q) => {
          const isExpanded = expanded.has(q.id);
          return (
            <div
              key={q.id}
              className={`bg-surface border border-line rounded-xl overflow-hidden ${
                isExpanded ? 'md:col-span-2 lg:col-span-3' : ''
              }`}
            >
              <div className="p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    <span className="inline-block text-xs px-2.5 py-0.5 rounded-md font-semibold badge-info">
                      {q.topic || 'SQL'}
                    </span>
                    <span
                      className={`inline-block text-xs px-2.5 py-0.5 rounded-md font-semibold ${difficultyStyles[q.difficulty]}`}
                    >
                      {q.difficulty}
                    </span>
                    <span
                      className={`inline-block text-xs px-2.5 py-0.5 rounded-md font-semibold ${statusStyles[q.status]}`}
                    >
                      {statusLabel[q.status]}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleExpand(q.id)}
                    className="btn-secondary min-w-8 min-h-8 rounded-md flex items-center justify-center shrink-0"
                  >
                    <ChevronDown
                      className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    />
                  </button>
                </div>

                <div className="space-y-1">
                  <p className="text-sm text-ink leading-relaxed line-clamp-3">
                    {q.question_text || q.id}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-muted">
                    <code>{q.id}</code>
                    <span>|</span>
                    <span>{q.created_at ? new Date(q.created_at).toLocaleDateString('vi-VN') : '-'}</span>
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="px-5 pb-5 pt-4 border-t border-line grid grid-cols-1 lg:grid-cols-2 gap-5">
                  <DetailBlock
                    icon={<MessageSquare className="w-3.5 h-3.5" />}
                    label="Nội dung đề"
                    content={q.question_text}
                  />
                  <DetailBlock
                    icon={<Database className="w-3.5 h-3.5" />}
                    label="Cấu trúc bảng"
                    content={q.schema_sql}
                  />
                  <DetailBlock
                    icon={<FileCode className="w-3.5 h-3.5" />}
                    label="Dữ liệu mẫu"
                    content={q.seed_sql}
                  />
                  <DetailBlock
                    icon={<CheckCircle className="w-3.5 h-3.5" />}
                    label="Truy vấn đáp án"
                    content={q.answer_sql}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {pageItems.length === 0 && (
        <div className="px-4 py-12 text-center text-muted text-sm">
          Không tìm thấy câu hỏi phù hợp.
        </div>
      )}

      {filtered.length > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted tabular-nums">
            Hiển thị {(currentPage - 1) * itemsPerPage + 1} đến{' '}
            {Math.min(currentPage * itemsPerPage, filtered.length)} trong {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="btn-secondary px-3 min-h-9 rounded-md text-sm disabled:opacity-40"
            >
              Trước
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                type="button"
                data-solid-btn={page === currentPage ? 'true' : undefined}
                onClick={() => setCurrentPage(page)}
                className={`px-3 min-h-9 rounded-md text-sm tabular-nums ${
                  page === currentPage ? 'btn-primary' : 'btn-secondary'
                }`}
              >
                {page}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="btn-secondary px-3 min-h-9 rounded-md text-sm disabled:opacity-40"
            >
              Tiếp
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
