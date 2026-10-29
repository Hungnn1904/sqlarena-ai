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
  getQuestionSubmissions,
  getDatasetSchema,
  runSandboxSql,
  explainSandboxSql,
  askAiSqlCoach,
  submitGradingSql,
} from '../lib/api';
import { useTheme } from './theme-provider';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const DIFF_META: Record<number, { label: string; code: string; badge: string }> = {
  1: {
    label: 'Dễ',
    code: 'Dễ',
    badge: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60',
  },
  2: {
    label: 'Trung bình',
    code: 'TB',
    badge: 'bg-amber-950/60 text-amber-300 border-amber-800/60',
  },
  3: {
    label: 'Khó',
    code: 'Khó',
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
  const [skillFilter, setSkillFilter] = useState<number | undefined>(undefined);
  const [solvedFilter, setSolvedFilter] = useState<boolean | undefined>(undefined);
  const [searchQ, setSearchQ] = useState('');
  const [hintStep, setHintStep] = useState<number>(0);

  // Editor & Console
  const [sql, setSql] = useState<string>('SELECT * FROM categories LIMIT 10;');
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [output, setOutput] = useState<any>(null);
  const [explainData, setExplainData] = useState<any>(null);
  const [aiCoachData, setAiCoachData] = useState<any>(null);
  const [aiPrompt, setAiPrompt] = useState<string>('');
  const [showInterviewAns, setShowInterviewAns] = useState(false);
  const [qSubs, setQSubs] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [consoleTab, setConsoleTab] = useState<
    'results' | 'tests' | 'explain' | 'ai_coach' | 'history' | 'policy'
  >('results');

  const loadQuestions = async () => {
    try {
      const [meta, qList] = await Promise.all([
        getWeeklyCurrent(),
        getWeeklyQuestions({
          difficulty: diffFilter,
          skill_id: skillFilter,
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
  }, [diffFilter, skillFilter, solvedFilter]);

  useEffect(() => {
    getDatasetSchema()
      .then(setSchemaInfo)
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setOutput(null);
    setExplainData(null);
    setAiCoachData(null);
    setShowInterviewAns(false);
    setErrorMsg(null);
    setHintStep(0);
    getQuestionDetail(selectedId)
      .then((d) => {
        setQuestionDetail(d);
        const firstTable = d.tables_used?.[0] || 'categories';
        setExpandedTable(firstTable);
        setSql(`SELECT *\nFROM ${firstTable}\nLIMIT 10;`);
      })
      .catch((e) => setErrorMsg(e?.response?.data?.error?.message || 'Lỗi tải đề bài'));
    getQuestionSubmissions(selectedId)
      .then((r) => setQSubs(r?.items || []))
      .catch(() => setQSubs([]));
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

  const handlePreviewTable = async (tableName: string) => {
    const qId = selectedId || questions[0]?.question_id || 1;
    setRunning(true);
    setErrorMsg(null);
    setConsoleTab('results');
    try {
      const res = await runSandboxSql(qId, "SELECT * FROM " + tableName + " LIMIT 5;");
      setOutput({ mode: 'run', ...res });
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Không xem trước được bảng');
    } finally {
      setRunning(false);
    }
  };

  const handleExplain = async () => {
    if (!selectedId) return;
    setRunning(true);
    setErrorMsg(null);
    setConsoleTab('explain');
    try {
      const res = await explainSandboxSql(selectedId, sql);
      setExplainData(res);
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Không phân tích được Explain Plan');
    } finally {
      setRunning(false);
    }
  };

  const handleAiCoach = async (mode: 'review' | 'nl2sql' | 'interview' = 'review') => {
    if (!selectedId) return;
    setRunning(true);
    setErrorMsg(null);
    setShowInterviewAns(false);
    setConsoleTab('ai_coach');
    try {
      const res = await askAiSqlCoach({
        question_id: selectedId,
        sql,
        mode,
        prompt: aiPrompt || undefined,
      });
      setAiCoachData(res);
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Không gọi được AI SQL Coach');
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
      const [updatedDetail, subsRes] = await Promise.all([
        getQuestionDetail(selectedId),
        getQuestionSubmissions(selectedId).catch(() => ({ items: [] })),
      ]);
      setQuestionDetail(updatedDetail);
      setQSubs(subsRes?.items || []);
      if (onSubmissionComplete) onSubmissionComplete();
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Lỗi chấm bài');
    } finally {
      setSubmitting(false);
    }
  };

  const tablesList = schemaInfo?.tables || schemaInfo?.schema_description?.tables || [];
  const currentIdx = questions.findIndex((q) => q.question_id === selectedId);
  const prevQuestionId = currentIdx > 0 ? questions[currentIdx - 1]?.question_id : null;
  const nextQuestionId =
    currentIdx >= 0 && currentIdx < questions.length - 1
      ? questions[currentIdx + 1]?.question_id
      : null;
  const solvedCount = weeklyMeta?.solved_count || 0;
  const totalCount = weeklyMeta?.question_count || questions.length || 20;
  const progressPct = Math.round((solvedCount * 100) / Math.max(totalCount, 1));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2 pb-1">
        <div>
          <div className="text-[11px] font-bold tracking-[0.15em] uppercase text-[var(--copper)]">
            KHÔNG GIAN HỌC TẬP
          </div>
          <h2 className="text-2xl font-bold text-[var(--ink)] mt-0.5">
            Luyện tập <span className="editorial-serif text-[var(--green)]">truy vấn SQL.</span>
          </h2>
        </div>
        <span className="text-xs font-mono text-[#64748b]">
          {weeklyMeta?.title || 'Tuần #42'} · {solvedCount}/{totalCount} câu ({progressPct}%)
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
      {/* LEFT RAIL: Problem Set & Database Catalog Navigator */}
      <aside className="lg:col-span-4 bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden flex flex-col h-[840px]">
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
            <span>Danh sách đề ({questions.length})</span>
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
            <span>Schema ({tablesList.length || 13})</span>
          </button>
        </div>

        {leftMode === 'problems' ? (
          <>
            {/* Weekly Set Progress & Filter Strip */}
            <div className="p-3.5 border-b border-[#1d283a] space-y-2.5 bg-[#0a0f1a]">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-2.5 top-2.5" />
                <input
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadQuestions()}
                  placeholder="Tìm bài tập..."
                  className="w-full pl-8 pr-3 py-1.5 rounded bg-[#090d16] border border-[#1f2b42] text-xs text-white placeholder-[#64748b] focus:outline-none focus:border-[#38bdf8]"
                />
              </div>

              <div className="flex items-center justify-between gap-1.5">
                <div className="flex items-center gap-1">
                  {[
                    { label: 'Tất cả', val: undefined },
                    { label: 'Dễ', val: 1 },
                    { label: 'TB', val: 2 },
                    { label: 'Khó', val: 3 },
                  ].map((b) => (
                    <button
                      key={b.label}
                      onClick={() => setDiffFilter(b.val)}
                      className={`px-2.5 py-1 rounded text-[11px] font-mono border transition ${
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

              <select
                value={skillFilter ?? ''}
                onChange={(e) =>
                  setSkillFilter(e.target.value ? Number(e.target.value) : undefined)
                }
                className="w-full px-2.5 py-1.5 rounded bg-[#090d16] border border-[#1f2b42] text-xs font-mono text-[#cbd5e1] focus:outline-none focus:border-[#38bdf8]"
              >
                <option value="">Mọi kỹ năng (S1–S6)</option>
                <option value="1">S1 · SELECT</option>
                <option value="2">S2 · JOIN</option>
                <option value="3">S3 · GROUP BY</option>
                <option value="4">S4 · Subquery/CTE</option>
                <option value="5">S5 · Window</option>
                <option value="6">S6 · NULL/Edge</option>
              </select>
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
                          #{String(q.position || idx + 1).padStart(2, '0')}
                        </span>
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${dm.badge}`}
                        >
                          {dm.label}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-[#e2e8f0] line-clamp-1 leading-snug">
                        {q.title}
                      </div>
                      {(q.skills || []).slice(0, 1).map((sk: any, sIdx: number) => {
                        const label =
                          typeof sk === 'string'
                            ? sk
                            : sk?.name || sk?.code || 'SQL Core';
                        return (
                          <div key={`${q.question_id}-sk-${sIdx}`} className="mt-1">
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#090d16] text-[#94a3b8] border border-[#1d283a]">
                              {label}
                            </span>
                          </div>
                        );
                      })}
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
                        <div className="flex justify-end gap-1.5 mb-1">
                          <button
                            onClick={() => handlePreviewTable(tb.table)}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#142922] hover:bg-[#1b382e] text-emerald-300 border border-emerald-800/60"
                          >
                            Xem 5 dòng
                          </button>
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
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="text-[#64748b]">
                  #{String(questionDetail.position || questionDetail.question_id).padStart(2, '0')}
                </span>
                <span
                  className={`px-2 py-0.5 rounded border text-[11px] ${
                    DIFF_META[questionDetail.difficulty]?.badge || ''
                  }`}
                >
                  {DIFF_META[questionDetail.difficulty]?.label}
                </span>
                {(questionDetail.skills || []).slice(0, 1).map((sk: any, idx: number) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded bg-[#131c2e] border border-[#22304a] text-[#94a3b8] text-[11px]"
                  >
                    {typeof sk === 'string' ? sk : sk?.name || sk?.code || 'SQL'}
                  </span>
                ))}
              </div>

              <div className="flex items-center gap-2">
                {questionDetail.solved && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Đã giải
                  </span>
                )}
                <button
                  onClick={() => setHintStep((prev) => (prev >= 3 ? 0 : prev + 1))}
                  className="px-2.5 py-1 rounded bg-amber-950/50 hover:bg-amber-900/60 border border-amber-800/60 text-amber-300 text-xs font-mono transition"
                >
                  💡 Gợi ý ({hintStep}/3)
                </button>
                <button
                  onClick={() => prevQuestionId && setSelectedId(prevQuestionId)}
                  disabled={!prevQuestionId}
                  className="px-2.5 py-1 rounded bg-[#111827] hover:bg-[#1b263b] border border-[#1f2b42] text-xs font-mono text-[#cbd5e1] disabled:opacity-40 transition"
                >
                  ← Bài trước
                </button>
                <button
                  onClick={() => nextQuestionId && setSelectedId(nextQuestionId)}
                  disabled={!nextQuestionId}
                  className="px-2.5 py-1 rounded bg-[#111827] hover:bg-[#1b263b] border border-[#1f2b42] text-xs font-mono text-[#cbd5e1] disabled:opacity-40 transition"
                >
                  Bài tiếp →
                </button>
              </div>
            </div>

            {/* Problem Content */}
            <div className="p-5 space-y-3.5">
              <h1 className="text-base font-semibold text-white tracking-tight">
                {questionDetail.title}
              </h1>

              <div className="p-4 rounded-md bg-[#080c14] border border-[#182235] text-[13px] text-[#cbd5e1] leading-relaxed whitespace-pre-line">
                {questionDetail.question}
              </div>

              {hintStep > 0 && (
                <div className="p-3.5 rounded-md bg-amber-950/25 border border-amber-800/50 space-y-2 text-xs font-mono text-amber-200">
                  {hintStep >= 1 && (
                    <div>
                      <strong className="text-amber-300">Bước 1 (Bảng &amp; Khóa):</strong>{' '}
                      Bảng sử dụng: {(questionDetail.tables_used || []).join(', ') || 'N/A'}.{' '}
                      {tablesList
                        .filter((t: any) => (questionDetail.tables_used || []).includes(t.table))
                        .map(
                          (t: any) =>
                            `${t.table}(${(t.columns || [])
                              .filter((c: any) => c.primary_key || c.name.endsWith('_id'))
                              .map((c: any) => c.name)
                              .join(', ')})`
                        )
                        .join(' · ')}
                    </div>
                  )}
                  {hintStep >= 2 && (
                    <div>
                      <strong className="text-amber-300">Bước 2 (Kỹ năng &amp; Logic):</strong>{' '}
                      Kỹ năng yêu cầu:{' '}
                      {(questionDetail.skills || [])
                        .map((sk: any) => (typeof sk === 'string' ? sk : sk?.name || sk?.code))
                        .join(', ') || 'SELECT / JOIN / GROUP BY'}
                      {' · '}Chế độ chấm:{' '}
                      <span className="underline">
                        {questionDetail.compare_mode || 'order_sensitive'}
                      </span>
                    </div>
                  )}
                  {hintStep >= 3 && (
                    <div>
                      <strong className="text-amber-300">Bước 3 (Khung truy vấn mẫu):</strong>
                      <pre className="mt-1 p-2 rounded bg-[#080c14] border border-amber-900/40 text-[#e2e8f0] overflow-x-auto">
                        {`SELECT ...\nFROM ${(questionDetail.tables_used || ['categories'])[0]}\n${
                          (questionDetail.tables_used || []).length > 1
                            ? `JOIN ${questionDetail.tables_used[1]} ON ...\n`
                            : ''
                        }WHERE ...\nGROUP BY ...\nORDER BY ...;`}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Schema & Tables Strip */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-mono text-[#64748b] mr-1">
                    Bảng:
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
                      <span>{tb}</span>
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-1.5">
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
            Đang tải đề bài...
          </div>
        )}

        {/* Lower Card: Studio SQL Editor & Multi-Tab Execution Console */}
        <div className="bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)] rounded-lg overflow-hidden card-interactive">
          {/* Editor Action Bar */}
          <div className="px-4 py-2.5 bg-[var(--soft)] border-b border-[var(--line)] flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs font-mono text-[var(--muted)]">
              <FileCode2 className="w-4 h-4 text-[var(--green)]" />
              <span className="text-[var(--ink)] font-semibold">query.sql</span>
              <span>·</span>
              <span className="text-[11px]">PostgreSQL 17</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const firstTable = questionDetail?.tables_used?.[0] || 'categories';
                  setSql(`SELECT *\nFROM ${firstTable}\nLIMIT 10;`);
                }}
                className="px-2.5 py-1.5 rounded bg-[var(--surface)] hover:bg-[var(--paper)] border border-[var(--line)] text-[var(--text2)] hover:text-[var(--ink)] text-xs font-mono transition"
              >
                ↺ Đặt lại
              </button>

              <button
                onClick={() => handleAiCoach('review')}
                disabled={running || submitting}
                className="px-3 py-1.5 rounded bg-[var(--surface)] hover:bg-[var(--paper)] border border-[var(--gold)] text-[var(--gold)] text-xs font-semibold transition disabled:opacity-50"
              >
                🤖 AI Coach
              </button>

              <button
                onClick={handleExplain}
                disabled={running || submitting}
                className="px-3 py-1.5 rounded bg-[var(--surface)] hover:bg-[var(--paper)] border border-[var(--copper)] text-[var(--copper)] text-xs font-semibold transition disabled:opacity-50"
              >
                ⚡ Explain
              </button>

              <button
                onClick={handleRunSandbox}
                disabled={running || submitting}
                className="px-3.5 py-1.5 rounded bg-[var(--surface)] hover:bg-[var(--paper)] border border-[var(--green)] text-[var(--green)] text-xs font-semibold transition disabled:opacity-50"
              >
                {running ? 'Đang chạy...' : '▶ Chạy thử'}
              </button>

              <button
                onClick={handleSubmitGrade}
                disabled={running || submitting}
                className="px-4 py-1.5 rounded bg-[#5C7F71] hover:bg-[#496B5D] text-[#F5EDDC] text-xs font-semibold transition disabled:opacity-50"
              >
                {submitting ? 'Đang chấm...' : 'Nộp bài →'}
              </button>
            </div>
          </div>

          {/* Monaco Code Editor */}
          <div className="h-[260px] border-b border-[var(--line)] bg-[var(--surface)]">
            <MonacoEditor
              height="260px"
              defaultLanguage="sql"
              theme={theme === 'dark' ? 'vs-dark' : 'light'}
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
          <div className="px-4 bg-[var(--soft)] border-b border-[var(--line)] flex items-center justify-between">
            <div className="flex items-center gap-4">
              {[
                { id: 'results', label: 'Kết quả' },
                {
                  id: 'tests',
                  label: `Test Cases (${output?.test_cases?.length || 1})`,
                },
                { id: 'ai_coach', label: '🤖 AI Coach' },
                { id: 'explain', label: '⚡ Explain Plan' },
                { id: 'history', label: `Lịch sử (${qSubs.length})` },
                { id: 'policy', label: 'Sandbox' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setConsoleTab(t.id as any)}
                  className={`py-2.5 text-xs font-semibold border-b-2 transition ${
                    consoleTab === t.id
                      ? 'border-[var(--copper)] text-[var(--ink)]'
                      : 'border-transparent text-[var(--muted)] hover:text-[var(--ink)]'
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
              <div className="space-y-3">
                {output?.test_cases ? (
                  output.test_cases.map((tc: any) => (
                    <div
                      key={tc.test_id}
                      className="p-3.5 rounded bg-[#0d1321] border border-[#1d283a] space-y-2.5 text-xs font-mono"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          {tc.passed ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-rose-400" />
                          )}
                          <span className="text-white font-semibold">
                            Dataset: {tc.dataset_ref} ({tc.type})
                          </span>
                          {tc.reason_code && (
                            <span className="px-2 py-0.5 rounded bg-[#162238] border border-[#293f66] text-[#38bdf8] text-[10px]">
                              {tc.reason_code}
                            </span>
                          )}
                        </div>
                        <div className="text-[#94a3b8]">
                          Expected rows: <strong className="text-white">{tc.expected_rows}</strong> ·
                          Actual rows: <strong className="text-white">{tc.actual_rows}</strong>
                        </div>
                      </div>

                      {tc.diagnostic_hint && (
                        <div className="text-amber-300 bg-amber-950/30 border border-amber-800/50 px-2.5 py-1.5 rounded">
                          💡 {tc.diagnostic_hint}
                        </div>
                      )}

                      {(tc.expected_columns || tc.actual_columns) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                          <div className="p-2 rounded bg-[#090d16] border border-[#192336] text-[#cbd5e1]">
                            <span className="text-[#64748b]">Expected Columns: </span>
                            {(tc.expected_columns || []).join(', ') || '-'}
                          </div>
                          <div className="p-2 rounded bg-[#090d16] border border-[#192336] text-[#cbd5e1]">
                            <span className="text-[#64748b]">Actual Columns: </span>
                            {(tc.actual_columns || []).join(', ') || '-'}
                          </div>
                        </div>
                      )}

                      {tc.expected_preview?.length > 0 && (
                        <div className="space-y-1">
                          <div className="text-[11px] font-semibold text-emerald-300">
                            Đáp án mẫu (5 dòng đầu)
                          </div>
                          <div className="overflow-x-auto border border-[#1a2436] rounded">
                            <table className="w-full text-left border-collapse text-[11px]">
                              <thead>
                                <tr className="bg-[#0e1525] border-b border-[#1a2436] text-[#94a3b8]">
                                  {Object.keys(tc.expected_preview[0] || {}).map((col) => (
                                    <th key={col} className="px-2.5 py-1.5 border-r border-[#1a2436] last:border-r-0">
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-[#141d2e]">
                                {tc.expected_preview.slice(0, 5).map((row: any, rIdx: number) => (
                                  <tr key={rIdx}>
                                    {Object.keys(tc.expected_preview[0] || {}).map((col) => (
                                      <td key={col} className="px-2.5 py-1 text-[#e2e8f0] border-r border-[#141d2e] last:border-r-0">
                                        {row[col] === null || row[col] === undefined ? 'null' : String(row[col])}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-xs font-mono text-[#64748b]">
                    Nhấn &quot;Nộp bài chấm điểm&quot; để xem chi tiết đối chiếu từng Test Case.
                  </div>
                )}
              </div>
            )}

            {!errorMsg && consoleTab === 'ai_coach' && (
              <div className="space-y-3 text-xs font-mono">
                <div className="p-3 rounded bg-[var(--surface)] border border-[var(--line)] flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => handleAiCoach('review')}
                      className={`px-3 py-1.5 rounded border font-semibold transition ${
                        aiCoachData?.mode === 'review' || !aiCoachData
                          ? 'bg-[#5C7F71] text-[#F5EDDC] border-[#5C7F71]'
                          : 'bg-[var(--paper)] text-[var(--ink)] border-[var(--line)]'
                      }`}
                    >
                      🔍 Review & Tối ưu SQL
                    </button>
                    <button
                      onClick={() => handleAiCoach('nl2sql')}
                      className={`px-3 py-1.5 rounded border font-semibold transition ${
                        aiCoachData?.mode === 'nl2sql'
                          ? 'bg-[#B2653B] text-[#F5EDDC] border-[#B2653B]'
                          : 'bg-[var(--paper)] text-[var(--ink)] border-[var(--line)]'
                      }`}
                    >
                      ✨ Ý tưởng Tiếng Việt → SQL
                    </button>
                    <button
                      onClick={() => handleAiCoach('interview')}
                      className={`px-3 py-1.5 rounded border font-semibold transition ${
                        aiCoachData?.mode === 'interview'
                          ? 'bg-[#BA8530] text-[#F5EDDC] border-[#BA8530]'
                          : 'bg-[var(--paper)] text-[var(--ink)] border-[var(--line)]'
                      }`}
                    >
                      🎙️ Phỏng vấn Data AI
                    </button>
                  </div>
                  <div className="flex items-center gap-1.5 flex-1 min-w-[220px]">
                    <input
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="Nhập ý tưởng tiếng Việt (VD: lấy top 5 khách chi tiêu cao nhất)..."
                      className="flex-1 px-2.5 py-1 rounded bg-[var(--paper)] border border-[var(--line)] text-[var(--ink)] text-xs focus:outline-none"
                    />
                    <button
                      onClick={() => handleAiCoach('nl2sql')}
                      className="px-2.5 py-1 rounded bg-[var(--soft)] hover:bg-[var(--paper)] border border-[var(--line)] text-[var(--ink)] font-semibold"
                    >
                      Sinh SQL
                    </button>
                  </div>
                </div>

                {aiCoachData ? (
                  <div className="p-4 rounded bg-[var(--surface)] border border-[var(--line)] space-y-3 text-[var(--ink)]">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] pb-2">
                      <span className="font-bold text-sm text-[var(--ink)]">
                        {aiCoachData.headline}
                      </span>
                      <span className="px-2.5 py-0.5 rounded bg-[var(--soft)] border border-[var(--line)] text-[var(--green)] font-bold">
                        AI Readiness: {aiCoachData.clean_score}/100
                      </span>
                    </div>

                    <div className="space-y-1.5">
                      {(aiCoachData.insights || []).map((ins: string, i: number) => (
                        <div key={i} className="text-xs leading-relaxed text-[var(--text2)]">
                          {ins}
                        </div>
                      ))}
                    </div>

                    {aiCoachData.interview_q && (
                      <div className="p-3 rounded bg-[var(--paper)] border border-[var(--gold)] space-y-2">
                        <div className="font-bold text-[var(--ink)]">
                          ❓ Câu hỏi phỏng vấn từ AI Tech Lead:
                        </div>
                        <div className="text-[var(--text2)]">{aiCoachData.interview_q}</div>
                        <button
                          onClick={() => setShowInterviewAns(!showInterviewAns)}
                          className="px-2.5 py-1 rounded bg-[var(--surface)] border border-[var(--line)] text-[var(--copper)] font-semibold"
                        >
                          {showInterviewAns ? 'Ẩn gợi ý trả lời' : '💡 Xem gợi ý trả lời phỏng vấn'}
                        </button>
                        {showInterviewAns && (
                          <div className="pt-1 text-[var(--green)] font-medium">
                            👉 {aiCoachData.interview_answer}
                          </div>
                        )}
                      </div>
                    )}

                    {aiCoachData.suggested_sql && (
                      <div className="p-3 rounded bg-[var(--paper)] border border-[var(--line)] flex flex-wrap items-center justify-between gap-2">
                        <pre className="text-[11px] text-[var(--ink)] overflow-x-auto">
                          {aiCoachData.suggested_sql}
                        </pre>
                        <button
                          onClick={() => setSql(aiCoachData.suggested_sql)}
                          className="px-3 py-1 rounded bg-[#5C7F71] text-[#F5EDDC] font-semibold shrink-0"
                        >
                          ↺ Chèn khung SQL vào Editor
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="py-8 text-center text-[var(--muted)]">
                    Chọn 1 trong 3 chế độ AI Coach phía trên để Review code, dịch Tiếng Việt sang SQL hoặc luyện phỏng vấn Data Engineer thời đại AI.
                  </div>
                )}
              </div>
            )}

            {!errorMsg && consoleTab === 'explain' && (
              <div className="space-y-3 text-xs font-mono">
                {explainData ? (
                  <>
                    <div className="flex flex-wrap items-center gap-4 p-3 rounded bg-[#0d1321] border border-[#1d283a] text-[#cbd5e1]">
                      <span>
                        Execution Time:{' '}
                        <strong className="text-emerald-400">
                          {explainData.execution_time_ms ?? 0} ms
                        </strong>
                      </span>
                      <span>
                        Total Cost:{' '}
                        <strong className="text-white">{explainData.total_cost ?? 0}</strong>
                      </span>
                      <span>
                        Planning Time:{' '}
                        <strong className="text-[#94a3b8]">
                          {explainData.planning_time_ms ?? 0} ms
                        </strong>
                      </span>
                    </div>

                    {(explainData.warnings || []).length > 0 && (
                      <div className="p-3 rounded bg-amber-950/30 border border-amber-800/50 text-amber-300 space-y-1">
                        {explainData.warnings.map((w: string, i: number) => (
                          <div key={i}>⚠️ {w}</div>
                        ))}
                      </div>
                    )}

                    <div className="overflow-x-auto border border-[#1a2436] rounded">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-[#0e1525] border-b border-[#1a2436] text-[#94a3b8]">
                            <th className="px-3 py-2">Node Type</th>
                            <th className="px-3 py-2">Relation</th>
                            <th className="px-3 py-2">Total Cost</th>
                            <th className="px-3 py-2">Plan Rows</th>
                            <th className="px-3 py-2">Actual Rows</th>
                            <th className="px-3 py-2">Actual Time (ms)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#141d2e]">
                          {(explainData.plan_nodes || []).map((n: any, idx: number) => (
                            <tr key={idx} className="hover:bg-[#11192b] text-[#e2e8f0]">
                              <td className="px-3 py-1.5 font-semibold text-[#38bdf8]">
                                {n.node_type}
                              </td>
                              <td className="px-3 py-1.5">{n.relation_name || '-'}</td>
                              <td className="px-3 py-1.5">{n.total_cost}</td>
                              <td className="px-3 py-1.5">{n.plan_rows}</td>
                              <td className="px-3 py-1.5">{n.actual_rows}</td>
                              <td className="px-3 py-1.5">{n.actual_total_time_ms}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <div className="py-8 text-center text-[#64748b]">
                    Nhấn &quot;⚡ Explain&quot; trên thanh công cụ để phân tích kế hoạch thực thi PostgreSQL.
                  </div>
                )}
              </div>
            )}

            {!errorMsg && consoleTab === 'history' && (
              <div className="space-y-2 text-xs font-mono">
                {qSubs.length > 0 ? (
                  qSubs.map((sub: any) => (
                    <div
                      key={sub.submission_id}
                      className="p-3 rounded bg-[#0d1321] border border-[#1d283a] flex flex-wrap items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`px-2 py-0.5 rounded border text-[11px] ${
                            sub.status === 'accepted' || sub.passed
                              ? 'bg-emerald-950/50 text-emerald-300 border-emerald-800/60'
                              : 'bg-rose-950/50 text-rose-300 border-rose-800/60'
                          }`}
                        >
                          {(sub.status || 'failed').toUpperCase()}
                        </span>
                        <span className="text-white">Score: {sub.score}/100</span>
                        <span className="text-[#94a3b8]">{sub.runtime_ms ?? 0} ms</span>
                        <span className="text-[#64748b]">
                          {sub.submitted_at
                            ? new Date(sub.submitted_at).toLocaleString('vi-VN')
                            : ''}
                        </span>
                      </div>
                      {sub.submitted_sql && (
                        <button
                          onClick={() => setSql(sub.submitted_sql)}
                          className="px-2.5 py-1 rounded bg-[#162238] hover:bg-[#1f304d] border border-[#293f66] text-[#38bdf8]"
                        >
                          ↺ Nạp lại code
                        </button>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-[#64748b]">
                    Chưa có lịch sử nộp bài cho câu hỏi này.
                  </div>
                )}
              </div>
            )}

            {!errorMsg && consoleTab === 'policy' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-[#202722] border border-[#2c352f]">
                  <div className="text-[#8d9a91] mb-1 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-[#5C7F71]" />
                    ROLE ISOLATION
                  </div>
                  <div className="text-[#F5EDDC]">sqlarena_ai_ro @ enterprise_db</div>
                </div>
                <div className="p-3 rounded bg-[#202722] border border-[#2c352f]">
                  <div className="text-[#8d9a91] mb-1">TRANSACTION GUARD</div>
                  <div className="text-[#F5EDDC]">READ ONLY · 10s timeout</div>
                </div>
                <div className="p-3 rounded bg-[#202722] border border-[#2c352f]">
                  <div className="text-[#8d9a91] mb-1">AST / REGEX FILTER</div>
                  <div className="text-[#F5EDDC]">SELECT / WITH Only</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
      </div>
    </div>
  );
}
