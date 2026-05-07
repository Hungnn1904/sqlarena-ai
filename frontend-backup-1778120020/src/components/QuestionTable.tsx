'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Question, Difficulty, QuestionStatus, Topic } from './types';

interface QuestionTableProps {
  questions: Question[];
  itemsPerPage?: number;
}

const difficultyStyles: Record<Difficulty, string> = {
  easy: 'bg-[rgba(0,229,160,0.1)] text-[#00e5a0] border border-[#00e5a0]',
  medium: 'bg-[rgba(255,184,48,0.1)] text-[#ffb830] border border-[#ffb830]',
  hard: 'bg-[rgba(255,77,109,0.1)] text-[#ff4d6d] border border-[#ff4d6d]',
};

const statusStyles: Record<QuestionStatus, string> = {
  pending_review: 'bg-[rgba(255,184,48,0.1)] text-[#ffb830]',
  approved: 'bg-[rgba(0,229,160,0.1)] text-[#00e5a0]',
  rejected: 'bg-[rgba(255,77,109,0.1)] text-[#ff4d6d]',
  active: 'bg-[rgba(0,212,255,0.1)] text-[#00d4ff]',
};

const statusLabel: Record<QuestionStatus, string> = {
  pending_review: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  active: 'Active',
};

export default function QuestionTable({ questions, itemsPerPage = 10 }: QuestionTableProps) {
  const [search, setSearch] = React.useState('');
  const [currentPage, setCurrentPage] = React.useState(1);
  const [filterDifficulty, setFilterDifficulty] = React.useState<Difficulty | 'all'>('all');
  const [filterTopic, setFilterTopic] = React.useState<Topic | 'all'>('all');
  const [filterStatus, setFilterStatus] = React.useState<QuestionStatus | 'all'>('all');

  const filtered = React.useMemo(() => {
    return questions.filter((q) => {
      const matchesSearch =
        q.questionText.toLowerCase().includes(search.toLowerCase()) ||
        q.id.toLowerCase().includes(search.toLowerCase()) ||
        q.domain.toLowerCase().includes(search.toLowerCase());
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

  const allTopics = Array.from(new Set(questions.map((q) => q.topic))).sort() as Topic[];
  const allStatuses = Array.from(new Set(questions.map((q) => q.status))).sort() as QuestionStatus[];

  return (
    <div className="space-y-4">
      {/* Search & Filters */}
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
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#5a7298]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <select
          value={filterTopic}
          onChange={(e) => setFilterTopic(e.target.value as Topic | 'all')}
          className="bg-[#0d1320] border border-[#1e2d45] rounded-lg px-3 py-2.5 text-sm text-[#e2eaf6] focus:outline-none focus:border-[#00d4ff]"
        >
          <option value="all">All Topics</option>
          {allTopics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
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
          onChange={(e) => setFilterStatus(e.target.value as QuestionStatus | 'all')}
          className="bg-[#0d1320] border border-[#1e2d45] rounded-lg px-3 py-2.5 text-sm text-[#e2eaf6] focus:outline-none focus:border-[#00d4ff]"
        >
          <option value="all">All Statuses</option>
          {allStatuses.map((s) => (
            <option key={s} value={s}>
              {statusLabel[s]}
            </option>
          ))}
        </select>
      </motion.div>

      {/* Table */}
      <div className="overflow-x-auto border border-[#1e2d45] rounded-lg">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#111827] border-b border-[#1e2d45]">
              {['ID', 'Topic', 'Difficulty', 'Domain', 'Status', 'Created', ''].map((h) => (
                <th
                  key={h}
                  className="text-left px-4 py-3 font-mono text-[0.7rem] uppercase tracking-[0.1em] text-[#5a7298] whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <AnimatePresence mode="popLayout">
              {pageItems.map((q, index) => (
                <motion.tr
                  key={q.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2, delay: index * 0.03 }}
                  className="border-b border-[#1e2d45] last:border-b-0 hover:bg-[#111827]/60 transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-[#8ba3c7] whitespace-nowrap">
                    {q.id}
                  </td>
                  <td className="px-4 py-3 text-[#e2eaf6] whitespace-nowrap">{q.topic}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block font-mono text-[0.65rem] px-2 py-0.5 rounded font-semibold uppercase tracking-[0.05em] ${
                        difficultyStyles[q.difficulty]
                      }`}
                    >
                      {q.difficulty}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#8ba3c7]">{q.domain}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block font-mono text-[0.65rem] px-2 py-0.5 rounded font-semibold uppercase tracking-[0.05em] ${
                        statusStyles[q.status]
                      }`}
                    >
                      {statusLabel[q.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#5a7298] whitespace-nowrap">
                    {new Date(q.createdAt).toLocaleDateString('vi-VN')}
                  </td>
                  <td className="px-4 py-3">
                    <button className="text-[#5a7298] hover:text-[#00d4ff] transition-colors">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>

        {pageItems.length === 0 && (
          <div className="px-4 py-12 text-center text-[#5a7298] text-sm">
            No questions found matching your filters.
          </div>
        )}
      </div>

      {/* Pagination */}
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
