'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Send,
  CheckCircle2,
  AlertCircle,
  Search,
  Database,
  FileCode2,
  Layers,
  Clock,
  RotateCcw,
  ChevronRight,
  ChevronDown,
  Table2,
  Shield,
} from 'lucide-react';
import {
  getWeeklyCurrent,
  getWeeklyQuestions,
  getQuestionDetail,
  getDatasetSchema,
  runSandboxSql,
  submitGradingSql,
} from '../lib/api';
import { useTheme } from './theme-provider';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const DIFF_META: Record<number, { label: string; code: string; badge: string }> = {
  1: {
    label: 'Basic',
    code: 'L1',
    badge: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60',
  },
  2: {
    label: 'Intermediate',
    code: 'L2',
    badge: 'bg-amber-950/60 text-amber-300 border-amber-800/60',
  },
  3: {
    label: 'Advanced',
    code: 'L3',
    badge: 'bg-rose-950/60 text-rose-300 border-rose-800/60',
  },
};

const SQL_SNIPPETS = [
  {
    label: 'SELECT + GROUP BY',
    code: 'SELECT column_name, COUNT(*) AS total\nFROM table_name\nWHERE status = \'active\'\nGROUP BY column_name\nORDER BY total DESC;',
  },
  {
    label: 'CTE (WITH)',
    code: 'WITH summary AS (\n  SELECT customer_id, SUM(total_amount) AS total_spent\n  FROM orders\n  WHERE status = \'completed\'\n  GROUP BY customer_id\n)\nSELECT * FROM summary ORDER BY total_spent DESC;',
  },
  {
    label: 'Window Function',
    code: 'SELECT employee_id, department_id, salary,\n       RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rk\nFROM employees;',
  },
];

