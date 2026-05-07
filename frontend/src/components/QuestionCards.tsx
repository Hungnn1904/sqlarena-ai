'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuestions } from '@/lib/hooks';
import { Search, ChevronDown, Database, FileCode, MessageSquare, CheckCircle } from 'lucide-react';

type Difficulty = 'easy' | 'medium' | 'hard';
type Status = 'pending_review' | 'approved' | 'rejected' | 'active' | 'archived';

const difficultyStyles: Record<Difficulty, string> = {
  easy: 'bg-[rgba(0,229,160,0.1)] text-[#00e5a0] border border-[#00e5a0]',
  medium: 'bg-[rgba(255,184,48,0.1)] text-[#ffb830] border border-[#ffb830]',
  hard: 'bg-[rgba(255,77,109,0.1)] text-[#ff4d6d] border border-[#ff4d6d]',
};

const statusStyles: Record<Status, string> = {
  pending_review: 'bg-[rgba(255,184,48,0.1)] text-[#ffb830]',
  approved: 'bg-[rgba(0,229,160,0.1)] text-[#00e5a0]',
  rejected: 'bg-[rgba(255,77,109,0.1)] text-[#ff4d6d]',
  active: 'bg-[rgba(0,212,255,0.1)] text-[#00d4ff]',
  archived: 'bg-[rgba(167,139,250,0.1)] text-[#a78bfa]',
};

const statusLabel: Record<Status, string> = {
  pending_review: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  active: 'Active',
  archived: 'Archived',
};

interface DetailBlockProps {
  icon: React.ReactNode;
  label: string;
  content: string | undefined;
  lang?: string;
}

