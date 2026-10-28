'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  getWeeklyCurrent,
  getWeeklyQuestions,
  getQuestionDetail,
  getDatasetSchema,
  runSandboxSql,
  submitGradingSql,
} from '../lib/api';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const DIFF_LABEL: Record<number, { text: string; cls: string }> = {
  1: { text: 'Easy', cls: 'bg-[#00e5a0]/15 text-[#00e5a0] border-[#00e5a0]/30' },
  2: { text: 'Medium', cls: 'bg-[#ffb830]/15 text-[#ffb830] border-[#ffb830]/30' },
  3: { text: 'Hard', cls: 'bg-red-500/15 text-red-400 border-red-500/30' },
};

export default function LearnerWorkbench({ onSubmissionComplete }: { onSubmissionComplete?: () => void }) {
  const [weeklyMeta, setWeeklyMeta] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [questionDetail, setQuestionDetail] = useState<any>(null);
  const [schemaInfo, setSchemaInfo] = useState<any>(null);
  const [showSchema, setShowSchema] = useState(false);

  // Filters
  const [diffFilter, setDiffFilter] = useState<number | undefined>(undefined);
  const [solvedFilter, setSolvedFilter] = useState<boolean | undefined>(undefined);
  const [searchQ, setSearchQ] = useState('');

  // SQL Editor & Output
  const [sql, setSql] = useState<string>('SELECT * FROM categories LIMIT 10;');
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [output, setOutput] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadQuestions = async () => {
    try {
      const [meta, qList] = await Promise.all([
        getWeeklyCurrent(),
        getWeeklyQuestions({ difficulty: diffFilter, solved: solvedFilter, q: searchQ || undefined }),
      ]);
      setWeeklyMeta(meta);
      const items = qList.items || [];
      setQuestions(items);
      if (items.length > 0 && (!selectedId || !items.some((x: any) => x.question_id === selectedId))) {
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
        setSql(`SELECT *\nFROM ${firstTable}\nLIMIT 10;`);
      })
      .catch((e) => setErrorMsg(e?.response?.data?.error?.message || 'Lỗi tải chi tiết đề'));
  }, [selectedId]);

  const handleRunSandbox = async () => {
    if (!selectedId) return;
    setRunning(true);
    setErrorMsg(null);
    setOutput(null);
    try {
      const res = await runSandboxSql(selectedId, sql);
      setOutput({ mode: 'run', ...res });
    } catch (e: any) {
      setErrorMsg(e?.response?.data?.error?.message || 'Lỗi thực thi SQL Sandbox');
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

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* Left Column: Question List */}
      <div className="lg:col-span-4 bg-[#111827] border border-[#1e2d45] rounded-xl p-4 flex flex-col max-h-[840px]">
        <div className="mb-3 pb-3 border-b border-[#1e2d45]">
          <div className="flex items-center justify-between">
            <span className="text-[0.68rem] font-mono uppercase tracking-wider text-[#00d4ff]">
              BỘ ĐỀ TUẦN ĐANG MỞ
            </span>
            {weeklyMeta && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#00e5a0]/15 text-[#00e5a0]">
                Đã giải: {weeklyMeta.solved_count || 0}/{weeklyMeta.total_questions || questions.length}
              </span>
            )}
          </div>
          <h2 className="text-sm font-bold text-white mt-1">
            {weeklyMeta?.title || 'Tuần #42 — Thử thách SQL Doanh nghiệp'}
          </h2>
        </div>

        {/* Filters */}
        <div className="space-y-2 mb-3">
          <div className="flex gap-1.5">
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadQuestions()}
              placeholder="Tìm tiêu đề câu hỏi..."
              className="flex-1 px-2.5 py-1.5 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
            />
            <button
              onClick={loadQuestions}
              className="px-3 py-1.5 rounded bg-[#1e2d45] text-xs text-white hover:bg-[#00d4ff] hover:text-[#0a0e17] font-medium"
            >
              Lọc
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {[
              { label: 'Tất cả', val: undefined },
              { label: 'Easy', val: 1 },
              { label: 'Medium', val: 2 },
              { label: 'Hard', val: 3 },
            ].map((b) => (
              <button
                key={b.label}
                onClick={() => setDiffFilter(b.val)}
                className={`px-2.5 py-1 rounded text-[0.7rem] font-mono border transition ${
                  diffFilter === b.val
                    ? 'bg-[#00d4ff]/20 border-[#00d4ff] text-[#00d4ff]'
                    : 'bg-[#0a0e17] border-[#1e2d45] text-[#8ba3c7]'
                }`}
              >
                {b.label}
              </button>
            ))}
            <button
              onClick={() =>
                setSolvedFilter(solvedFilter === undefined ? true : solvedFilter ? false : undefined)
              }
              className="px-2.5 py-1 rounded text-[0.7rem] font-mono border bg-[#0a0e17] border-[#1e2d45] text-[#8ba3c7]"
            >
              {solvedFilter === undefined
                ? 'Trạng thái: Tất cả'
                : solvedFilter
                ? '✓ Đã giải'
                : '○ Chưa giải'}
            </button>
          </div>
        </div>

        {/* Question Items */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {questions.map((q) => {
            const d = DIFF_LABEL[q.difficulty] || DIFF_LABEL[1];
            const active = q.question_id === selectedId;
            return (
              <button
                key={q.question_id}
                onClick={() => setSelectedId(q.question_id)}
                className={`w-full text-left p-3 rounded-lg border transition ${
                  active
                    ? 'bg-[#00d4ff]/10 border-[#00d4ff] shadow-md'
                    : 'bg-[#0a0e17]/80 border-[#1e2d45] hover:border-[#00d4ff]/40'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-mono text-[0.68rem] text-[#5a7298]">
                    Câu #{q.position} · ID {q.question_id}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {q.solved && (
                      <span className="text-[0.65rem] font-mono px-1.5 py-0.5 rounded bg-[#00e5a0]/20 text-[#00e5a0] border border-[#00e5a0]/40">
                        ✓ PASSED
                      </span>
                    )}
                    <span className={`text-[0.65rem] font-mono px-1.5 py-0.5 rounded border ${d.cls}`}>
                      {d.text}
                    </span>
                  </div>
                </div>
                <div className="text-xs font-semibold text-white line-clamp-2">{q.title}</div>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {(q.skills || []).map((sk: any) => (
                    <span
                      key={sk.code}
                      className="text-[0.62rem] font-mono px-1.5 py-0.5 rounded bg-[#1e2d45]/70 text-[#8ba3c7]"
                    >
                      {sk.code}: {sk.name}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right Column: Question Statement + Monaco SQL Workbench + Grading Result */}
      <div className="lg:col-span-8 flex flex-col gap-4">
        {questionDetail ? (
          <div className="bg-[#111827] border border-[#1e2d45] rounded-xl p-5">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs text-[#00d4ff]">
                    QUESTION #{questionDetail.question_id}
                  </span>
                  <span
                    className={`text-xs font-mono px-2 py-0.5 rounded border ${
                      DIFF_LABEL[questionDetail.difficulty]?.cls || ''
                    }`}
                  >
                    {DIFF_LABEL[questionDetail.difficulty]?.text}
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#1e2d45] text-[#8ba3c7]">
                    So khớp: {questionDetail.compare_mode === 'ordered' ? 'Có thứ tự (ORDERED)' : 'Không thứ tự'}
                  </span>
                  {questionDetail.solved && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#00e5a0]/20 text-[#00e5a0] font-semibold">
                      ✓ Đã hoàn thành ({questionDetail.attempt_count} lần nộp)
                    </span>
                  )}
                </div>
                <h1 className="text-lg font-bold text-white">{questionDetail.title}</h1>
              </div>
              <button
                onClick={() => setShowSchema(!showSchema)}
                className="text-xs px-3 py-1.5 rounded-lg border border-[#00d4ff]/40 text-[#00d4ff] hover:bg-[#00d4ff]/10 font-mono"
              >
                {showSchema ? 'Ẩn Schema Enterprise DB' : '🗄️ Xem Schema Enterprise DB (13 bảng)'}
              </button>
            </div>

            <div className="p-3.5 rounded-lg bg-[#0a0e17] border border-[#1e2d45] text-sm text-[#dbe7ff] leading-relaxed whitespace-pre-line">
              {questionDetail.question}
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
              <span className="font-mono text-[#5a7298]">Bảng liên quan:</span>
              {(questionDetail.tables_used || []).map((tb: string) => (
                <code
                  key={tb}
                  className="px-2 py-0.5 rounded bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/25 font-mono"
                >
                  {tb}
                </code>
              ))}
            </div>

            {showSchema && tablesList.length > 0 && (
              <div className="mt-4 pt-3 border-t border-[#1e2d45] max-h-56 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-2">
                {tablesList.map((t: any) => (
                  <div key={t.table} className="p-2.5 rounded bg-[#0a0e17] border border-[#1e2d45]">
                    <div className="font-mono text-xs font-bold text-[#00e5a0] mb-1">
                      public.{t.table}
                    </div>
                    <div className="text-[0.7rem] font-mono text-[#8ba3c7] space-y-0.5">
                      {(t.columns || []).map((c: any) => (
                        <div key={c.name} className="flex justify-between">
                          <span className="text-white">{c.name}</span>
                          <span className="text-[#5a7298]">{c.postgres_type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="bg-[#111827] border border-[#1e2d45] rounded-xl p-6 text-center text-sm text-[#8ba3c7]">
            Đang tải chi tiết câu hỏi...
          </div>
        )}

        {/* Monaco SQL Editor */}
        <div className="bg-[#111827] border border-[#1e2d45] rounded-xl overflow-hidden">
          <div className="px-4 py-2.5 bg-[#0b1120] border-b border-[#1e2d45] flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#00e5a0]" />
              <span className="font-mono text-xs text-white font-semibold">
                PostgreSQL 17 Read-Only Sandbox (sqlarena_ai_ro @ enterprise_db)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleRunSandbox}
                disabled={running || submitting}
                className="px-3.5 py-1.5 rounded-lg bg-[#1e2d45] hover:bg-[#2a3f5f] text-white text-xs font-semibold transition"
              >
                {running ? '⏳ Đang chạy thử...' : '▶ Chạy thử SQL (Không lưu)'}
              </button>
              <button
                onClick={handleSubmitGrade}
                disabled={running || submitting}
                className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-[#00d4ff] to-[#00e5a0] text-[#0a0e17] text-xs font-bold shadow hover:opacity-95 transition"
              >
                {submitting ? '⏳ Đang chấm điểm...' : '🚀 Nộp bài & Chấm Test Case'}
              </button>
            </div>
          </div>

          <div className="h-[250px] border-b border-[#1e2d45]">
            <MonacoEditor
              height="250px"
              defaultLanguage="sql"
              theme="vs-dark"
              value={sql}
              onChange={(val) => setSql(val || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: 'JetBrains Mono, monospace',
                scrollBeyondLastLine: false,
                padding: { top: 12 },
              }}
            />
          </div>

          {/* Execution & Grading Output */}
          <div className="p-4 bg-[#0a0e17]">
            {errorMsg && (
              <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/30 text-red-300 text-xs font-mono">
                ❌ Lỗi thực thi: {errorMsg}
              </div>
            )}

            {output && (
              <div className="space-y-3">
                {output.mode === 'submit' && (
                  <div
                    className={`p-3.5 rounded-lg border flex flex-wrap items-center justify-between gap-2 ${
                      output.passed
                        ? 'bg-[#00e5a0]/10 border-[#00e5a0]/40 text-[#00e5a0]'
                        : 'bg-red-500/10 border-red-500/40 text-red-300'
                    }`}
                  >
                    <div>
                      <div className="text-sm font-bold">
                        {output.passed
                          ? '🎉 CHÍNH XÁC! Vượt qua toàn bộ Test Cases chuẩn (100/100 điểm)'
                          : `❌ CHƯA KHỚP ĐÁP ÁN (${output.submission_status.toUpperCase()})`}
                      </div>
                      {output.error && <div className="text-xs mt-0.5">{output.error}</div>}
                    </div>
                    <div className="font-mono text-xs">
                      Điểm: <strong>{output.score}</strong> · Runtime: <strong>{output.runtime_ms}ms</strong>
                    </div>
                  </div>
                )}

                {output.mode === 'run' && (
                  <div className="flex items-center justify-between text-xs font-mono text-[#00d4ff]">
                    <span>✓ Chạy thử Sandbox thành công (SELECT Read-Only)</span>
                    <span>Số dòng trả về: {output.row_count}</span>
                  </div>
                )}

                {output.columns && output.columns.length > 0 && (
                  <div className="overflow-x-auto max-h-64 border border-[#1e2d45] rounded-lg">
                    <table className="w-full text-left border-collapse text-xs font-mono">
                      <thead>
                        <tr className="bg-[#111827] border-b border-[#1e2d45] text-[#00d4ff]">
                          {output.columns.map((c: string) => (
                            <th key={c} className="px-3 py-2 whitespace-nowrap">
                              {c}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(output.rows || []).slice(0, 30).map((r: any, idx: number) => (
                          <tr key={idx} className="border-b border-[#1e2d45]/50 hover:bg-[#111827]/60">
                            {output.columns.map((c: string) => (
                              <td key={c} className="px-3 py-1.5 text-[#dbe7ff] whitespace-nowrap">
                                {r[c] === null || r[c] === undefined ? (
                                  <span className="text-[#5a7298] italic">NULL</span>
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
                )}
              </div>
            )}

            {!errorMsg && !output && (
              <div className="text-xs font-mono text-[#5a7298]">
                💡 Nhấn &quot;Chạy thử SQL&quot; để kiểm tra kết quả truy vấn trên Enterprise DB, hoặc nhấn &quot;Nộp bài&quot; để hệ thống chấm tự động với bộ Test Case chuẩn.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
