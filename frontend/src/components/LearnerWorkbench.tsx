'use client';

import React, { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  Play,
  Send,
  RotateCcw,
  Table2,
  CheckCircle2,
  AlertCircle,
  Search,
  KeyRound,
  Link2,
} from 'lucide-react';
import {
  getWeeklyCurrent,
  getWeeklyQuestions,
  getQuestionDetail,
  getQuestionSubmissions,
  getDatasetSchema,
  runSandboxSql,
  submitGradingSql,
  extractApiError,
} from '../lib/api';
import { matchesVisibleRecord } from '../lib/search';
import { useTheme } from './theme-provider';
import { QuestionFeedbackBar } from './QuestionFeedbackBar';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const DIFF_META: Record<number, { label: string; shortLabel: string; badge: string }> = {
  1: {
    label: 'Dễ (Mức 1)',
    shortLabel: 'Dễ',
    badge: 'badge-easy',
  },
  2: {
    label: 'Trung bình (Mức 2)',
    shortLabel: 'Trung bình',
    badge: 'badge-medium',
  },
  3: {
    label: 'Khó (Mức 3)',
    shortLabel: 'Khó',
    badge: 'badge-hard',
  },
};

const SKILL_MAP: Record<number, string> = {
  1: 'S1: SELECT / WHERE',
  2: 'S2: JOIN nhiều bảng',
  3: 'S3: GROUP BY / HAVING',
  4: 'S4: Subquery / CTE',
  5: 'S5: Window Functions',
  6: 'S6: Xử lý NULL & ngoại lệ',
};

const DOMAIN_CATEGORIES = [
  'Tài chính & Chi phí',
  'Nhân sự & Phòng ban',
  'Đơn hàng & Doanh thu',
  'Kho vận & Tồn kho',
  'Khách hàng (CRM)',
  'Sản phẩm & Nhà cung cấp',
];