function DetailBlock({ icon, label, content, lang }: DetailBlockProps) {
  if (!content) return null;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[0.7rem] font-mono uppercase tracking-[0.1em] text-[#5a7298]">
        {icon}
        {label}
      </div>
      <pre className="bg-[#080c14] border border-[#1e2d45] rounded-lg p-3 overflow-auto text-[0.78rem] leading-[1.6] font-mono text-[#a8c4e8] max-h-[280px]">
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
      const matchesSearch =
        (q.question_text?.toLowerCase() ?? '').includes(s) ||
        q.id.toLowerCase().includes(s) ||
        q.domain.toLowerCase().includes(s) ||
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-[#0d1320] border border-[#1e2d45] rounded-xl p-5 h-40 animate-pulse" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 text-[#ff4d6d] text-sm">
        Failed to load questions. Please try again later.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-wrap gap-3 items-center"
      >
        <div className="relative flex-1 min-w-[240px]">
          <input
            type="text"
            placeholder="Search questions, ID, domain..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#0d1320] border border-[#1e2d45] rounded-lg px-4 py-2.5 pl-10 text-sm text-[#e2eaf6] placeholder-[#5a7298] focus:outline-none focus:border-[#00d4ff] transition-colors"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#5a7298]" />
        </div>

        <select
          value={filterTopic}
          onChange={(e) => setFilterTopic(e.target.value)}
          className="bg-[#0d1320] border border-[#1e2d45] rounded-lg px-3 py-2.5 text-sm text-[#e2eaf6] focus:outline-none focus:border-[#00d4ff]"
        >
          <option value="all">All Topics</option>
          {allTopics.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        <select
          value={filterDifficulty}
          onChange={(e) => setFilterDifficulty(e.target.value as Difficulty | 'all')}
          className="bg-[#0d1320] border border-[#1e2d45] rounded-lg px-3 py-2.5 text-sm text-[#e2eaf6] focus:outline-none focus:border-[#00d4ff]"
        >
          <option value="all">All Difficulties</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as Status | 'all')}
          className="bg-[#0d1320] border border-[#1e2d45] rounded-lg px-3 py-2.5 text-sm text-[#e2eaf6] focus:outline-none focus:border-[#00d4ff]"
        >
          <option value="all">All Statuses</option>
          {allStatuses.map((s) => (
            <option key={s} value={s}>{statusLabel[s]}</option>
          ))}
        </select>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <AnimatePresence mode="popLayout">
          {pageItems.map((q, index) => {
            const isExpanded = expanded.has(q.id);
            return (
              <motion.div
                key={q.id}
                layout
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.25, delay: index * 0.04 }}
                className={`bg-[#0d1320] border border-[#1e2d45] rounded-xl overflow-hidden transition-colors hover:border-[#243550] ${
                  isExpanded ? 'md:col-span-2 lg:col-span-3' : ''
                }`}
              >
                <div className="p-5 space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-wrap gap-2">
                      <span className="inline-block font-mono text-[0.65rem] px-2 py-0.5 rounded font-semibold uppercase tracking-[0.05em] bg-[rgba(0,212,255,0.1)] text-[#00d4ff] border border-[#00d4ff]/30">
                        {q.topic || 'SQL'}
                      </span>
                      <span
                        className={`inline-block font-mono text-[0.65rem] px-2 py-0.5 rounded font-semibold uppercase tracking-[0.05em] ${difficultyStyles[q.difficulty]}`}
                      >
                        {q.difficulty}
                      </span>
                      <span
                        className={`inline-block font-mono text-[0.65rem] px-2 py-0.5 rounded font-semibold uppercase tracking-[0.05em] ${statusStyles[q.status]}`}
                      >
                        {statusLabel[q.status]}
                      </span>
                    </div>
                    <button
                      onClick={() => toggleExpand(q.id)}
                      className="text-[#5a7298] hover:text-[#00d4ff] transition-colors shrink-0"
                    >
                      <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
                        <ChevronDown className="w-4 h-4" />
                      </motion.div>
                    </button>
                  </div>

                  <div className="space-y-1">
                    <p className="text-sm text-[#e2eaf6] leading-relaxed line-clamp-3">
                      {q.question_text || q.id}
                    </p>
                    <div className="flex items-center gap-2 text-[0.7rem] text-[#5a7298] font-mono">
                      <span>{q.id}</span>
                      <span className="text-[#1e2d45]">|</span>
                      <span>{q.domain}</span>
                      <span className="text-[#1e2d45]">|</span>
                      <span>{q.created_at ? new Date(q.created_at).toLocaleDateString('vi-VN') : '—'}</span>
                    </div>
                  </div>
                </div>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="overflow-hidden"
                    >
                      <div className="px-5 pb-5 pt-0 space-y-5 border-t border-[#1e2d45]">
                        <div className="pt-4 grid grid-cols-1 lg:grid-cols-2 gap-5">
                          <DetailBlock
                            icon={<MessageSquare className="w-3.5 h-3.5" />}
                            label="Question Text"
                            content={q.question_text}
                          />
                          <DetailBlock
                            icon={<Database className="w-3.5 h-3.5" />}
                            label="Schema SQL"
                            content={q.schema_sql}
                          />
                          <DetailBlock
                            icon={<FileCode className="w-3.5 h-3.5" />}
                            label="Seed Data"
                            content={q.seed_sql}
                          />
                          <DetailBlock
                            icon={<CheckCircle className="w-3.5 h-3.5" />}
                            label="Answer Query"
                            content={q.answer_sql}
                          />
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {pageItems.length === 0 && (
        <div className="px-4 py-12 text-center text-[#5a7298] text-sm">
          No questions found matching your filters.
        </div>
      )}

      {filtered.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-between"
        >
          <span className="text-[0.75rem] text-[#5a7298]">
            Showing {(currentPage - 1) * itemsPerPage + 1} -{' '}
            {Math.min(currentPage * itemsPerPage, filtered.length)} of {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 rounded-md text-sm text-[#5a7298] hover:text-[#e2eaf6] hover:bg-[#111827] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Prev
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`px-3 py-1.5 rounded-md text-sm font-mono transition-colors ${
                  page === currentPage
                    ? 'bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/30'
                    : 'text-[#5a7298] hover:text-[#e2eaf6] hover:bg-[#111827]'
                }`}
              >
                {page}
              </button>
            ))}
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 rounded-md text-sm text-[#5a7298] hover:text-[#e2eaf6] hover:bg-[#111827] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
