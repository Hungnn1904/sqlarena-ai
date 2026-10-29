'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  getWeeklyCurrent,
  getWeeklyQuestions,
  getQuestionDetail,
  getQuestionSubmissions,
  getDatasetSchema,
  runSandboxSql,
  submitGradingSql,
} from '../lib/api';
import { useTheme } from './theme-provider';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const DIFF_META: Record<number, { label: string; badge: string }> = {
  1: {
    label: 'Dễ',
    badge: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60',
  },
  2: {
    label: 'Trung bình',
    badge: 'bg-amber-950/60 text-amber-300 border-amber-800/60',
  },
  3: {
    label: 'Khó',
    badge: 'bg-rose-950/60 text-rose-300 border-rose-800/60',
  },
};

const SKILL_MAP: Record<number, string> = {
  1: 'S1 · SELECT / WHERE',
  2: 'S2 · JOIN',
  3: 'S3 · GROUP BY / HAVING',
  4: 'S4 · Subquery / CTE',
  5: 'S5 · Window Functions',
  6: 'S6 · NULL & Edge Cases',
};

export default function LearnerWorkbench({
  onSubmissionComplete,
}: {
  onSubmissionComplete?: () => void;
}) {
  const { theme } = useTheme();
  const [viewMode, setViewMode] = useState<'list' | 'solve'>('list');
  const [weeklyMeta, setWeeklyMeta] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [questionDetail, setQuestionDetail] = useState<any>(null);
  const [schemaInfo, setSchemaInfo] = useState<any>(null);

  // Filters
  const [diffFilter, setDiffFilter] = useState<number | undefined>(undefined);
  const [skillFilter, setSkillFilter] = useState<number | undefined>(undefined);
  const [solvedFilter, setSolvedFilter] = useState<boolean | undefined>(undefined);
  const [searchQ, setSearchQ] = useState('');

  // Editor & Console
  const [sql, setSql] = useState<string>('SELECT * FROM categories LIMIT 10;');
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [output, setOutput] = useState<any>(null);
  const [qSubs, setQSubs] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [consoleTab, setConsoleTab] = useState<'results' | 'tests' | 'history'>('results');

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
      setErrorMsg(e?.response?.data?.error?.message || 'Không tải được danh sách đề bài');
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
    setErrorMsg(null);
    getQuestionDetail(selectedId)
      .then((d) => {
        setQuestionDetail(d);
        const firstTable = d.tables_used?.[0] || 'categories';
        setSql(`SELECT *\nFROM ${firstTable}\nLIMIT 10;`);
      })
      .catch((e) => setErrorMsg(e?.response?.data?.error?.message || 'Lỗi tải đề bài'));
    getQuestionSubmissions(selectedId)
      .then((r) => setQSubs(r?.items || []))
      .catch(() => setQSubs([]));
  }, [selectedId]);

  const handleOpenQuestion = (qId: number) => {
    setSelectedId(qId);
    setViewMode('solve');
  };

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
      const res = await runSandboxSql(qId, `SELECT * FROM ${tableName} LIMIT 5;`);
      setOutput({ mode: 'run', ...res });
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Không xem trước được bảng');
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

  const allTables: any[] =
    schemaInfo?.tables || schemaInfo?.schema_description?.tables || [];
  const usedTableNames: string[] = questionDetail?.tables_used || [];
  const relevantTables =
    usedTableNames.length > 0
      ? allTables.filter((tb: any) =>
          usedTableNames.includes(tb.name || tb.table)
        )
      : allTables.slice(0, 2);

  const currentIdx = questions.findIndex((q) => q.question_id === selectedId);
  const prevQuestionId = currentIdx > 0 ? questions[currentIdx - 1]?.question_id : null;
  const nextQuestionId =
    currentIdx >= 0 && currentIdx < questions.length - 1
      ? questions[currentIdx + 1]?.question_id
      : null;
  const solvedCount = weeklyMeta?.solved_count || 0;
  const totalCount = weeklyMeta?.question_count || questions.length || 20;

  // VIEW 1: CODE PTIT STYLE PROBLEM LIST TABLE
  if (viewMode === 'list') {
    return (
      <div className="space-y-4">
        {/* Filter Bar */}
        <div className="p-4 rounded-lg bg-[var(--surface)] border border-[var(--line)] flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5 flex-1">
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadQuestions()}
              placeholder="Tìm mã bài hoặc tiêu đề..."
              className="w-full sm:w-64 px-3 py-1.5 rounded bg-[var(--paper)] border border-[var(--line)] text-xs text-[var(--ink)] placeholder-[var(--muted)] focus:outline-none focus:border-[var(--green)]"
            />
            <button
              onClick={loadQuestions}
              className="px-3 py-1.5 rounded bg-[var(--soft)] hover:bg-[var(--paper)] border border-[var(--line)] text-xs font-medium text-[var(--ink)]"
            >
              Tìm kiếm
            </button>

            <div className="flex items-center gap-1">
              {[
                { label: 'Tất cả', val: undefined },
                { label: 'Dễ', val: 1 },
                { label: 'Trung bình', val: 2 },
                { label: 'Khó', val: 3 },
              ].map((b) => (
                <button
                  key={b.label}
                  onClick={() => setDiffFilter(b.val)}
                  className={`px-2.5 py-1.5 rounded text-xs font-medium border transition ${
                    diffFilter === b.val
                      ? 'bg-[var(--green)] border-[var(--green)] text-[var(--on-accent)]'
                      : 'bg-[var(--paper)] border-[var(--line)] text-[var(--text2)] hover:text-[var(--ink)]'
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>

            <select
              value={skillFilter ?? ''}
              onChange={(e) =>
                setSkillFilter(e.target.value ? Number(e.target.value) : undefined)
              }
              className="px-2.5 py-1.5 rounded bg-[var(--paper)] border border-[var(--line)] text-xs text-[var(--ink)] focus:outline-none"
            >
              <option value="">Mọi kỹ năng (S1–S6)</option>
              <option value="1">S1 · SELECT / WHERE</option>
              <option value="2">S2 · JOIN</option>
              <option value="3">S3 · GROUP BY / HAVING</option>
              <option value="4">S4 · Subquery / CTE</option>
              <option value="5">S5 · Window Functions</option>
              <option value="6">S6 · NULL & Edge Cases</option>
            </select>

            <select
              value={
                solvedFilter === undefined ? '' : solvedFilter ? 'solved' : 'unsolved'
              }
              onChange={(e) =>
                setSolvedFilter(
                  e.target.value === ''
                    ? undefined
                    : e.target.value === 'solved'
                )
              }
              className="px-2.5 py-1.5 rounded bg-[var(--paper)] border border-[var(--line)] text-xs text-[var(--ink)] focus:outline-none"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="solved">Đã giải</option>
              <option value="unsolved">Chưa làm</option>
            </select>
          </div>

          <div className="text-xs font-medium text-[var(--text2)]">
            {weeklyMeta?.title || 'Tuần #42'} · Đã giải{' '}
            <strong className="text-[var(--green)]">
              {solvedCount}/{totalCount}
            </strong>
          </div>
        </div>

        {/* Code PTIT Style Full-Width Table */}
        <div className="rounded-lg bg-[var(--surface)] border border-[var(--line)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[var(--soft)] border-b border-[var(--line)] text-[var(--text2)] font-semibold">
                  <th className="py-3 px-4 w-28">Trạng thái</th>
                  <th className="py-3 px-4 w-24">Mã bài</th>
                  <th className="py-3 px-4">Tiêu đề bài tập</th>
                  <th className="py-3 px-4 w-52">Nhóm kỹ năng</th>
                  <th className="py-3 px-4 w-48">Bảng dữ liệu</th>
                  <th className="py-3 px-4 w-28">Độ khó</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {questions.length > 0 ? (
                  questions.map((q: any) => {
                    const diff = DIFF_META[q.difficulty] || DIFF_META[1];
                    const code = `SQL${String(q.position || q.question_id).padStart(2, '0')}`;
                    const skillLabel =
                      Array.isArray(q.skills) && q.skills.length > 0
                        ? q.skills.join(', ')
                        : q.skill_code && q.skill_name
                        ? `${q.skill_code} · ${q.skill_name}`
                        : SKILL_MAP[q.skill_id] || 'SELECT / WHERE';
                    const tablesText =
                      Array.isArray(q.tables_used) && q.tables_used.length > 0
                        ? q.tables_used.join(', ')
                        : 'enterprise_db';
                    return (
                      <tr
                        key={q.question_id}
                        onClick={() => handleOpenQuestion(q.question_id)}
                        className="hover:bg-[var(--soft)]/60 cursor-pointer transition"
                      >
                        <td className="py-3 px-4">
                          {q.solved ? (
                            <span className="inline-block px-2 py-0.5 rounded bg-[var(--green)]/15 text-[var(--green)] font-semibold text-[11px]">
                              Đã giải
                            </span>
                          ) : (
                            <span className="inline-block px-2 py-0.5 rounded bg-[var(--soft)] text-[var(--muted)] text-[11px]">
                              Chưa làm
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-semibold text-[var(--copper)]">
                          {code}
                        </td>
                        <td className="py-3 px-4 font-semibold text-[var(--ink)] hover:text-[var(--green)]">
                          {q.title}
                        </td>
                        <td className="py-3 px-4 text-[var(--text2)]">
                          {skillLabel}
                        </td>
                        <td className="py-3 px-4 text-[var(--muted)]">
                          {tablesText}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-block px-2 py-0.5 rounded border text-[11px] font-medium ${diff.badge}`}
                          >
                            {diff.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td
                      colSpan={6}
                      className="py-10 text-center text-xs text-[var(--muted)]"
                    >
                      Không tìm thấy bài tập phù hợp với bộ lọc hiện tại.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // VIEW 2: SOLVE WORKSPACE (PROBLEM + INLINE RELEVANT SCHEMA ON LEFT, EDITOR + CONSOLE ON RIGHT)
  const diff = DIFF_META[questionDetail?.difficulty || 1] || DIFF_META[1];
  const qCode = selectedId ? `SQL${String(selectedId).padStart(2, '0')}` : 'SQL01';

  return (
    <div className="space-y-4">
      {/* Top Navigation Bar */}
      <div className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--line)] flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setViewMode('list')}
            className="px-3 py-1.5 rounded bg-[var(--soft)] hover:bg-[var(--paper)] border border-[var(--line)] text-xs font-semibold text-[var(--ink)]"
          >
            Quay lại danh sách đề
          </button>
          <span className="text-xs font-bold text-[var(--copper)]">{qCode}</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] font-medium ${diff.badge}`}>
            {diff.label}
          </span>
          {questionDetail?.solved && (
            <span className="px-2 py-0.5 rounded bg-[var(--green)]/15 text-[var(--green)] text-[11px] font-semibold">
              Đã giải
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => prevQuestionId && setSelectedId(prevQuestionId)}
            disabled={!prevQuestionId}
            className="px-3 py-1.5 rounded bg-[var(--paper)] hover:bg-[var(--soft)] border border-[var(--line)] text-xs font-medium text-[var(--ink)] disabled:opacity-40"
          >
            Bài trước
          </button>
          <button
            onClick={() => nextQuestionId && setSelectedId(nextQuestionId)}
            disabled={!nextQuestionId}
            className="px-3 py-1.5 rounded bg-[var(--paper)] hover:bg-[var(--soft)] border border-[var(--line)] text-xs font-medium text-[var(--ink)] disabled:opacity-40"
          >
            Bài tiếp
          </button>
        </div>
      </div>

      {/* Main Split Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Column: Problem Statement + Inline Relevant Table Schema */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-5 rounded-lg bg-[var(--surface)] border border-[var(--line)] space-y-3">
            <h1 className="text-lg font-bold text-[var(--ink)] leading-snug">
              {questionDetail?.title || 'Đang tải đề bài...'}
            </h1>
            <p className="text-xs text-[var(--text2)] leading-relaxed whitespace-pre-line">
              {questionDetail?.question || ''}
            </p>

            {questionDetail?.expected_columns?.length > 0 && (
              <div className="pt-2 border-t border-[var(--line)]">
                <div className="text-[11px] font-semibold text-[var(--muted)] mb-1.5">
                  Các cột kết quả cần trả về:
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {questionDetail.expected_columns.map((col: string) => (
                    <span
                      key={col}
                      className="px-2 py-0.5 rounded bg-[var(--paper)] border border-[var(--line)] text-xs font-semibold text-[var(--copper)]"
                    >
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Inline Schema of Tables Used by This Problem */}
          <div className="p-4 rounded-lg bg-[var(--surface)] border border-[var(--line)] space-y-3">
            <div className="flex items-center justify-between border-b border-[var(--line)] pb-2">
              <span className="text-xs font-bold text-[var(--ink)]">
                Cấu trúc bảng dữ liệu sử dụng ({relevantTables.length})
              </span>
              <span className="text-[11px] text-[var(--muted)]">
                PostgreSQL 17
              </span>
            </div>

            <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
              {relevantTables.map((tb: any) => {
                const tableName = tb.name || tb.table || 'table';
                const cols = tb.columns || [];
                return (
                  <div
                    key={tableName}
                    className="rounded border border-[var(--line)] bg-[var(--paper)] overflow-hidden"
                  >
                    <div className="px-3 py-2 bg-[var(--soft)] border-b border-[var(--line)] flex items-center justify-between gap-2">
                      <div>
                        <span className="text-xs font-bold text-[var(--ink)]">
                          {tableName}
                        </span>
                        {tb.row_count !== undefined && (
                          <span className="ml-2 text-[11px] text-[var(--muted)]">
                            ({tb.row_count} dòng)
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handlePreviewTable(tableName)}
                        className="px-2.5 py-1 rounded bg-[var(--surface)] hover:bg-[var(--green)] hover:text-[var(--on-accent)] border border-[var(--line)] text-[11px] font-medium text-[var(--ink)] transition"
                      >
                        Xem dữ liệu mẫu
                      </button>
                    </div>
                    <div className="p-2.5 grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
                      {cols.map((c: any) => (
                        <div
                          key={c.name}
                          className="flex items-center justify-between px-2 py-1 rounded bg-[var(--surface)] border border-[var(--line)]"
                        >
                          <span className="font-medium text-[var(--ink)]">
                            {c.name}
                          </span>
                          <span className="text-[11px] text-[var(--muted)]">
                            {c.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: SQL Editor + Grading Console */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-lg bg-[var(--surface)] border border-[var(--line)] overflow-hidden">
            <div className="px-4 py-2.5 bg-[var(--soft)] border-b border-[var(--line)] flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold text-[var(--ink)]">
                query.sql · PostgreSQL 17
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const firstTable = questionDetail?.tables_used?.[0] || 'categories';
                    setSql(`SELECT *\nFROM ${firstTable}\nLIMIT 10;`);
                  }}
                  className="px-3 py-1.5 rounded bg-[var(--surface)] hover:bg-[var(--paper)] border border-[var(--line)] text-xs font-medium text-[var(--ink)]"
                >
                  Đặt lại
                </button>
                <button
                  onClick={handleRunSandbox}
                  disabled={running || submitting}
                  className="px-3.5 py-1.5 rounded bg-[var(--copper)] text-[var(--on-accent)] text-xs font-semibold disabled:opacity-50"
                >
                  {running ? 'Đang chạy...' : 'Chạy thử'}
                </button>
                <button
                  onClick={handleSubmitGrade}
                  disabled={submitting || running}
                  className="px-4 py-1.5 rounded bg-[var(--green)] hover:bg-[var(--green-hover)] text-[var(--on-accent)] text-xs font-semibold disabled:opacity-50"
                >
                  {submitting ? 'Đang chấm...' : 'Nộp bài'}
                </button>
              </div>
            </div>

            <div className="h-[280px] border-b border-[var(--line)]">
              <MonacoEditor
                height="100%"
                defaultLanguage="sql"
                theme={theme === 'dark' ? 'vs-dark' : 'light'}
                value={sql}
                onChange={(v) => setSql(v || '')}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  padding: { top: 12, bottom: 12 },
                }}
              />
            </div>

            {/* Console Tabs */}
            <div className="px-4 py-2 bg-[var(--soft)] border-b border-[var(--line)] flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                {[
                  { id: 'results', label: 'Kết quả' },
                  { id: 'tests', label: 'Test Cases' },
                  { id: 'history', label: `Lịch sử nộp (${qSubs.length})` },
                ].map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setConsoleTab(t.id as any)}
                    className={`px-3 py-1 rounded text-xs font-semibold transition ${
                      consoleTab === t.id
                        ? 'bg-[var(--green)] text-[var(--on-accent)]'
                        : 'text-[var(--text2)] hover:text-[var(--ink)]'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              {output?.runtime_ms !== undefined && (
                <span className="text-xs text-[var(--muted)]">
                  Thời gian: {output.runtime_ms} ms
                </span>
              )}
            </div>

            {/* Console Body */}
            <div className="p-4 max-h-[360px] overflow-y-auto">
              {errorMsg && (
                <div className="p-3 rounded bg-[var(--red)]/10 border border-[var(--red)]/30 text-[var(--red)] text-xs">
                  {errorMsg}
                </div>
              )}

              {!errorMsg && consoleTab === 'results' && (
                <div className="space-y-3 text-xs">
                  {output?.mode === 'submit' && (
                    <div
                      className={`p-3 rounded border flex flex-wrap items-center justify-between gap-2 ${
                        output.passed
                          ? 'bg-[var(--green)]/15 border-[var(--green)] text-[var(--ink)]'
                          : 'bg-[var(--red)]/10 border-[var(--red)]/40 text-[var(--ink)]'
                      }`}
                    >
                      <div className="font-bold">
                        {output.passed
                          ? 'Chính xác (Accepted) — Đã vượt qua toàn bộ Test Cases!'
                          : `Chưa chính xác (${output.status || 'Wrong Answer'})`}
                      </div>
                      <div className="font-semibold">
                        Điểm: {output.score ?? 0}/100 ({output.passed_AutoTests ?? output.passed_tests ?? 0}/
                        {output.total_AutoTests ?? output.total_tests ?? 1} tests)
                      </div>
                    </div>
                  )}

                  {output?.error && (
                    <div className="p-3 rounded bg-[var(--red)]/10 border border-[var(--red)]/30 text-[var(--red)]">
                      {output.error}
                    </div>
                  )}

                  {output?.rows ? (
                    <div className="space-y-2">
                      <div className="text-[11px] text-[var(--muted)]">
                        Trả về {output.row_count ?? output.rows.length} dòng dữ liệu
                      </div>
                      {output.rows.length > 0 ? (
                        <div className="overflow-x-auto border border-[var(--line)] rounded">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-[var(--soft)] border-b border-[var(--line)] text-[var(--ink)] font-semibold">
                                {(output.columns || Object.keys(output.rows[0] || {})).map(
                                  (col: string) => (
                                    <th
                                      key={col}
                                      className="px-3 py-2 border-r border-[var(--line)] last:border-r-0"
                                    >
                                      {col}
                                    </th>
                                  )
                                )}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[var(--line)]">
                              {output.rows.slice(0, 50).map((row: any, rIdx: number) => (
                                <tr key={rIdx} className="hover:bg-[var(--soft)]/40">
                                  {(output.columns || Object.keys(output.rows[0] || {})).map(
                                    (col: string, cIdx: number) => {
                                      const val = Array.isArray(row) ? row[cIdx] : row[col];
                                      return (
                                        <td
                                          key={col}
                                          className="px-3 py-1.5 border-r border-[var(--line)] last:border-r-0 text-[var(--ink)]"
                                        >
                                          {val === null || val === undefined
                                            ? 'NULL'
                                            : String(val)}
                                        </td>
                                      );
                                    }
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="p-4 text-center text-[var(--muted)] bg-[var(--paper)] rounded border border-[var(--line)]">
                          Truy vấn thực thi thành công nhưng không có dòng dữ liệu nào trả về (0 rows).
                        </div>
                      )}
                    </div>
                  ) : (
                    !output && (
                      <div className="py-8 text-center text-[var(--muted)]">
                        Nhấn &quot;Chạy thử&quot; để kiểm tra kết quả truy vấn hoặc &quot;Nộp bài&quot; để chấm điểm.
                      </div>
                    )
                  )}
                </div>
              )}

              {!errorMsg && consoleTab === 'tests' && (
                <div className="space-y-3 text-xs">
                  {output?.test_cases?.length > 0 ? (
                    output.test_cases.map((tc: any) => (
                      <div
                        key={tc.test_id}
                        className="p-3 rounded bg-[var(--paper)] border border-[var(--line)] space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-bold text-[var(--ink)]">
                            {tc.passed ? 'Đạt' : 'Chưa đạt'} · Dataset: {tc.dataset_ref} ({tc.type})
                          </span>
                          <span className="text-[var(--text2)]">
                            Số dòng mẫu: <strong>{tc.expected_rows}</strong> · Thực tế:{' '}
                            <strong>{tc.actual_rows}</strong>
                          </span>
                        </div>
                        {tc.diagnostic_hint && (
                          <div className="p-2 rounded bg-[var(--surface)] border border-[var(--line)] text-[var(--copper)]">
                            Nhận xét: {tc.diagnostic_hint}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="py-8 text-center text-[var(--muted)]">
                      Nhấn &quot;Nộp bài&quot; để xem chi tiết kết quả đối chiếu từng Test Case.
                    </div>
                  )}
                </div>
              )}

              {!errorMsg && consoleTab === 'history' && (
                <div className="space-y-2 text-xs">
                  {qSubs.length > 0 ? (
                    qSubs.map((sub: any) => (
                      <div
                        key={sub.submission_id}
                        className="p-3 rounded bg-[var(--paper)] border border-[var(--line)] flex flex-wrap items-center justify-between gap-2"
                      >
                        <div className="flex items-center gap-3">
                          <span
                            className={`px-2 py-0.5 rounded font-semibold text-[11px] ${
                              sub.status === 'accepted' || sub.passed
                                ? 'bg-[var(--green)]/15 text-[var(--green)]'
                                : 'bg-[var(--red)]/15 text-[var(--red)]'
                            }`}
                          >
                            {(sub.status || 'failed').toUpperCase()}
                          </span>
                          <span className="font-semibold text-[var(--ink)]">
                            {sub.score}/100 điểm
                          </span>
                          <span className="text-[var(--muted)]">{sub.runtime_ms ?? 0} ms</span>
                          <span className="text-[var(--muted)]">
                            {sub.submitted_at
                              ? new Date(sub.submitted_at).toLocaleString('vi-VN')
                              : ''}
                          </span>
                        </div>
                        {sub.submitted_sql && (
                          <button
                            onClick={() => setSql(sub.submitted_sql)}
                            className="px-2.5 py-1 rounded bg-[var(--surface)] hover:bg-[var(--soft)] border border-[var(--line)] text-[var(--ink)] font-medium"
                          >
                            Nạp lại code
                          </button>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="py-8 text-center text-[var(--muted)]">
                      Chưa có lịch sử nộp bài cho câu hỏi này.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