export default function LearnerWorkbench({
  onSubmissionComplete,
}: {
  onSubmissionComplete?: () => void;
}) {
  const { theme } = useTheme();
  const [leftMode, setLeftMode] = useState<'problems' | 'schema'>('problems');
  const [weeklyMeta, setWeeklyMeta] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [questionDetail, setQuestionDetail] = useState<any>(null);
  const [schemaInfo, setSchemaInfo] = useState<any>(null);
  const [expandedTable, setExpandedTable] = useState<string | null>('customers');

  // Filters
  const [diffFilter, setDiffFilter] = useState<number | undefined>(undefined);
  const [solvedFilter, setSolvedFilter] = useState<boolean | undefined>(undefined);
  const [searchQ, setSearchQ] = useState('');

  // Editor & Console
  const [sql, setSql] = useState<string>('SELECT * FROM categories LIMIT 10;');
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [output, setOutput] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [consoleTab, setConsoleTab] = useState<'results' | 'tests' | 'policy'>('results');

  const loadQuestions = async () => {
    try {
      const [meta, qList] = await Promise.all([
        getWeeklyCurrent(),
        getWeeklyQuestions({
          difficulty: diffFilter,
          solved: solvedFilter,
          q: searchQ || undefined,
        }),
      ]);
      setWeeklyMeta(meta);
      const items = qList.items || [];
      setQuestions(items);
      if (
        items.length > 0 &&
        (!selectedId || !items.some((x: any) => x.question_id === selectedId))
      ) {
        setSelectedId(items[0].question_id);
      }
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Không tải được bộ đề tuần');
    }
  };

  useEffect(() => {
    loadQuestions();
  }, [diffFilter, solvedFilter]);

  useEffect(() => {
    getDatasetSchema()
      .then(setSchemaInfo)
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setOutput(null);
    setErrorMsg(null);
    getQuestionDetail(selectedId)
      .then((d) => {
        setQuestionDetail(d);
        const firstTable = d.tables_used?.[0] || 'categories';
        setExpandedTable(firstTable);
        setSql(`SELECT *\nFROM ${firstTable}\nLIMIT 10;`);
      })
      .catch((e) => setErrorMsg(e?.response?.data?.error?.message || 'Lỗi tải đề bài'));
  }, [selectedId]);

  const handleRunSandbox = async () => {
    if (!selectedId) return;
    setRunning(true);
    setErrorMsg(null);
    setOutput(null);
    setConsoleTab('results');
    try {
      const res = await runSandboxSql(selectedId, sql);
      setOutput({ mode: 'run', ...res });
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Truy vấn không hợp lệ');
    } finally {
      setRunning(false);
    }
  };

  const handleSubmitGrade = async () => {
    if (!selectedId) return;
    setSubmitting(true);
    setErrorMsg(null);
    setOutput(null);
    try {
      const res = await submitGradingSql(selectedId, sql);
      setOutput({ mode: 'submit', ...res });
      setConsoleTab('results');
      await loadQuestions();
      const updatedDetail = await getQuestionDetail(selectedId);
      setQuestionDetail(updatedDetail);
      if (onSubmissionComplete) onSubmissionComplete();
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Lỗi chấm bài');
    } finally {
      setSubmitting(false);
    }
  };

  const tablesList = schemaInfo?.schema_description?.tables || [];
  const solvedCount = weeklyMeta?.solved_count || 0;
  const totalCount = weeklyMeta?.question_count || questions.length || 20;
  const progressPct = Math.round((solvedCount * 100) / Math.max(totalCount, 1));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
      {/* LEFT RAIL: Problem Set & Database Catalog Navigator */}
      <aside className="lg:col-span-4 bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden flex flex-col h-[860px]">
        {/* Switcher Header */}
        <div className="grid grid-cols-2 border-b border-[#1d283a] bg-[#090d16]">
          <button
            onClick={() => setLeftMode('problems')}
            className={`py-3 px-3 text-xs font-medium flex items-center justify-center gap-2 border-b-2 transition ${
              leftMode === 'problems'
                ? 'border-[#38bdf8] text-white bg-[#0d1321]'
                : 'border-transparent text-[#64748b] hover:text-[#cbd5e1]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Bộ đề tuần ({questions.length})</span>
          </button>
          <button
            onClick={() => setLeftMode('schema')}
            className={`py-3 px-3 text-xs font-medium flex items-center justify-center gap-2 border-b-2 transition ${
              leftMode === 'schema'
                ? 'border-[#38bdf8] text-white bg-[#0d1321]'
                : 'border-transparent text-[#64748b] hover:text-[#cbd5e1]'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Schema DB ({tablesList.length || 13})</span>
          </button>
        </div>

        {leftMode === 'problems' ? (
          <>
            {/* Weekly Set Progress & Filter Strip */}
            <div className="p-3.5 border-b border-[#1d283a] space-y-3 bg-[#0a0f1a]">
              <div>
                <div className="flex items-center justify-between text-[11px] font-mono text-[#94a3b8] mb-1">
                  <span className="truncate max-w-[220px]">
                    {weeklyMeta?.title || 'Tuần #42 — Enterprise SQL'}
                  </span>
                  <span className="text-emerald-400">
                    {solvedCount}/{totalCount} hoàn thành ({progressPct}%)
                  </span>
                </div>
                <div className="w-full h-1.5 bg-[#162032] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-300"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>

              <div className="relative">
                <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-2.5 top-2.5" />
                <input
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadQuestions()}
                  placeholder="Tìm kiếm tiêu đề bài tập..."
                  className="w-full pl-8 pr-3 py-1.5 rounded bg-[#090d16] border border-[#1f2b42] text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-[#38bdf8]"
                />
              </div>

              <div className="flex items-center justify-between gap-1.5">
                <div className="flex items-center gap-1">
                  {[
                    { label: 'All', val: undefined },
                    { label: 'L1 · Basic', val: 1 },
                    { label: 'L2 · Mid', val: 2 },
                    { label: 'L3 · Hard', val: 3 },
                  ].map((b) => (
                    <button
                      key={b.label}
                      onClick={() => setDiffFilter(b.val)}
                      className={`px-2 py-1 rounded text-[11px] font-mono border transition ${
                        diffFilter === b.val
                          ? 'bg-[#17253d] border-[#38bdf8]/60 text-white'
                          : 'bg-[#090d16] border-[#1d283a] text-[#64748b] hover:text-[#94a3b8]'
                      }`}
                    >
                      {b.label}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() =>
                    setSolvedFilter(
                      solvedFilter === undefined ? true : solvedFilter ? false : undefined
                    )
                  }
                  className="px-2 py-1 rounded text-[11px] font-mono border bg-[#090d16] border-[#1d283a] text-[#94a3b8] hover:border-[#2e405e]"
                >
                  {solvedFilter === undefined
                    ? 'Tất cả'
                    : solvedFilter
                    ? 'Đã giải'
                    : 'Chưa giải'}
                </button>
              </div>
            </div>

            {/* Problem Items List */}
            <div className="flex-1 overflow-y-auto divide-y divide-[#162032]">
              {questions.map((q, idx) => {
                const dm = DIFF_META[q.difficulty] || DIFF_META[1];
                const active = q.question_id === selectedId;
                return (
                  <motion.button
                    key={q.question_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.2,
                      delay: Math.min(idx * 0.025, 0.25),
                      ease: [0.23, 1, 0.32, 1],
                    }}
                    onClick={() => setSelectedId(q.question_id)}
                    className={`relative w-full text-left px-3.5 py-3 transition-colors flex items-start gap-3 ${
                      active
                        ? 'bg-[#141f35]'
                        : 'hover:bg-[#101829]'
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="activeProblemBar"
                        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#0284c7] to-emerald-500"
                      />
                    )}
                    <div className="mt-0.5">
                      {q.solved ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                      ) : (
                        <span className="w-4 h-4 rounded-full border border-[#334155] block shrink-0" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-mono text-[11px] text-[#64748b]">
                          #{String(q.position).padStart(2, '0')} · Q-{q.question_id}
                        </span>
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${dm.badge}`}
                        >
                          {dm.code} · {dm.label}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-[#e2e8f0] line-clamp-2 leading-snug">
                        {q.title}
                      </div>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {(q.skills || []).map((sk: any, sIdx: number) => {
                          const label =
                            typeof sk === 'string'
                              ? sk
                              : sk?.code && sk?.name
                              ? `${sk.code} · ${sk.name}`
                              : sk?.name || sk?.code || 'SQL Core';
                          return (
                            <span
                              key={`${q.question_id}-sk-${sIdx}`}
                              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#090d16] text-[#94a3b8] border border-[#1d283a]"
                            >
                              {label}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </div>
          </>
        ) : (
          /* Database Schema Browser */
          <div className="flex-1 overflow-y-auto divide-y divide-[#162032]">
            <div className="p-3 bg-[#0a0f1a] text-[11px] text-[#94a3b8] font-mono">
              Catalog: <span className="text-white">enterprise_db.public</span> · Bấm vào bảng để xem cột hoặc chèn truy vấn mẫu.
            </div>
            {tablesList.map((tb: any) => {
              const isExp = expandedTable === tb.table;
              const isUsedInQ = (questionDetail?.tables_used || []).includes(tb.table);
              return (
                <div key={tb.table} className="bg-[#0d1321]">
                  <div
                    onClick={() => setExpandedTable(isExp ? null : tb.table)}
                    className="w-full px-3.5 py-2.5 flex items-center justify-between cursor-pointer hover:bg-[#131c2e] transition"
                  >
                    <div className="flex items-center gap-2">
                      {isExp ? (
                        <ChevronDown className="w-3.5 h-3.5 text-[#38bdf8]" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-[#64748b]" />
                      )}
                      <Table2 className="w-3.5 h-3.5 text-[#94a3b8]" />
                      <span className="font-mono text-xs font-medium text-white">
                        {tb.table}
                      </span>
                      {isUsedInQ && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-950/80 text-sky-300 border border-sky-800/60">
                          Đang dùng
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-[#64748b]">
                      {(tb.columns || []).length} cols
                    </span>
                  </div>

                  <AnimatePresence initial={false}>
                    {isExp && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
                        className="bg-[#080c14] px-4 py-2.5 border-t border-[#162032] space-y-1.5 overflow-hidden"
                      >
                        <div className="flex justify-end mb-1">
                          <button
                            onClick={() =>
                              setSql(`SELECT *\nFROM ${tb.table}\nLIMIT 20;`)
                            }
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#162238] hover:bg-[#1e2f4d] text-[#38bdf8] border border-[#263a5e]"
                          >
                            Chèn SELECT * FROM {tb.table}
                          </button>
                        </div>
                        {(tb.columns || []).map((c: any) => (
                          <div
                            key={c.name}
                            className="flex items-center justify-between text-[11px] font-mono py-0.5"
                          >
                            <div className="flex items-center gap-1.5">
                              <span className="text-[#cbd5e1]">{c.name}</span>
                              {c.primary_key && (
                                <span className="text-[9px] px-1 rounded bg-amber-950/70 text-amber-300 border border-amber-800/50">
                                  PK
                                </span>
                              )}
                              {!c.nullable && !c.primary_key && (
                                <span className="text-[9px] text-[#475569]">NOT NULL</span>
                              )}
                            </div>
                            <span className="text-[#64748b]">{c.postgres_type}</span>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        )}
      </aside>

      {/* RIGHT MAIN WORKSPACE: Problem Specification + Studio SQL Editor + Output Console */}
      <section className="lg:col-span-8 flex flex-col gap-4">
        {/* Upper Card: Problem Specification */}
        {questionDetail ? (
          <motion.div
            key={questionDetail.question_id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, ease: [0.23, 1, 0.32, 1] }}
            className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden card-interactive"
          >
            {/* Metadata Header Bar */}
            <div className="px-5 py-3 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2.5 text-xs font-mono">
                <span className="text-[#64748b]">
                  PROBLEM #{questionDetail.question_id}
                </span>
                <span className="text-[#334155]">/</span>
                <span
                  className={`px-2 py-0.5 rounded border text-[11px] ${
                    DIFF_META[questionDetail.difficulty]?.badge || ''
                  }`}
                >
                  {DIFF_META[questionDetail.difficulty]?.code} ·{' '}
                  {DIFF_META[questionDetail.difficulty]?.label}
                </span>
                <span className="px-2 py-0.5 rounded bg-[#131c2e] border border-[#22304a] text-[#94a3b8] text-[11px]">
                  {questionDetail.compare_mode === 'ordered'
                    ? 'ORDER SENSITIVE'
                    : 'UNORDERED SET'}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono text-[#94a3b8]">
                <span>Lượt nộp: {questionDetail.attempt_count || 0}</span>
                {questionDetail.solved && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-300">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    SOLVED
                  </span>
                )}
              </div>
            </div>

            {/* Problem Content */}
            <div className="p-5 space-y-4">
              <h1 className="text-base font-semibold text-white tracking-tight">
                {questionDetail.title}
              </h1>

              <div className="p-4 rounded-md bg-[#080c14] border border-[#182235] text-[13px] text-[#cbd5e1] leading-relaxed whitespace-pre-line">
                {questionDetail.question}
              </div>

              {/* Schema & Tables Strip */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-mono text-[#64748b] mr-1">
                    Bảng dữ liệu yêu cầu:
                  </span>
                  {(questionDetail.tables_used || []).map((tb: string) => (
                    <button
                      key={tb}
                      onClick={() => {
                        setLeftMode('schema');
                        setExpandedTable(tb);
                      }}
                      className="px-2.5 py-1 rounded bg-[#111a2e] hover:bg-[#18243f] text-[#38bdf8] border border-[#223459] font-mono text-xs flex items-center gap-1.5 transition"
                    >
                      <Table2 className="w-3 h-3" />
                      <span>public.{tb}</span>
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-mono text-[#64748b]">Mẫu cú pháp:</span>
                  {SQL_SNIPPETS.map((sn) => (
                    <button
                      key={sn.label}
                      onClick={() => setSql(sn.code)}
                      className="px-2 py-1 rounded bg-[#111827] hover:bg-[#1b263b] text-[#94a3b8] hover:text-white border border-[#1f2b42] text-[11px] font-mono transition"
                    >
                      {sn.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg p-8 text-center text-xs font-mono text-[#64748b]">
            Đang nạp đặc tả bài toán...
          </div>
        )}

        {/* Lower Card: Studio SQL Editor & Multi-Tab Execution Console */}
        <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
          {/* Editor Action Bar */}
          <div className="px-4 py-2.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
              <FileCode2 className="w-4 h-4 text-[#38bdf8]" />
              <span className="text-white font-medium">query.sql</span>
              <span className="text-[#475569]">·</span>
              <span className="text-[11px] text-[#64748b]">PostgreSQL 17 Dialect</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const firstTable = questionDetail?.tables_used?.[0] || 'categories';
                  setSql(`SELECT *\nFROM ${firstTable}\nLIMIT 10;`);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-[#111827] hover:bg-[#1b263b] border border-[#22304a] text-[#94a3b8] hover:text-white text-xs transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Khôi phục</span>
              </button>

              <button
                onClick={handleRunSandbox}
                disabled={running || submitting}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-[#162238] hover:bg-[#1f304d] border border-[#293f66] text-white text-xs font-medium transition disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 text-[#38bdf8]" />
                <span>{running ? 'Đang thực thi...' : 'Chạy thử SQL'}</span>
              </button>

              <button
                onClick={handleSubmitGrade}
                disabled={running || submitting}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-medium transition disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{submitting ? 'Đang chấm...' : 'Nộp bài chấm điểm'}</span>
              </button>
            </div>
          </div>

          {/* Monaco Code Editor */}
          <div className="h-[260px] border-b border-[#1d283a]">
            <MonacoEditor
              height="260px"
              defaultLanguage="sql"
              theme={theme === 'light' ? 'light' : 'vs-dark'}
              value={sql}
              onChange={(val) => setSql(val || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineHeight: 21,
                fontFamily: 'JetBrains Mono, Menlo, monospace',
                scrollBeyondLastLine: false,
                padding: { top: 14, bottom: 14 },
                renderLineHighlight: 'all',
              }}
            />
          </div>

          {/* Console Tabs Header */}
          <div className="px-4 bg-[#090d16] border-b border-[#1d283a] flex items-center justify-between">
            <div className="flex items-center gap-4">
              {[
                { id: 'results', label: 'Bảng kết quả (Result Set)' },
                {
                  id: 'tests',
                  label: `Kiểm định Test Cases (${output?.test_cases?.length || 1})`,
                },
                { id: 'policy', label: 'Cấu hình Sandbox' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setConsoleTab(t.id as any)}
                  className={`py-2.5 text-xs font-medium border-b-2 transition ${
                    consoleTab === t.id
                      ? 'border-[#38bdf8] text-white'
                      : 'border-transparent text-[#64748b] hover:text-[#94a3b8]'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {output && (
              <div className="flex items-center gap-3 text-[11px] font-mono text-[#94a3b8]">
                <span>Rows: {output.row_count ?? 0}</span>
                {output.runtime_ms !== undefined && (
                  <span className="flex items-center gap-1 text-emerald-400">
                    <Clock className="w-3 h-3" />
                    {output.runtime_ms} ms
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Console Body */}
          <div className="p-4 bg-[#070b12] min-h-[210px]">
            {errorMsg && (
              <div className="p-3.5 rounded bg-red-950/30 border border-red-900/60 flex items-start gap-2.5 text-red-300 text-xs font-mono">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-red-200 mb-0.5">
                    SQL Execution Error
                  </div>
                  <div>{errorMsg}</div>
                </div>
              </div>
            )}

            {!errorMsg && consoleTab === 'results' && (
              <>
                {output?.mode === 'submit' && (
                  <div
                    className={`mb-3 p-3 rounded border flex flex-wrap items-center justify-between gap-2 ${
                      output.passed
                        ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-200'
                        : 'bg-rose-950/30 border-rose-800/60 text-rose-200'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-xs">
                      {output.passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-rose-400" />
                      )}
                      <span className="font-semibold">
                        {output.passed
                          ? 'ACCEPTED — Kết quả khớp hoàn toàn với bộ Test Case chuẩn'
                          : `WRONG ANSWER — ${output.error || 'Chưa khớp kết quả chuẩn'}`}
                      </span>
                    </div>
                    <div className="font-mono text-xs">
                      Score: <strong>{output.score}/100</strong> · Latency:{' '}
                      <strong>{output.runtime_ms} ms</strong>
                    </div>
                  </div>
                )}

                {output?.columns && output.columns.length > 0 ? (
                  <div className="overflow-x-auto max-h-64 border border-[#1a2436] rounded">
                    <table className="w-full text-left border-collapse text-xs font-mono">
                      <thead>
                        <tr className="bg-[#0e1525] border-b border-[#1a2436] text-[#94a3b8]">
                          <th className="px-2.5 py-2 w-10 text-center border-r border-[#1a2436] text-[#475569]">
                            #
                          </th>
                          {output.columns.map((c: string) => (
                            <th
                              key={c}
                              className="px-3 py-2 whitespace-nowrap border-r border-[#1a2436] last:border-r-0 text-[#cbd5e1]"
                            >
                              {c}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#141d2e]">
                        {(output.rows || []).slice(0, 40).map((r: any, idx: number) => (
                          <tr key={idx} className="hover:bg-[#11192b]">
                            <td className="px-2.5 py-1.5 text-center border-r border-[#141d2e] text-[#475569]">
                              {idx + 1}
                            </td>
                            {output.columns.map((c: string) => (
                              <td
                                key={c}
                                className="px-3 py-1.5 text-[#e2e8f0] whitespace-nowrap border-r border-[#141d2e] last:border-r-0"
                              >
                                {r[c] === null || r[c] === undefined ? (
                                  <span className="text-[#475569] italic">null</span>
                                ) : (
                                  String(r[c])
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="py-10 text-center text-xs font-mono text-[#64748b]">
                    Chưa có dữ liệu đầu ra. Nhấn &quot;Chạy thử SQL&quot; hoặc &quot;Nộp bài chấm điểm&quot; để thực thi truy vấn.
                  </div>
                )}
              </>
            )}

            {!errorMsg && consoleTab === 'tests' && (
              <div className="space-y-2">
                {output?.test_cases ? (
                  output.test_cases.map((tc: any) => (
                    <div
                      key={tc.test_id}
                      className="p-3 rounded bg-[#0d1321] border border-[#1d283a] flex items-center justify-between text-xs font-mono"
                    >
                      <div className="flex items-center gap-2.5">
                        {tc.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-rose-400" />
                        )}
                        <span className="text-white">
                          Dataset: {tc.dataset_ref} ({tc.type})
                        </span>
                      </div>
                      <div className="text-[#94a3b8]">
                        Expected rows: <strong className="text-white">{tc.expected_rows}</strong> ·
                        Actual rows: <strong className="text-white">{tc.actual_rows}</strong>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-xs font-mono text-[#64748b]">
                    Nhấn &quot;Nộp bài chấm điểm&quot; để xem chi tiết đối chiếu từng Test Case.
                  </div>
                )}
              </div>
            )}

            {!errorMsg && consoleTab === 'policy' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-[#0d1321] border border-[#1d283a]">
                  <div className="text-[#64748b] mb-1 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-[#38bdf8]" />
                    ROLE ISOLATION
                  </div>
                  <div className="text-white">sqlarena_ai_ro @ enterprise_db</div>
                  <div className="text-[11px] text-[#64748b] mt-1">
                    Quyền SELECT thuần túy, chặn tuyệt đối ghi/xóa bảng hệ thống.
                  </div>
                </div>
                <div className="p-3 rounded bg-[#0d1321] border border-[#1d283a]">
                  <div className="text-[#64748b] mb-1">TRANSACTION GUARD</div>
                  <div className="text-white">SET LOCAL TRANSACTION READ ONLY</div>
                  <div className="text-[11px] text-[#64748b] mt-1">
                    statement_timeout = 10000ms · max_rows = 100,000
                  </div>
                </div>
                <div className="p-3 rounded bg-[#0d1321] border border-[#1d283a]">
                  <div className="text-[#64748b] mb-1">AST / REGEX FILTER</div>
                  <div className="text-white">Single-Statement SELECT / WITH</div>
                  <div className="text-[11px] text-[#64748b] mt-1">
                    Chặn DDL, DML, COPY, GRANT, VACUUM và multi-statement.
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
