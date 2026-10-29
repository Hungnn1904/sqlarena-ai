'use client';

import React, { useEffect, useState } from 'react';
import {
  GitPullRequest,
  Cpu,
  CalendarRange,
  Users,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertTriangle,
  Search,
  Lock,
  Unlock,
  UserCog,
  Database,
  Settings,
} from 'lucide-react';
import {
  getGenerationJobs,
  createGenerationJob,
  getLlmUsage,
  getAdminDrafts,
  getAdminDraftDetail,
  editAdminDraft,
  approveAdminDraft,
  rejectAdminDraft,
  requeueAdminDraft,
  getAdminQuestions,
  retireAdminQuestion,
  restoreAdminQuestion,
  toggleAdminQuestionSource,
  getAdminWeeklySets,
  createAdminWeeklySet,
  publishAdminWeeklySet,
  closeAdminWeeklySet,
  getAdminUsers,
  updateAdminUser,
  getAdminSettings,
  updateAdminSetting,
} from '../lib/api';

const SKILL_OPTIONS = [
  { id: 1, code: 'S1', name: 'SELECT / WHERE' },
  { id: 2, code: 'S2', name: 'JOIN Multi-Table' },
  { id: 3, code: 'S3', name: 'GROUP BY / HAVING' },
  { id: 4, code: 'S4', name: 'Subquery / CTE' },
  { id: 5, code: 'S5', name: 'Window Functions' },
  { id: 6, code: 'S6', name: 'Edge Cases & NULL' },
];