function stripLeadingEmoji(text?: string | null): string {
  if (!text) return '';
  return String(text)
    .replace(/^[^\p{L}\p{N}(["'`]+/u, '')
    .trim();
}

function getDomainCategory(q: any): string {
  if (!q) return 'Nghiệp vụ doanh nghiệp';
  if (q.domain_category && DOMAIN_CATEGORIES.includes(q.domain_category)) {
    return q.domain_category;
  }
  const raw = `${q.domain_category || ''} ${q.topic || ''} ${q.job_topic || ''} ${(q.tables_used || []).join(' ')} ${q.title || ''}`.toLowerCase();
  if (raw.includes('department_expenses') || raw.includes('chi phí') || raw.includes('ngân sách') || raw.includes('finance')) {
    return 'Tài chính & Chi phí';
  }
  if (raw.includes('employees') || raw.includes('salary') || raw.includes('nhân sự') || raw.includes('phòng ban') || raw.includes('lương')) {
    return 'Nhân sự & Phòng ban';
  }
  if (raw.includes('warehouses') || raw.includes('inventory') || raw.includes('stock_movements') || raw.includes('tồn kho') || raw.includes('kho vận')) {
    return 'Kho vận & Tồn kho';
  }
  if (raw.includes('customers') || raw.includes('reviews') || raw.includes('khách hàng') || raw.includes('crm')) {
    return 'Khách hàng (CRM)';
  }
  if (raw.includes('products') || raw.includes('categories') || raw.includes('suppliers') || raw.includes('sản phẩm') || raw.includes('nhà cung cấp')) {
    return 'Sản phẩm & Nhà cung cấp';
  }
  if (raw.includes('orders') || raw.includes('payments') || raw.includes('shipments') || raw.includes('đơn hàng') || raw.includes('doanh thu')) {
    return 'Đơn hàng & Doanh thu';
  }
  return q.domain_category || 'Đơn hàng & Doanh thu';
}

function buildStarterSql(detail: any): string {
  const firstTable = detail?.tables_used?.[0] || 'categories';
  const outCols: string[] = detail?.output_columns || detail?.expected_columns || [];
  if (outCols.length > 0) {
    return `-- Viết câu lệnh SELECT trả về đúng các cột: ${outCols.join(', ')}\nSELECT *\nFROM ${firstTable}\nLIMIT 10;`;
  }
  return `SELECT *\nFROM ${firstTable}\nLIMIT 10;`;
}

function matchesQuestionSearch(q: any, rawQuery: string): boolean {
  if (!rawQuery.trim()) return true;

  const displayPos = Number(q.position || q.question_id || 0);
  const diffMeta = DIFF_META[q.difficulty] || DIFF_META[1];
  const attempted = Boolean(q.attempted) || Number(q.attempt_count ?? q.submission_count ?? 0) > 0;
  const statusLabel = q.solved ? 'Đã giải' : attempted ? 'Chưa làm được' : 'Chưa làm';
  const tablesArr = Array.isArray(q.tables_used) ? q.tables_used : [];
  const visibleTablesStr = [
    ...tablesArr.slice(0, 2),
    tablesArr.length > 2 ? `+${tablesArr.length - 2} bảng` : '',
  ].join(' ');
  const skillsStr = Array.isArray(q.skills) ? q.skills.join(' ') : '';

  return matchesVisibleRecord(
    rawQuery,
    `SQL${displayPos}`,
    q.title || '',
    getDomainCategory(q),
    visibleTablesStr,
    skillsStr,
    diffMeta.shortLabel,
    statusLabel
  );
}

function getSubmissionVerdictBadge(sub: any): { label: string; cls: string } {
  if (sub.submission_status === 'passed' || sub.status === 'accepted' || sub.passed) {
    return { label: 'Làm được', cls: 'badge-easy' };
  }
  const isWrongAnswerMsg =
    typeof sub.error_message === 'string' &&
    sub.error_message.includes('Kết quả truy vấn chưa khớp');
  if (
    sub.submission_status === 'error' ||
    sub.execution_status === 'timeout' ||
    (sub.execution_status === 'error' && sub.submission_status !== 'failed' && !isWrongAnswerMsg)
  ) {
    return { label: 'RTE', cls: 'badge-medium' };
  }
  return { label: 'Chưa làm được', cls: 'badge-hard' };
}

function getDraftStorageKey(qId: number): string {
  return `sqlarena_draft_q_${qId}`;
}

export default function LearnerWorkbench({
  onSubmissionComplete,
}: {
  onSubmissionComplete?: () => void;
}) {
  const { theme } = useTheme();
  const [viewMode, setViewMode] = useState<'list' | 'solve'>('list');
  const [weeklyMeta, setWeeklyMeta] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [questionDetail, setQuestionDetail] = useState<any>(null);
  const [schemaInfo, setSchemaInfo] = useState<any>(null);
  const [showAllSchemaTables, setShowAllSchemaTables] = useState<boolean>(false);

  // Filters (Default collapsed: strictly 1 search row visible)
  const [filtersExpanded, setFiltersExpanded] = useState<boolean>(false);
  const [sourceFilter, setSourceFilter] = useState<'ALL' | 'AI' | 'SEED'>('ALL');
  const [domainFilter, setDomainFilter] = useState<string>('ALL');
  const [sortOrder, setSortOrder] = useState<'difficulty_asc' | 'position_asc' | 'newest_first'>('position_asc');
  const [diffFilter, setDiffFilter] = useState<number | undefined>(undefined);
  const [skillFilter, setSkillFilter] = useState<number | undefined>(undefined);
  const [solvedFilter, setSolvedFilter] = useState<boolean | undefined>(undefined);
  const [searchQ, setSearchQ] = useState('');
  const [appliedSearchQ, setAppliedSearchQ] = useState('');

  // Editor, Draft Persistence & Console
  const [sql, setSql] = useState<string>('SELECT * FROM categories LIMIT 10;');
  const [draftSavedHint, setDraftSavedHint] = useState<boolean>(false);
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [output, setOutput] = useState<any>(null);
  const [qSubs, setQSubs] = useState<any[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [consoleTab, setConsoleTab] = useState<'results' | 'tests' | 'history'>('results');
  const submissionResultRef = useRef<HTMLDivElement | null>(null);

  const updateSqlWithAutosave = (nextValue: string, qIdOverride?: number | null) => {
    setSql(nextValue);
    const activeQid = qIdOverride ?? selectedId;
    if (activeQid && typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(getDraftStorageKey(activeQid), nextValue);
        setDraftSavedHint(true);
      } catch {}
    }
  };

  const loadQuestions = async () => {
    setLoadingList(true);
    try {
      const [meta, qList] = await Promise.all([
        getWeeklyCurrent().catch(() => null),
        getWeeklyQuestions({
          difficulty: diffFilter,
          skill_id: skillFilter,
          solved: solvedFilter,
        }),
      ]);
      if (meta) setWeeklyMeta(meta);
      const items = qList?.items || [];
      setQuestions(items);
      if (
        items.length > 0 &&
        (!selectedId || !items.some((x: any) => x.question_id === selectedId))
      ) {
        setSelectedId(items[0].question_id);
      }
    } catch (e: any) {
      setErrorMsg(extractApiError(e, 'Chưa tải được danh sách bài tập'));
    } finally {
      setLoadingList(false);
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
    setDraftSavedHint(false);

    getQuestionDetail(selectedId)
      .then((d) => {
        setQuestionDetail(d);
        if (typeof window !== 'undefined') {
          const savedDraft = window.localStorage.getItem(getDraftStorageKey(selectedId));
          if (savedDraft && savedDraft.trim().length > 0) {
            setSql(savedDraft);
            setDraftSavedHint(true);
            return;
          }
        }
        setSql(buildStarterSql(d));
      })
      .catch((e) => setErrorMsg(extractApiError(e, 'Không tải được nội dung câu hỏi')));

    getQuestionSubmissions(selectedId)
      .then((r) => setQSubs(r?.items || []))
      .catch(() => setQSubs([]));
  }, [selectedId]);

  const handleOpenQuestion = (qId: number) => {
    setSelectedId(qId);
    setViewMode('solve');
  };

  const handleResetTemplate = () => {
    const starter = buildStarterSql(questionDetail);
    setSql(starter);
    if (selectedId && typeof window !== 'undefined') {
      window.localStorage.setItem(getDraftStorageKey(selectedId), starter);
    }
    setDraftSavedHint(false);
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
      setErrorMsg(extractApiError(e, 'Câu lệnh SQL chưa hợp lệ'));
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
      setOutput({ mode: 'preview', previewTable: tableName, ...res });
    } catch (e: any) {
      setErrorMsg(extractApiError(e, `Không xem trước được dữ liệu bảng ${tableName}`));
    } finally {
      setRunning(false);
    }
  };

  const scrollToSubmissionResult = () => {
    if (typeof window === 'undefined') return;
    window.setTimeout(() => {
      submissionResultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
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
      scrollToSubmissionResult();
      await loadQuestions();
      const [updatedDetail, subsRes] = await Promise.all([
        getQuestionDetail(selectedId),
        getQuestionSubmissions(selectedId).catch(() => ({ items: [] })),
      ]);
      setQuestionDetail(updatedDetail);
      setQSubs(subsRes?.items || []);
      if (onSubmissionComplete) onSubmissionComplete();
    } catch (e: any) {
      setConsoleTab('results');
      setErrorMsg(extractApiError(e, 'Chấm bài không thành công. Hãy kiểm tra lại cú pháp SQL.'));
      scrollToSubmissionResult();
    } finally {
      setSubmitting(false);
    }
  };

  const allTables: any[] =
    schemaInfo?.tables || schemaInfo?.schema_description?.tables || [];
  const usedTableNames: string[] = questionDetail?.tables_used || [];
  const relevantTables =
    usedTableNames.length > 0
      ? allTables.filter((tb: any) => usedTableNames.includes(tb.name || tb.table))
      : allTables.slice(0, 3);
  const displayedTables = showAllSchemaTables ? allTables : relevantTables;

  const activeQuery = searchQ !== appliedSearchQ ? searchQ : appliedSearchQ;

  const filteredQuestions = questions
    .filter((q) => {
      if (sourceFilter === 'AI') {
        const isAi = Boolean(q.source_draft_id) || q.is_source === false;
        if (!isAi) return false;
      } else if (sourceFilter === 'SEED') {
        const isSeed = !q.source_draft_id && q.is_source !== false;
        if (!isSeed) return false;
      }
      if (domainFilter !== 'ALL' && getDomainCategory(q) !== domainFilter) return false;
      if (!matchesQuestionSearch(q, activeQuery)) return false;
      return true;
    })
    .sort((a, b) => {
      const posA = Number(a.position || a.question_id || 0);
      const posB = Number(b.position || b.question_id || 0);
      const diffA = Number(a.difficulty || 1);
      const diffB = Number(b.difficulty || 1);
      if (sortOrder === 'difficulty_asc') {
        if (diffA !== diffB) return diffA - diffB;
        return posA - posB;
      }
      if (sortOrder === 'newest_first') {
        return Number(b.question_id || 0) - Number(a.question_id || 0);
      }
      return posA - posB;
    });

  const currentIdx = filteredQuestions.findIndex((q) => q.question_id === selectedId);
  const prevQuestionId = currentIdx > 0 ? filteredQuestions[currentIdx - 1]?.question_id : null;
  const nextQuestionId =
    currentIdx >= 0 && currentIdx < filteredQuestions.length - 1
      ? filteredQuestions[currentIdx + 1]?.question_id
      : null;

  const activeAdvancedCount =
    (sourceFilter !== 'ALL' ? 1 : 0) +
    (diffFilter !== undefined ? 1 : 0) +
    (domainFilter !== 'ALL' ? 1 : 0) +
    (skillFilter !== undefined ? 1 : 0) +
    (solvedFilter !== undefined ? 1 : 0) +
    (sortOrder !== 'position_asc' ? 1 : 0);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedSearchQ(searchQ.trim());
  };

  // VIEW 1: CLEAN EXERCISE LIST (SINGLE COMPACT SEARCH ROW BY DEFAULT)
  if (viewMode === 'list') {
    return (
      <div className="space-y-4">
        {/* Single-Row Search & Expandable Filter Toolbar */}
        <div className="p-3.5 rounded-xl bg-surface border border-line space-y-3.5">
          <form
            onSubmit={handleSearchSubmit}
            className="flex flex-wrap sm:flex-nowrap items-center gap-2.5"
          >
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 text-muted absolute left-3.5 top-3" />
              <input
                value={searchQ}
                onChange={(e) => {
                  setSearchQ(e.target.value);
                  setAppliedSearchQ(e.target.value);
                }}
                placeholder="Lọc theo từ khóa bất kỳ (số bài, mã SQL, tiêu đề, bảng dữ liệu, kỹ năng…)"
                className="w-full pl-9 pr-9 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink placeholder:text-muted"
              />
              {searchQ && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQ('');
                    setAppliedSearchQ('');
                  }}
                  aria-label="Xóa từ khóa tìm kiếm"
                  className="absolute right-2.5 top-2 px-1.5 py-0.5 rounded text-xs font-semibold text-muted hover:text-ink"
                >
                  ×
                </button>
              )}
            </div>

            <button
              type="submit"
              data-solid-btn="true"
              className="btn-primary px-4 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap shrink-0"
            >
              Tìm kiếm
            </button>

            <button
              type="button"
              onClick={() => setFiltersExpanded((v) => !v)}
              className="btn-subtle px-3.5 min-h-10 rounded-lg text-sm font-medium flex items-center gap-2 whitespace-nowrap shrink-0"
            >
              <SlidersHorizontal className="w-4 h-4 text-muted" />
              <span>{filtersExpanded ? 'Thu gọn' : 'Mở rộng thêm'}</span>
              {activeAdvancedCount > 0 && (
                <span className="badge-info px-2 py-0.5 rounded-full text-xs font-semibold tabular-nums">
                  {activeAdvancedCount}
                </span>
              )}
            </button>
          </form>

          {filtersExpanded && (
            <div className="pt-3.5 border-t border-line space-y-3.5">
              {/* Row 1 inside expanded: Question Source + Difficulty */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-1.5">
                  {[
                    { id: 'ALL', label: 'Tất cả bài tập' },
                    { id: 'AI', label: 'Đề AI mới sinh' },
                    { id: 'SEED', label: 'Đề gốc chuẩn' },
                  ].map((src) => {
                    const active = sourceFilter === src.id;
                    return (
                      <button
                        key={src.id}
                        type="button"
                        data-solid-btn={active ? 'true' : undefined}
                        onClick={() => setSourceFilter(src.id as 'ALL' | 'AI' | 'SEED')}
                        className={`px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap ${
                          active ? 'btn-primary' : 'btn-secondary'
                        }`}
                      >
                        {src.label}
                      </button>
                    );
                  })}
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {[
                    { label: 'Mọi độ khó', val: undefined },
                    { label: 'Dễ', val: 1 },
                    { label: 'Trung bình', val: 2 },
                    { label: 'Khó', val: 3 },
                  ].map((b) => {
                    const active = diffFilter === b.val;
                    return (
                      <button
                        key={b.label}
                        type="button"
                        data-solid-btn={active ? 'true' : undefined}
                        onClick={() => setDiffFilter(b.val)}
                        className={`px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap ${
                          active ? 'btn-primary' : 'btn-secondary'
                        }`}
                      >
                        {b.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Row 2 inside expanded: Domain Topic Tags */}
              <div className="flex flex-wrap items-center gap-1.5">
                {['ALL', ...DOMAIN_CATEGORIES].map((cat) => {
                  const active = domainFilter === cat;
                  return (
                    <button
                      key={cat}
                      type="button"
                      data-solid-btn={active ? 'true' : undefined}
                      onClick={() => setDomainFilter(cat)}
                      className={`px-3 min-h-9 rounded-lg text-xs font-medium whitespace-nowrap ${
                        active ? 'btn-primary' : 'btn-secondary'
                      }`}
                    >
                      {cat === 'ALL' ? 'Tất cả chủ đề' : cat}
                    </button>
                  );
                })}
              </div>

              {/* Row 3 inside expanded: Skill, Status & Sort */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    Nhóm kỹ năng SQL
                  </label>
                  <select
                    value={skillFilter ?? ''}
                    onChange={(e) =>
                      setSkillFilter(e.target.value ? Number(e.target.value) : undefined)
                    }
                    className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  >
                    <option value="">Tất cả kỹ năng (S1 đến S6)</option>
                    {Object.entries(SKILL_MAP).map(([id, label]) => (
                      <option key={id} value={id}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    Trạng thái hoàn thành
                  </label>
                  <select
                    value={
                      solvedFilter === undefined ? '' : solvedFilter ? 'solved' : 'unsolved'
                    }
                    onChange={(e) =>
                      setSolvedFilter(
                        e.target.value === '' ? undefined : e.target.value === 'solved'
                      )
                    }
                    className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  >
                    <option value="">Tất cả trạng thái</option>
                    <option value="unsolved">Chưa hoàn thành</option>
                    <option value="solved">Đã giải đúng</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted mb-1">
                    Sắp xếp
                  </label>
                  <select
                    value={sortOrder}
                    onChange={(e) => setSortOrder(e.target.value as any)}
                    className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  >
                    <option value="difficulty_asc">Từ Dễ đến Khó</option>
                    <option value="position_asc">Theo thứ tự bộ đề</option>
                    <option value="newest_first">Bài mới cập nhật lên đầu</option>
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Exercise Table */}
        <div className="rounded-xl bg-surface border border-line overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm tabular-nums">
              <thead>
                <tr className="bg-soft border-b border-line text-text2 font-semibold">
                  <th className="py-3.5 px-4 w-36">Trạng thái</th>
                  <th className="py-3.5 px-4 w-28">Mã bài</th>
                  <th className="py-3.5 px-4">Tiêu đề câu hỏi</th>
                  <th className="py-3.5 px-4 w-72">Chủ đề &amp; Bảng dữ liệu</th>
                  <th className="py-3.5 px-4 w-36">Độ khó</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {loadingList ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-sm text-muted">
                      Đang tải danh sách câu hỏi…
                    </td>
                  </tr>
                ) : filteredQuestions.length > 0 ? (
                  filteredQuestions.map((q: any) => {
                    const diff = DIFF_META[q.difficulty] || DIFF_META[1];
                    const posNum = q.position || q.question_id;
                    const code = `SQL${posNum}`;
                    const domainCat = getDomainCategory(q);
                    const tablesArr = Array.isArray(q.tables_used) ? q.tables_used : [];
                    return (
                      <tr
                        key={q.question_id}
                        tabIndex={0}
                        onClick={() => handleOpenQuestion(q.question_id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleOpenQuestion(q.question_id);
                          }
                        }}
                        className="hover:bg-soft cursor-pointer transition-colors"
                      >
                        <td className="py-3.5 px-4">
                          {q.solved ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md badge-easy text-xs font-semibold">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Đã giải</span>
                            </span>
                          ) : q.attempted || Number(q.attempt_count ?? q.submission_count ?? 0) > 0 ? (
                            <span className="inline-block px-2.5 py-1 rounded-md badge-hard text-xs font-semibold">
                              Chưa làm được
                            </span>
                          ) : (
                            <span className="inline-block px-2.5 py-1 rounded-md badge-neutral text-xs font-medium">
                              Chưa làm
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <code className="text-sm font-bold text-brand">{code}</code>
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-ink text-sm leading-snug">
                            {q.title}
                          </div>
                          {Array.isArray(q.skills) && q.skills.length > 0 && (
                            <div className="text-xs text-muted mt-1">
                              Kỹ năng: {q.skills.join(', ')}
                            </div>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="px-2 py-0.5 rounded-md badge-neutral text-xs font-medium">
                              {domainCat}
                            </span>
                            {tablesArr.slice(0, 2).map((tb: string) => (
                              <code
                                key={tb}
                                className="px-2 py-0.5 rounded bg-canvas border border-line text-xs text-text2"
                              >
                                {tb}
                              </code>
                            ))}
                            {tablesArr.length > 2 && (
                              <span className="text-xs text-muted">
                                +{tablesArr.length - 2} bảng
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-block px-2.5 py-1 rounded-md text-xs font-semibold ${diff.badge}`}
                          >
                            {diff.shortLabel}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-sm text-muted">
                      Không có bài tập nào khớp với bộ lọc hiện tại. Hãy thử chọn lại &quot;Tất cả&quot; độ khó.
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

  // VIEW 2: SOLVE WORKSPACE (LEFT: PROBLEM + PK/FK SCHEMA, RIGHT: EDITOR + AI COACH/EXPLAIN + CONSOLE)
  const activeListItem = questions.find((q) => q.question_id === selectedId);
  const mergedQ = { ...(activeListItem || {}), ...(questionDetail || {}) };
  const diff = DIFF_META[mergedQ?.difficulty || 1] || DIFF_META[1];
  const qCode = `SQL${mergedQ?.position || selectedId || 1}`;
  const detailDomain = getDomainCategory(mergedQ);
  const outputColumns: string[] =
    questionDetail?.output_columns || questionDetail?.expected_columns || [];

  return (
    <div className="space-y-4">
      {/* Solve Header Navigation */}
      <div className="p-3.5 rounded-xl bg-surface border border-line flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => setViewMode('list')}
            className="btn-subtle px-3.5 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Danh sách đề bài</span>
          </button>
          <code className="px-2.5 py-1 rounded-md bg-soft border border-line text-sm font-bold text-brand">
            {qCode}
          </code>
          <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${diff.badge}`}>
            {diff.label}
          </span>
          <span className="px-2.5 py-1 rounded-md badge-neutral text-xs font-medium">
            {detailDomain}
          </span>
          {mergedQ?.solved && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md badge-easy text-xs font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Đã hoàn thành</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => prevQuestionId && setSelectedId(prevQuestionId)}
            disabled={!prevQuestionId}
            className="btn-secondary px-3 min-h-10 rounded-lg text-sm font-medium flex items-center gap-1 disabled:opacity-40"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Bài trước</span>
          </button>
          <button
            type="button"
            onClick={() => nextQuestionId && setSelectedId(nextQuestionId)}
            disabled={!nextQuestionId}
            className="btn-secondary px-3 min-h-10 rounded-lg text-sm font-medium flex items-center gap-1 disabled:opacity-40"
          >
            <span>Bài tiếp</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main 2-Column Dense Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Problem Statement + Output Columns + Inline PK/FK Schema */}
        <div className="lg:col-span-5">
          <div className="p-5 rounded-xl bg-surface border border-line space-y-4">
            <h1 className="text-xl font-bold text-ink leading-snug">
              {questionDetail?.title || 'Đang tải nội dung bài tập...'}
            </h1>

            <div className="text-base text-ink leading-relaxed whitespace-pre-line">
              {questionDetail?.question || ''}
            </div>

            {outputColumns.length > 0 && (
              <div className="p-3.5 rounded-xl bg-soft border border-line space-y-2.5">
                <div className="text-sm font-semibold text-ink">
                  Cột kết quả cần trả về theo thứ tự:
                </div>
                <div className="flex flex-wrap gap-2">
                  {outputColumns.map((col: string, idx: number) => (
                    <code
                      key={`${col}-${idx}`}
                      className="px-2.5 py-1 rounded-md bg-surface border border-line text-sm font-semibold text-brand"
                    >
                      {idx + 1}. {col}
                    </code>
                  ))}
                </div>
              </div>
            )}

            <QuestionFeedbackBar
              questionId={questionDetail?.question_id || selectedId}
              feedback={questionDetail?.feedback}
              onFeedbackUpdated={() => {
                if (selectedId) {
                  getQuestionDetail(selectedId)
                    .then((d) => setQuestionDetail(d))
                    .catch(() => {});
                }
              }}
            />

            {/* Inline Schema Explorer right inside the Problem Statement Card */}
            <div className="pt-3 border-t border-line space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Table2 className="w-4 h-4 text-brand" />
                  <span className="text-sm font-bold text-ink">
                    Sơ đồ bảng dữ liệu ({displayedTables.length})
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    data-solid-btn={!showAllSchemaTables ? 'true' : undefined}
                    onClick={() => setShowAllSchemaTables(false)}
                    className={`px-2.5 min-h-8 rounded-md text-xs font-medium ${
                      !showAllSchemaTables ? 'btn-primary' : 'btn-secondary'
                    }`}
                  >
                    Bảng của bài ({relevantTables.length})
                  </button>
                  <button
                    type="button"
                    data-solid-btn={showAllSchemaTables ? 'true' : undefined}
                    onClick={() => setShowAllSchemaTables(true)}
                    className={`px-2.5 min-h-8 rounded-md text-xs font-medium ${
                      showAllSchemaTables ? 'btn-primary' : 'btn-secondary'
                    }`}
                  >
                    Tất cả ({allTables.length})
                  </button>
                </div>
              </div>

              <p className="text-xs text-muted">
                Các bảng dữ liệu sử dụng trong đề bài. Bấm vào tên bảng để xem nhanh 5 dòng dữ liệu mẫu.
              </p>

              <div className="space-y-2.5">
                {displayedTables.map((tb: any) => {
                  const tableName = tb.name || tb.table || 'table';
                  const cols = tb.columns || [];
                  return (
                    <div
                      key={tableName}
                      className="rounded-lg border border-line bg-canvas overflow-hidden"
                    >
                      <div className="px-3.5 py-2 bg-soft border-b border-line flex items-center justify-between gap-2">
                        <button
                          type="button"
                          onClick={() => handlePreviewTable(tableName)}
                          className="text-left flex items-center gap-2 hover:text-brand font-semibold text-sm text-ink min-h-8"
                          title={`Xem 5 dòng mẫu của bảng ${tableName}`}
                        >
                          <code className="font-bold">{tableName}</code>
                          {tb.row_count !== undefined && (
                            <span className="text-xs text-muted font-normal tabular-nums">
                              ({tb.row_count} dòng)
                            </span>
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => handlePreviewTable(tableName)}
                          className="btn-secondary px-2.5 min-h-8 rounded-md text-xs font-medium"
                        >
                          Xem 5 dòng mẫu
                        </button>
                      </div>
                      <div className="p-2.5 space-y-1.5">
                        {cols.map((c: any) => {
                          const isPk = Boolean(c.pk || c.is_primary_key);
                          const fkTarget = c.references || c.fk || null;
                          return (
                            <div
                              key={c.name}
                              className="flex flex-wrap items-center justify-between gap-2 px-2.5 py-1.5 rounded-md bg-surface border border-line text-sm"
                            >
                              <div className="flex flex-wrap items-center gap-1.5">
                                <code className="font-medium text-ink text-sm">{c.name}</code>
                                {isPk && (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded badge-medium text-xs font-semibold">
                                    <KeyRound className="w-3 h-3" />
                                    <span>PK</span>
                                  </span>
                                )}
                                {fkTarget && (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded badge-info text-xs font-medium">
                                    <Link2 className="w-3 h-3" />
                                    <span>FK -&gt; {fkTarget}</span>
                                  </span>
                                )}
                              </div>
                              <code className="text-xs text-muted">{c.type}</code>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: SQL Editor + Learning Assistant + Results Console */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-xl bg-surface border border-line overflow-hidden">
            {/* Editor Action Bar */}
            <div className="px-4 py-3 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2.5">
                <code className="text-sm font-semibold text-ink">query.sql</code>
                {draftSavedHint && (
                  <span className="text-xs text-muted">Đã tự lưu nháp trên trình duyệt</span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleResetTemplate}
                  className="btn-secondary px-3 min-h-10 rounded-lg text-sm font-medium flex items-center gap-1.5"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Đặt lại SQL mẫu</span>
                </button>
                <button
                  type="button"
                  data-solid-btn="true"
                  onClick={handleRunSandbox}
                  disabled={running || submitting}
                  className="btn-copper px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Play className="w-4 h-4" />
                  <span>{running ? 'Đang chạy...' : 'Chạy thử'}</span>
                </button>
                <button
                  type="button"
                  data-solid-btn="true"
                  onClick={handleSubmitGrade}
                  disabled={submitting || running}
                  className="btn-primary px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  <span>{submitting ? 'Đang chấm...' : 'Nộp bài'}</span>
                </button>
              </div>
            </div>

            {/* Monaco SQL Editor */}
            <div className="h-[340px] border-b border-line">
              <MonacoEditor
                height="100%"
                defaultLanguage="sql"
                theme={theme === 'dark' ? 'vs-dark' : 'light'}
                value={sql}
                onChange={(v) => updateSqlWithAutosave(v || '')}
                options={{
                  automaticLayout: true,
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineHeight: 20,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  padding: { top: 12, bottom: 12 },
                }}
              />
            </div>

            {/* Console Tabs (Pure SQL Execution, Test Cases & Submission History) */}
            <div
              ref={submissionResultRef}
              className="px-4 py-2 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-2 scroll-mt-4"
            >
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: 'results', label: 'Kết quả chạy & Nộp bài' },
                  { id: 'tests', label: 'Chi tiết Test Cases' },
                  { id: 'history', label: `Lịch sử nộp (${qSubs.length})` },
                ].map((t) => {
                  const active = consoleTab === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      data-solid-btn={active ? 'true' : undefined}
                      onClick={() => setConsoleTab(t.id as any)}
                      className={`px-3 min-h-9 rounded-lg text-xs font-semibold ${
                        active ? 'btn-primary' : 'text-text2 hover:text-ink hover:bg-surface'
                      }`}
                    >
                      {t.label}
                    </button>
                  );
                })}
              </div>
              {output?.runtime_ms !== undefined && (
                <span className="text-xs text-muted tabular-nums">
                  Thời gian thực thi: {output.runtime_ms} ms
                </span>
              )}
            </div>

            {/* Console Body */}
            <div className="p-4 space-y-3">
              {errorMsg && (
                <div className="p-3.5 rounded-xl badge-hard text-sm flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* TAB: RESULTS & SUBMISSION VERDICT */}
              {consoleTab === 'results' && (
                <div className="space-y-3 text-sm">
                  {output?.mode === 'submit' && (() => {
                    const submitVerdict = getSubmissionVerdictBadge({
                      submission_status: output.submission_status,
                      passed: output.passed,
                      error_message: output.error,
                    });
                    const submitCases: any[] = Array.isArray(output.test_cases)
                      ? output.test_cases
                      : [];
                    return (
                      <div className="space-y-3">
                        <div
                          className={`p-4 rounded-xl flex flex-wrap items-center justify-between gap-2 ${submitVerdict.cls}`}
                        >
                          <div className="font-bold">
                            {submitVerdict.label === 'Làm được'
                              ? 'Thông báo kết quả nộp bài: Làm được — Vượt qua toàn bộ bộ kiểm thử!'
                              : submitVerdict.label === 'RTE'
                              ? 'Thông báo kết quả nộp bài: Chưa làm được (Lỗi thực thi SQL trên PostgreSQL 17).'
                              : 'Thông báo kết quả nộp bài: Chưa làm được — Kết quả chưa khớp với toàn bộ test case.'}
                          </div>
                          <div className="font-semibold tabular-nums">
                            Đạt {output.passed_AutoTests ?? output.passed_tests ?? 0}/
                            {output.total_AutoTests ?? output.total_tests ?? submitCases.length} test case
                          </div>
                        </div>

                        {submitCases.length > 0 && (
                          <div className="p-3.5 rounded-xl bg-canvas border border-line space-y-2">
                            <div className="text-sm font-bold text-ink">
                              Kết quả chấm từng Test Case
                            </div>
                            <div className="space-y-2">
                              {submitCases.map((tc: any, idx: number) => {
                                const caseLabel = tc.label || `Test case ${tc.test_number || idx + 1}`;
                                return (
                                  <div
                                    key={`${tc.test_id || 'tc'}-${tc.test_number || idx}`}
                                    className="p-2.5 rounded-lg bg-surface border border-line flex flex-wrap items-center justify-between gap-2"
                                  >
                                    <div className="flex flex-wrap items-center gap-2">
                                      <span
                                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                                          tc.passed ? 'badge-easy' : 'badge-hard'
                                        }`}
                                      >
                                        {tc.passed ? (
                                          <CheckCircle2 className="w-3.5 h-3.5" />
                                        ) : (
                                          <AlertCircle className="w-3.5 h-3.5" />
                                        )}
                                        <span>
                                          {caseLabel}: {tc.passed ? 'Đúng' : 'Sai'}
                                        </span>
                                      </span>
                                      {tc.title && (
                                        <span className="text-xs font-medium text-ink">
                                          {tc.title}
                                        </span>
                                      )}
                                    </div>
                                    {tc.diagnostic_hint && (
                                      <span className="text-xs text-text2">
                                        {tc.diagnostic_hint}
                                      </span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}

                  {output?.mode === 'preview' && output?.previewTable && (
                    <div className="px-3 py-2 rounded-lg badge-info text-xs font-semibold">
                      Đang hiển thị 5 dòng dữ liệu mẫu của bảng <code>{output.previewTable}</code>
                    </div>
                  )}

                  {output?.error && output?.mode !== 'submit' && (
                    <div className="p-3.5 rounded-xl badge-hard text-sm">
                      <span>{output.error}</span>
                    </div>
                  )}

                  {output?.rows ? (
                    <div className="space-y-2">
                      <div className="text-xs text-muted tabular-nums">
                        Trả về {output.row_count ?? output.rows.length} dòng dữ liệu
                      </div>
                      {output.rows.length > 0 ? (
                        <div className="overflow-x-auto border border-line rounded-lg">
                          <table className="w-full text-left border-collapse text-sm tabular-nums">
                            <thead>
                              <tr className="bg-soft border-b border-line text-ink font-semibold">
                                {(output.columns || Object.keys(output.rows[0] || {})).map(
                                  (col: string) => (
                                    <th
                                      key={col}
                                      className="px-3 py-2.5 border-r border-line last:border-r-0 font-mono text-xs"
                                    >
                                      {col}
                                    </th>
                                  )
                                )}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-line">
                              {output.rows.slice(0, 50).map((row: any, rIdx: number) => (
                                <tr key={rIdx} className="hover:bg-soft">
                                  {(output.columns || Object.keys(output.rows[0] || {})).map(
                                    (col: string, cIdx: number) => {
                                      const val = Array.isArray(row) ? row[cIdx] : row[col];
                                      return (
                                        <td
                                          key={col}
                                          className="px-3 py-2 border-r border-line last:border-r-0 text-ink text-sm"
                                        >
                                          {val === null || val === undefined ? (
                                            <code className="text-xs text-muted">NULL</code>
                                          ) : (
                                            String(val)
                                          )}
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
                        <div className="p-5 text-center text-sm text-muted bg-canvas rounded-lg border border-line">
                          Câu lệnh hợp lệ nhưng không có dòng dữ liệu nào thỏa mãn điều kiện (0 dòng).
                        </div>
                      )}
                    </div>
                  ) : (
                    !output &&
                    !errorMsg && (
                      <div className="py-8 text-center text-sm text-muted">
                        Bấm <strong>Chạy thử</strong> để kiểm tra bảng kết quả hoặc bấm{' '}
                        <strong>Nộp bài</strong> để chấm điểm tự động.
                      </div>
                    )
                  )}
                </div>
              )}

              {/* TAB: TEST CASES */}
              {consoleTab === 'tests' && (
                <div className="space-y-3 text-sm">
                  {output?.test_cases?.length > 0 ? (
                    output.test_cases.map((tc: any, idx: number) => {
                      const caseLabel = tc.label || `Test case ${tc.test_number || idx + 1}`;
                      return (
                        <div
                          key={`${tc.test_id || 'tc'}-${tc.test_number || idx}`}
                          className="p-3.5 rounded-xl bg-canvas border border-line space-y-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span
                              className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                                tc.passed ? 'badge-easy' : 'badge-hard'
                              }`}
                            >
                              {caseLabel}: {tc.passed ? 'Đúng' : 'Sai'}
                              {tc.title ? ` · ${tc.title}` : ''}
                            </span>
                            <span className="text-xs text-text2 tabular-nums">
                              Số dòng chuẩn:{' '}
                              <strong>{tc.target_rows ?? tc.expected_rows ?? '—'}</strong> | Thực
                              tế: <strong>{tc.actual_rows ?? '—'}</strong>
                            </span>
                          </div>
                          {tc.diagnostic_hint && (
                            <div className="p-2.5 rounded-lg bg-surface border border-line text-sm text-text2">
                              Chi tiết: {tc.diagnostic_hint}
                            </div>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <div className="py-8 text-center text-sm text-muted">
                      Bấm <strong>Nộp bài</strong> để xem kết quả đối chiếu từng bộ kiểm thử.
                    </div>
                  )}
                </div>
              )}

              {/* TAB: SUBMISSION HISTORY */}
              {consoleTab === 'history' && (
                <div className="space-y-2.5 text-sm">
                  {qSubs.length > 0 ? (
                    qSubs.map((sub: any) => {
                      const verdict = getSubmissionVerdictBadge(sub);
                      return (
                        <div
                          key={sub.submission_id}
                          className="p-3 rounded-xl bg-canvas border border-line flex flex-wrap items-center justify-between gap-2 tabular-nums"
                        >
                          <div className="flex flex-wrap items-center gap-2.5">
                            <span
                              className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${verdict.cls}`}
                            >
                              {verdict.label}
                            </span>
                            <span className="text-xs text-muted">{sub.runtime_ms ?? 0} ms</span>
                            <span className="text-xs text-muted">
                              {sub.submitted_at
                                ? new Date(sub.submitted_at).toLocaleString('vi-VN')
                                : ''}
                            </span>
                          </div>
                          {sub.submitted_sql && (
                            <button
                              type="button"
                              onClick={() => updateSqlWithAutosave(sub.submitted_sql)}
                              className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                            >
                              Nạp lại câu lệnh này
                            </button>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <div className="py-8 text-center text-sm text-muted">
                      Bạn chưa có lượt nộp bài nào cho câu hỏi này.
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