export default function AdminPortal({ isAdmin }: { isAdmin: boolean }) {
  const [subTab, setSubTab] = useState<
    'drafts' | 'questions' | 'jobs' | 'weekly' | 'users' | 'settings'
  >('drafts');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Drafts
  const [draftStatus, setDraftStatus] = useState<string>('');
  const [drafts, setDrafts] = useState<any[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<any>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editQuestion, setEditQuestion] = useState('');
  const [reviewNote, setReviewNote] = useState('');

  // Live Questions Bank
  const [qStatusFilter, setQStatusFilter] = useState<string>('');
  const [liveQuestions, setLiveQuestions] = useState<any[]>([]);

  // Jobs
  const [jobs, setJobs] = useState<any[]>([]);
  const [llmUsage, setLlmUsage] = useState<any>(null);
  const [jobDiff, setJobDiff] = useState(2);
  const [jobCount, setJobCount] = useState(3);
  const [jobTopic, setJobTopic] = useState(
    'Phân tích doanh thu theo danh mục và tỷ lệ hoàn tiền quý 1/2025'
  );
  const [jobSkills, setJobSkills] = useState<number[]>([2, 3]);

  // Weekly, Users & Settings
  const [weeklySets, setWeeklySets] = useState<any[]>([]);
  const [newWeekTitle, setNewWeekTitle] = useState('Bộ đề tuần SQL nâng cao');
  const [newWeekStart, setNewWeekStart] = useState('2026-11-02');
  const [users, setUsers] = useState<any[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [settingsList, setSettingsList] = useState<any[]>([]);
  const [settingEdits, setSettingEdits] = useState<Record<string, string>>({});

  const loadDrafts = async () => {
    try {
      const r = await getAdminDrafts({ status: draftStatus || undefined });
      setDrafts(r.items || []);
      if (r.items?.length > 0 && !selectedDraft) {
        inspectDraft(r.items[0].draft_id);
      }
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Cần quyền Quản trị viên (Admin)');
    }
  };

  const inspectDraft = async (draftId: number) => {
    try {
      const d = await getAdminDraftDetail(draftId);
      setSelectedDraft(d);
      setEditTitle(d.title || '');
      setEditQuestion(d.question || '');
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Không tải được chi tiết bản nháp');
    }
  };

  const loadJobs = async () => {
    try {
      const [j, u] = await Promise.all([getGenerationJobs(), getLlmUsage()]);
      setJobs(j.items || []);
      setLlmUsage(u);
    } catch {}
  };

  const loadWeekly = async () => {
    try {
      const w = await getAdminWeeklySets();
      setWeeklySets(w.items || []);
    } catch {}
  };

  const loadUsers = async () => {
    try {
      const u = await getAdminUsers({ q: userSearch || undefined });
      setUsers(u.items || []);
    } catch {}
  };

  const loadLiveQuestions = async () => {
    try {
      const q = await getAdminQuestions({ status: qStatusFilter || undefined });
      setLiveQuestions(q.items || []);
    } catch {}
  };

  const loadSettings = async () => {
    try {
      const s = await getAdminSettings();
      const items = s.items || [];
      setSettingsList(items);
      const map: Record<string, string> = {};
      items.forEach((it: any) => {
        map[it.key] =
          typeof it.value === 'string' ? it.value : JSON.stringify(it.value);
      });
      setSettingEdits(map);
    } catch {}
  };

  useEffect(() => {
    if (!isAdmin) return;
    setErr(null);
    if (subTab === 'drafts') loadDrafts();
    if (subTab === 'questions') loadLiveQuestions();
    if (subTab === 'jobs') loadJobs();
    if (subTab === 'weekly') loadWeekly();
    if (subTab === 'users') loadUsers();
    if (subTab === 'settings') loadSettings();
  }, [subTab, draftStatus, qStatusFilter, isAdmin]);

  if (!isAdmin) {
    return (
      <div className="bg-[#0d1321] border border-amber-900/50 rounded-lg p-8 text-center space-y-3">
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-amber-950/60 border border-amber-800/60 text-amber-400">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="text-sm font-semibold text-white">
          Phân hệ Quản trị & Kiểm duyệt yêu cầu quyền Admin
        </div>
        <p className="text-xs text-[#94a3b8] max-w-md mx-auto leading-relaxed">
          Tài khoản hiện tại đang ở vai trò Học viên. Bạn có thể chuyển sang quyền quản trị bằng nút{' '}
          <strong className="text-amber-300 font-mono">Admin (admin)</strong> trên thanh trạng thái phía trên.
        </p>
      </div>
    );
  }

  const toggleSkill = (id: number) => {
    setJobSkills((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    try {
      const job = await createGenerationJob({
        difficulty: jobDiff,
        skill_ids: jobSkills.length ? jobSkills : [2],
        requested_count: jobCount,
        topic: jobTopic,
      });
      setMsg(
        `Đã khởi tạo Generation Job #${job.job_id} vào hàng đợi worker (status: ${job.status}).`
      );
      loadJobs();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi tạo job sinh đề');
    }
  };

  const handleApproveDraft = async () => {
    if (!selectedDraft) return;
    setMsg(null);
    setErr(null);
    try {
      const firstRunId = selectedDraft.self_solve_runs?.[0]?.run_id;
      const d = await approveAdminDraft(selectedDraft.draft_id, {
        selected_run_id: firstRunId,
        note: reviewNote || 'Admin xác nhận thông qua',
      });
      setSelectedDraft(d);
      setMsg(
        `Đã phê duyệt Draft #${d.draft_id} và chuyển vào ngân hàng đề live.questions.`
      );
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi phê duyệt');
    }
  };

  const handleRejectDraft = async () => {
    if (!selectedDraft) return;
    setMsg(null);
    setErr(null);
    try {
      const d = await rejectAdminDraft(
        selectedDraft.draft_id,
        reviewNote || 'Không đạt tiêu chuẩn kiểm định'
      );
      setSelectedDraft(d);
      setMsg(`Đã từ chối Draft #${d.draft_id}.`);
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi từ chối draft');
    }
  };

  const handleEditDraft = async () => {
    if (!selectedDraft) return;
    setMsg(null);
    setErr(null);
    try {
      const d = await editAdminDraft(selectedDraft.draft_id, {
        title: editTitle,
        question: editQuestion,
        note: reviewNote || 'Hiệu đính nội dung đề bài',
      });
      setSelectedDraft(d);
      setMsg(`Đã lưu hiệu đính Draft #${d.draft_id} và đưa lại hàng đợi kiểm duyệt.`);
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi lưu bản nháp');
    }
  };

  const handleRequeueDraft = async () => {
    if (!selectedDraft) return;
    setMsg(null);
    setErr(null);
    try {
      const d = await requeueAdminDraft(
        selectedDraft.draft_id,
        reviewNote || 'Đưa lại vào hàng đợi kiểm định tự động'
      );
      setSelectedDraft(d);
      setMsg(`Đã Requeue Draft #${d.draft_id} (status: ${d.status}).`);
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi requeue draft');
    }
  };

  const handleCreateWeeklySet = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    try {
      const w = await createAdminWeeklySet({
        title: newWeekTitle,
        week_start: newWeekStart,
      });
      setMsg(`Đã tạo bộ đề tuần mới #${w.set_id} (${w.title}).`);
      loadWeekly();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Không tạo được bộ đề tuần');
    }
  };

  const handleUpdateSetting = async (key: string) => {
    setMsg(null);
    setErr(null);
    try {
      const raw = settingEdits[key] ?? '';
      let parsed: any = raw;
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = raw;
      }
      await updateAdminSetting(key, parsed);
      setMsg(`Đã cập nhật cấu hình ${key}.`);
      loadSettings();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi cập nhật cấu hình');
    }
  };

  const handleToggleUser = async (u: any, field: 'role' | 'status') => {
    try {
      const payload =
        field === 'role'
          ? { role: (u.role === 'admin' ? 'learner' : 'admin') as 'learner' | 'admin' }
          : {
              status: (u.status === 'active' ? 'locked' : 'active') as
                | 'active'
                | 'locked',
            };
      await updateAdminUser(u.user_id, payload);
      setMsg(`Đã cập nhật cấu hình tài khoản @${u.username}.`);
      loadUsers();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Không thể cập nhật tài khoản');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2 pb-1">
        <div>
          <div className="text-[11px] font-bold tracking-[0.15em] uppercase text-[var(--copper)]">
            QUẢN TRỊ HỆ THỐNG
          </div>
          <h2 className="text-2xl font-bold text-[var(--ink)] mt-0.5">
            Điều phối &amp; <span className="editorial-serif text-[var(--green)]">duyệt đề AI.</span>
          </h2>
        </div>

        {/* Sub-navigation Bar */}
        <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg p-1 flex flex-wrap items-center gap-1">
          {[
            {
              id: 'drafts',
              label: `Duyệt đề (${drafts.length})`,
              icon: GitPullRequest,
            },
            { id: 'questions', label: 'Ngân hàng đề', icon: Database },
            { id: 'jobs', label: 'Sinh đề AI', icon: Cpu },
            { id: 'weekly', label: 'Bộ đề tuần', icon: CalendarRange },
            { id: 'users', label: 'Người dùng', icon: Users },
            { id: 'settings', label: 'Cấu hình', icon: Settings },
          ].map((t) => {
            const Icon = t.icon;
            const active = subTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setSubTab(t.id as any)}
                className={`px-3 py-1.5 rounded text-xs font-medium flex items-center gap-1.5 transition ${
                  active
                    ? 'bg-[#162238] text-white border border-[#293f66]'
                    : 'text-[#64748b] hover:text-white border border-transparent'
                }`}
              >
                <Icon className="w-3.5 h-3.5 text-[#38bdf8]" />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {err && (
        <div className="p-3 rounded bg-red-950/40 border border-red-900/60 text-red-300 text-xs font-mono">
          {err}
        </div>
      )}
      {msg && (
        <div className="p-3 rounded bg-emerald-950/40 border border-emerald-900/60 text-emerald-300 text-xs font-mono">
          {msg}
        </div>
      )}

      {/* TAB 1: DRAFT REVIEW */}
      {subTab === 'drafts' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left Queue */}
          <div className="lg:col-span-4 bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
            <div className="p-3.5 bg-[#090d16] border-b border-[#1d283a] flex items-center justify-between">
              <span className="text-xs font-semibold text-white">
                Bản nháp ({drafts.length})
              </span>
              <select
                value={draftStatus}
                onChange={(e) => setDraftStatus(e.target.value)}
                className="px-2.5 py-1 rounded bg-[#0d1321] border border-[#22304a] text-xs text-[#cbd5e1] font-mono"
              >
                <option value="">Tất cả</option>
                <option value="needs_human">Cần duyệt</option>
                <option value="pending">Đang chờ</option>
                <option value="approved">Đã duyệt</option>
                <option value="rejected">Từ chối</option>
              </select>
            </div>

            <div className="divide-y divide-[#162032] max-h-[640px] overflow-y-auto">
              {drafts.map((d) => {
                const active = selectedDraft?.draft_id === d.draft_id;
                const statusBadge =
                  d.status === 'needs_human'
                    ? 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                    : d.status === 'approved'
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                    : 'bg-slate-900 text-slate-400 border-slate-800';
                return (
                  <button
                    key={d.draft_id}
                    onClick={() => inspectDraft(d.draft_id)}
                    className={`w-full text-left p-3.5 transition ${
                      active
                        ? 'bg-[#141f35] border-l-2 border-l-[#38bdf8]'
                        : 'hover:bg-[#101829]'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono mb-1">
                      <span className="text-[#64748b]">
                        DRAFT #{d.draft_id} · L{d.difficulty}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded border ${statusBadge}`}>
                        {d.status}
                      </span>
                    </div>
                    <div className="text-xs font-medium text-white line-clamp-2">
                      {d.title}
                    </div>
                    {d.status_reason && (
                      <div className="text-[11px] text-[#64748b] mt-1 line-clamp-2 font-mono">
                        {d.status_reason}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Inspector */}
          <div className="lg:col-span-8 bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
            {selectedDraft ? (
              <>
                <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-[11px] font-mono text-[#64748b]">
                      DRAFT REVIEW INSPECTOR · ID #{selectedDraft.draft_id}
                    </div>
                    <div className="text-sm font-semibold text-white mt-0.5">
                      Generator: {selectedDraft.gen_model} ({selectedDraft.gen_prompt_version})
                    </div>
                  </div>
                  <span className="font-mono text-xs px-2.5 py-1 rounded bg-[#131c2e] border border-[#22304a] text-[#38bdf8]">
                    STATUS: {selectedDraft.status.toUpperCase()}
                  </span>
                </div>

                <div className="p-5 space-y-4">
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-mono text-[#94a3b8] mb-1">
                        Tiêu đề bài tập
                      </label>
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-[#94a3b8] mb-1">
                        Nội dung đặc tả đề bài (Tiếng Việt)
                      </label>
                      <textarea
                        rows={3}
                        value={editQuestion}
                        onChange={(e) => setEditQuestion(e.target.value)}
                        className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white leading-relaxed"
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-xs font-mono text-[#94a3b8] mb-1.5">
                      <span>Lời giải SQL tham chiếu & Kết quả đối sánh Model B</span>
                      <span>
                        Self-solve runs: {selectedDraft.self_solve_runs?.length || 0}
                      </span>
                    </div>
                    <pre className="p-3.5 rounded bg-[#080c14] border border-[#182235] text-xs font-mono text-[#cbd5e1] overflow-x-auto leading-relaxed">
                      {selectedDraft.reference_sql ||
                        selectedDraft.self_solve_runs?.[0]?.model_sql ||
                        '-- Chưa có SQL'}
                    </pre>
                  </div>

                  {selectedDraft.self_solve_runs?.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {selectedDraft.self_solve_runs.map((run: any) => (
                        <div
                          key={run.run_id}
                          className="p-3 rounded bg-[#090d16] border border-[#192336] text-xs font-mono"
                        >
                          <div className="flex items-center justify-between text-[#94a3b8] mb-1">
                            <span>Reviewer: {run.review_model}</span>
                            <span className="text-emerald-400">
                              Matched: {run.matched_datasets}/{run.total_datasets} datasets
                            </span>
                          </div>
                          <div className="text-[#64748b]">
                            Status: {run.exec_status} · Rows: {run.row_count}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="pt-3 border-t border-[#1d283a] space-y-3">
                    <input
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                      placeholder="Ghi chú quyết định kiểm duyệt (lưu vào live.audit_logs)..."
                      className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white"
                    />
                    <div className="flex flex-wrap gap-2.5">
                      <button
                        onClick={handleApproveDraft}
                        disabled={selectedDraft.status !== 'needs_human'}
                        className="flex items-center gap-1.5 px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium disabled:opacity-40 transition"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Phê duyệt & Đưa vào Ngân hàng đề</span>
                      </button>
                      <button
                        onClick={handleEditDraft}
                        disabled={!['needs_human', 'rejected'].includes(selectedDraft.status)}
                        className="flex items-center gap-1.5 px-4 py-2 rounded bg-[#162238] hover:bg-[#1f304d] border border-[#293f66] text-white text-xs font-medium disabled:opacity-40 transition"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Lưu hiệu đính & Kiểm định lại</span>
                      </button>
                      <button
                        onClick={handleRequeueDraft}
                        className="flex items-center gap-1.5 px-3.5 py-2 rounded bg-amber-950/50 hover:bg-amber-900/60 border border-amber-800/60 text-amber-200 text-xs font-medium transition"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Requeue</span>
                      </button>
                      <button
                        onClick={handleRejectDraft}
                        disabled={selectedDraft.status !== 'needs_human'}
                        className="flex items-center gap-1.5 px-4 py-2 rounded bg-rose-950/50 hover:bg-rose-900/60 border border-rose-800/60 text-rose-200 text-xs font-medium disabled:opacity-40 transition"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Từ chối bản nháp</span>
                      </button>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-xs font-mono text-[#64748b]">
                Chọn một bản nháp ở danh sách bên trái để kiểm tra.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 1B: LIVE QUESTIONS BANK */}
      {subTab === 'questions' && (
        <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
          <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-white">
              Ngân hàng đề Live ({liveQuestions.length})
            </h3>
            <select
              value={qStatusFilter}
              onChange={(e) => setQStatusFilter(e.target.value)}
              className="px-2.5 py-1 rounded bg-[#0d1321] border border-[#22304a] text-xs text-[#cbd5e1] font-mono"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="ready">ready</option>
              <option value="archived">archived</option>
              <option value="retired">retired</option>
            </select>
          </div>

          <div className="divide-y divide-[#162032]">
            {liveQuestions.map((q: any) => (
              <div
                key={q.question_id}
                className="p-4 flex flex-wrap items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 font-mono text-[11px] text-[#94a3b8]">
                    <span>#{q.question_id}</span>
                    <span>· L{q.difficulty}</span>
                    <span className="px-1.5 py-0.5 rounded bg-[#131c2e] border border-[#22304a] text-[#38bdf8]">
                      {q.status}
                    </span>
                    {q.pass_rate !== undefined && (
                      <span className="text-emerald-400">
                        Pass rate: {Math.round(q.pass_rate)}%
                      </span>
                    )}
                  </div>
                  <div className="font-semibold text-white">{q.title}</div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() =>
                      toggleAdminQuestionSource(q.question_id, !q.is_source)
                        .then(() => {
                          setMsg(`Đã cập nhật trạng thái Seed mẫu cho đề #${q.question_id}.`);
                          loadLiveQuestions();
                        })
                        .catch(() => setErr('Lỗi cập nhật Seed mẫu'))
                    }
                    className={`px-2.5 py-1 rounded font-mono text-[11px] border ${
                      q.is_source
                        ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300'
                        : 'bg-[#162032] border-[#263552] text-[#94a3b8]'
                    }`}
                  >
                    Seed mẫu: {q.is_source ? 'ON' : 'OFF'}
                  </button>

                  {q.status !== 'retired' ? (
                    <button
                      onClick={() =>
                        retireAdminQuestion(q.question_id, 'Thu hồi bởi Admin')
                          .then(() => {
                            setMsg(`Đã thu hồi câu hỏi #${q.question_id}.`);
                            loadLiveQuestions();
                          })
                          .catch(() => setErr('Lỗi thu hồi câu hỏi'))
                      }
                      className="px-2.5 py-1 rounded bg-rose-950/60 border border-rose-800/60 text-rose-200 font-medium"
                    >
                      Thu hồi (Retire)
                    </button>
                  ) : (
                    <button
                      onClick={() =>
                        restoreAdminQuestion(q.question_id)
                          .then(() => {
                            setMsg(`Đã khôi phục câu hỏi #${q.question_id}.`);
                            loadLiveQuestions();
                          })
                          .catch(() => setErr('Lỗi khôi phục câu hỏi'))
                      }
                      className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
                    >
                      Khôi phục (Restore)
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: AI GENERATION JOBS */}
      {subTab === 'jobs' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          <form
            onSubmit={handleCreateJob}
            className="lg:col-span-5 bg-[#0d1321] border border-[#1d283a] rounded-lg p-5 space-y-4"
          >
            <div className="border-b border-[#1d283a] pb-3">
              <h3 className="text-sm font-semibold text-white">
                Sinh đề AI mới
              </h3>
            </div>

            <div>
              <label className="block text-xs text-[#94a3b8] mb-1">
                Chủ đề (Topic)
              </label>
              <input
                value={jobTopic}
                onChange={(e) => setJobTopic(e.target.value)}
                className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white"
              />
            </div>

            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5">
                Nhóm kỹ năng mục tiêu (Skills S1–S6)
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {SKILL_OPTIONS.map((sk) => {
                  const active = jobSkills.includes(sk.id);
                  return (
                    <button
                      type="button"
                      key={sk.id}
                      onClick={() => toggleSkill(sk.id)}
                      className={`px-2.5 py-1.5 rounded text-left text-xs font-mono border transition ${
                        active
                          ? 'bg-[#162238] border-[#38bdf8]/60 text-white'
                          : 'bg-[#080c14] border-[#1d283a] text-[#64748b]'
                      }`}
                    >
                      {sk.code} · {sk.name}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[#94a3b8] mb-1">Cấp độ khó</label>
                <select
                  value={jobDiff}
                  onChange={(e) => setJobDiff(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white"
                >
                  <option value={1}>L1 — Basic</option>
                  <option value={2}>L2 — Intermediate</option>
                  <option value={3}>L3 — Advanced</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-[#94a3b8] mb-1">
                  Số lượng câu hỏi
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={jobCount}
                  onChange={(e) => setJobCount(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 rounded bg-[#0284c7] hover:bg-[#0369a1] text-white font-medium text-xs transition"
            >
              Tạo đề AI
            </button>
          </form>

          <div className="lg:col-span-7 bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">
                Lịch sử sinh đề
              </h3>
              {llmUsage && (
                <span className="text-xs font-mono text-[#38bdf8]">
                  LLM Budget:{' '}
                  {llmUsage.used_today ?? llmUsage.calls_used ?? 0}/
                  {llmUsage.daily_cap ?? llmUsage.daily_call_cap ?? 200} calls
                </span>
              )}
            </div>
            <div className="divide-y divide-[#162032]">
              {jobs.map((j) => (
                <div
                  key={j.job_id}
                  className="p-4 flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-medium text-white">
                      #{j.job_id} · {j.topic || 'SQL Generation'}
                    </div>
                    <div className="font-mono text-[11px] text-[#64748b] mt-0.5">
                      L{j.difficulty} · {j.created_count}/{j.requested_count} câu
                    </div>
                  </div>
                  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[#131c2e] border border-[#22304a] text-[#cbd5e1] uppercase">
                    {j.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: WEEKLY SETS */}
      {subTab === 'weekly' && (
        <div className="space-y-4">
          <form
            onSubmit={handleCreateWeeklySet}
            className="bg-[#0d1321] border border-[#1d283a] rounded-lg p-4 flex flex-wrap items-end gap-3 text-xs"
          >
            <div className="flex-1 min-w-[200px]">
              <label className="block font-mono text-[#94a3b8] mb-1">
                Tiêu đề bộ đề tuần mới
              </label>
              <input
                value={newWeekTitle}
                onChange={(e) => setNewWeekTitle(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-[#080c14] border border-[#1f2b42] text-white"
              />
            </div>
            <div>
              <label className="block font-mono text-[#94a3b8] mb-1">
                Ngày bắt đầu (week_start)
              </label>
              <input
                type="date"
                value={newWeekStart}
                onChange={(e) => setNewWeekStart(e.target.value)}
                className="px-3 py-1.5 rounded bg-[#080c14] border border-[#1f2b42] text-white font-mono"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-[#0284c7] hover:bg-[#0369a1] text-white font-medium"
            >
              + Tạo bộ đề tuần mới
            </button>
          </form>

          <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
          <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a]">
            <h3 className="text-sm font-semibold text-white">
              Bộ đề tuần
            </h3>
          </div>
          <div className="divide-y divide-[#162032]">
            {weeklySets.map((w) => (
              <div
                key={w.set_id}
                className="p-4 flex flex-wrap items-center justify-between gap-3 text-xs"
              >
                <div>
                  <div className="font-semibold text-white">
                    Set #{w.set_id} · {w.title}
                  </div>
                  <div className="font-mono text-[11px] text-[#64748b] mt-0.5">
                    Week Start: {w.week_start} · Status: {w.status.toUpperCase()}
                  </div>
                </div>
                <div className="flex gap-2">
                  {w.status === 'draft' && (
                    <button
                      onClick={() => publishAdminWeeklySet(w.set_id).then(loadWeekly)}
                      className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
                    >
                      Publish Bộ đề
                    </button>
                  )}
                  {w.status === 'published' && (
                    <button
                      onClick={() => closeAdminWeeklySet(w.set_id).then(loadWeekly)}
                      className="px-3 py-1.5 rounded bg-rose-950/60 border border-rose-800/60 text-rose-200"
                    >
                      Đóng chu kỳ tuần
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
        </div>
      )}

      {/* TAB 4: USERS */}
      {subTab === 'users' && (
        <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
          <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-white">
              Danh mục Tài khoản & Phân quyền Hệ thống
            </h3>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-2.5 top-2" />
                <input
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="Tìm username hoặc email..."
                  className="pl-8 pr-3 py-1 rounded bg-[#0d1321] border border-[#22304a] text-xs text-white"
                />
              </div>
              <button
                onClick={loadUsers}
                className="px-3 py-1 rounded bg-[#162238] border border-[#293f66] text-xs text-white"
              >
                Lọc
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#0a0f1a] border-b border-[#1d283a] text-[#64748b] font-mono">
                  <th className="py-2.5 px-4">ID</th>
                  <th className="py-2.5 px-4">TÀI KHOẢN</th>
                  <th className="py-2.5 px-4">EMAIL</th>
                  <th className="py-2.5 px-4">VAI TRÒ</th>
                  <th className="py-2.5 px-4">TRẠNG THÁI</th>
                  <th className="py-2.5 px-4">THAO TÁC</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#151f30]">
                {users.map((u) => (
                  <tr key={u.user_id} className="hover:bg-[#101829]">
                    <td className="py-2.5 px-4 font-mono text-[#64748b]">
                      #{u.user_id}
                    </td>
                    <td className="py-2.5 px-4 font-medium text-white">
                      {u.display_name || u.username}{' '}
                      <span className="font-mono text-[#64748b]">(@{u.username})</span>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[#94a3b8]">{u.email}</td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`font-mono px-2 py-0.5 rounded uppercase text-[10px] border ${
                          u.role === 'admin'
                            ? 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                            : 'bg-sky-950/60 text-sky-300 border-sky-800/60'
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`font-mono px-2 py-0.5 rounded uppercase text-[10px] border ${
                          u.status === 'active'
                            ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                            : 'bg-rose-950/60 text-rose-300 border-rose-800/60'
                        }`}
                      >
                        {u.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 flex gap-2">
                      <button
                        onClick={() => handleToggleUser(u, 'role')}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#162032] hover:bg-[#1f2e47] text-[#cbd5e1] border border-[#263552]"
                      >
                        <UserCog className="w-3 h-3" />
                        <span>Đổi Role</span>
                      </button>
                      <button
                        onClick={() => handleToggleUser(u, 'status')}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#162032] hover:bg-rose-950/60 text-[#cbd5e1] hover:text-rose-200 border border-[#263552]"
                      >
                        {u.status === 'active' ? (
                          <>
                            <Lock className="w-3 h-3" />
                            <span>Khóa</span>
                          </>
                        ) : (
                          <>
                            <Unlock className="w-3 h-3" />
                            <span>Mở khóa</span>
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: SYSTEM SETTINGS */}
      {subTab === 'settings' && (
        <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
          <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a]">
            <h3 className="text-sm font-semibold text-white">
              Cấu hình Hệ thống (live.system_settings)
            </h3>
          </div>
          <div className="divide-y divide-[#162032]">
            {settingsList.map((st: any) => (
              <div
                key={st.key}
                className="p-4 flex flex-wrap items-center justify-between gap-3 text-xs font-mono"
              >
                <div>
                  <div className="text-white font-semibold">{st.key}</div>
                  {st.description && (
                    <div className="text-[11px] text-[#64748b] mt-0.5">
                      {st.description}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    value={settingEdits[st.key] ?? ''}
                    onChange={(e) =>
                      setSettingEdits((prev) => ({
                        ...prev,
                        [st.key]: e.target.value,
                      }))
                    }
                    className="px-3 py-1.5 rounded bg-[#080c14] border border-[#1f2b42] text-white w-64"
                  />
                  <button
                    onClick={() => handleUpdateSetting(st.key)}
                    className="px-3 py-1.5 rounded bg-[#162238] hover:bg-[#1f304d] border border-[#293f66] text-[#38bdf8]"
                  >
                    Lưu
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
