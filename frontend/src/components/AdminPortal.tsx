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
  runAdminWorker,
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
  getAdminSkills,
  updateAdminSetting,
} from '../lib/api';

const TOPIC_PRESETS = [
  'Phân tích hiệu suất nhân sự & lương thưởng theo phòng ban (HR)',
  'Rà soát tồn kho, sức chứa kho vận & điều chuyển hàng hóa (Inventory)',
  'Phân tích hành vi mua sắm & phân khúc khách hàng hoạt động (CRM)',
  'Đối soát đơn hàng giao trễ, hoàn tiền & cổng thanh toán (Orders & Payments)',
  'Đánh giá biên lợi nhuận sản phẩm & nhà cung cấp chủ lực (Catalog)',
  'Kiểm soát chi phí vận hành & ngân sách phê duyệt theo quý (Finance)',
];

const formatVnDateTime = (iso?: string | null) => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())} · ${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
};

const formatVnTime = (iso?: string | null) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

const SKILL_OPTIONS = [
  { id: 19, code: 'S1', name: 'SELECT / WHERE' },
  { id: 20, code: 'S2', name: 'JOIN Multi-Table' },
  { id: 21, code: 'S3', name: 'GROUP BY / HAVING' },
  { id: 22, code: 'S4', name: 'Subquery / CTE' },
  { id: 23, code: 'S5', name: 'Window Functions' },
  { id: 24, code: 'S6', name: 'Edge Cases & NULL' },
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
  const [qSourceFilter, setQSourceFilter] = useState<'ALL' | 'ai_generated' | 'seed'>('ALL');
  const [liveQuestions, setLiveQuestions] = useState<any[]>([]);

  // Jobs
  const [jobs, setJobs] = useState<any[]>([]);
  const [llmUsage, setLlmUsage] = useState<any>(null);
  const [jobDiff, setJobDiff] = useState(2);
  const [jobCount, setJobCount] = useState(1);
  const [jobTopic, setJobTopic] = useState('');
  const [skillOptions, setSkillOptions] = useState(SKILL_OPTIONS);
  const [jobSkills, setJobSkills] = useState<number[]>([2, 3]);
  const [submittingJob, setSubmittingJob] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);

  // Weekly, Users & Settings
  const [weeklySets, setWeeklySets] = useState<any[]>([]);
  const [newWeekTitle, setNewWeekTitle] = useState('Bộ đề tuần SQL nâng cao');
  const [newWeekStart, setNewWeekStart] = useState('2026-11-02');
  const [users, setUsers] = useState<any[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [settingsList, setSettingsList] = useState<any[]>([]);
  const [settingEdits, setSettingEdits] = useState<Record<string, string>>({});

  const loadSkills = async () => {
    try {
      const r = await getAdminSkills();
      const items = (r?.items || []).filter((s: any) => s.is_active !== false);
      if (items.length > 0) {
        const mapped = items.map((s: any) => ({
          id: s.skill_id ?? s.id,
          code: s.code,
          name: s.name,
        }));
        setSkillOptions(mapped);
        const validIds = new Set(mapped.map((m: any) => m.id));
        setJobSkills((prev) => {
          const filtered = prev.filter((id) => validIds.has(id));
          return filtered.length > 0
            ? filtered
            : mapped.slice(0, 2).map((m: any) => m.id);
        });
      }
    } catch {}
  };

  const loadDrafts = async () => {
    try {
      const r = await getAdminDrafts({});
      setDrafts(r.items || []);
      if (r.items?.length > 0 && !selectedDraft) {
        inspectDraft(r.items[0].draft_id);
      }
    } catch (e: any) {
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Cần quyền Quản trị viên (Admin)');
    }
  };

  const inspectDraft = async (draftId: number) => {
    try {
      const d = await getAdminDraftDetail(draftId);
      setSelectedDraft(d);
      setEditTitle(d.title || '');
      setEditQuestion(d.question || '');
    } catch (e: any) {
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Không tải được chi tiết bản nháp');
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
    loadSkills();
    loadDrafts();
    loadLiveQuestions();
    if (subTab === 'jobs') {
      loadJobs();
    }
    if (subTab === 'weekly') loadWeekly();
    if (subTab === 'users') loadUsers();
    if (subTab === 'settings') loadSettings();
  }, [subTab, qStatusFilter, isAdmin]);

  const activeRunningJob = jobs.find(
    (j: any) => j.status === 'queued' || j.status === 'running'
  );
  const isGenerating = Boolean(submittingJob || activeRunningJob);

  useEffect(() => {
    if (!isAdmin) return;
    if (!activeRunningJob) {
      setElapsedSec(0);
      return;
    }
    const updateElapsed = () => {
      const startMs = new Date(
        activeRunningJob.started_at || activeRunningJob.created_at || Date.now()
      ).getTime();
      setElapsedSec(Math.max(0, Math.floor((Date.now() - startMs) / 1000)));
    };
    updateElapsed();
    const tick = setInterval(updateElapsed, 1000);
    const poll = setInterval(() => {
      loadJobs();
      loadDrafts();
    }, 2000);
    return () => {
      clearInterval(tick);
      clearInterval(poll);
    };
  }, [activeRunningJob?.job_id, activeRunningJob?.status, isAdmin]);

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
          <strong className="text-amber-300">Admin (admin)</strong> trên thanh trạng thái phía trên.
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
    if (isGenerating) return;
    setMsg(null);
    setErr(null);
    setSubmittingJob(true);
    const chosenTopic =
      jobTopic.trim() ||
      TOPIC_PRESETS[Math.floor(Math.random() * TOPIC_PRESETS.length)];
    try {
      const job = await createGenerationJob({
        difficulty: jobDiff,
        skill_ids: jobSkills.length ? jobSkills : [skillOptions[0]?.id ?? 2],
        requested_count: jobCount,
        quantity: jobCount,
        topic: chosenTopic,
        auto_run: true,
      });
      setMsg(
        job.status === 'done'
          ? `Đã chạy xong Job Sinh đề #${job.job_id} (${job.created_count}/${job.requested_count} câu nháp mới đã vào mục "Duyệt đề").`
          : `Đang thực thi Job Sinh đề #${job.job_id} (${job.requested_count} câu · "${chosenTopic}"). Hệ thống đang chạy Model A (llama3) & Model B (qwen2.5-coder:7b)...`
      );
      await Promise.all([loadJobs(), loadDrafts()]);
    } catch (e: any) {
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Lỗi tạo job sinh đề');
    } finally {
      setSubmittingJob(false);
    }
  };

  const handleRunWorker = async () => {
    setMsg(null);
    setErr(null);
    try {
      const res = await runAdminWorker();
      setMsg(
        `Đã kích hoạt xử lý hàng đợi thành công (Đã chạy ${res?.processed_jobs ?? 0} job).`
      );
      loadJobs();
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Lỗi khi chạy hàng đợi sinh đề');
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
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Lỗi phê duyệt');
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
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Lỗi từ chối draft');
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
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Lỗi lưu bản nháp');
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
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Lỗi requeue draft');
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
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Không tạo được bộ đề tuần');
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
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Lỗi cập nhật cấu hình');
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
      setErr(e?.response?.data?.message || e?.response?.data?.error?.message || 'Không thể cập nhật tài khoản');
    }
  };

  const filteredDrafts = draftStatus
    ? drafts.filter((d) => d.status === draftStatus)
    : drafts;

  return (
    <div className="space-y-4">
      {/* Permanent 3-Step Workflow Guide Strip */}
      <div className="p-3.5 rounded-lg bg-[#0d1321] border border-[#1d283a] grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div className="p-2.5 rounded bg-[#090d16] border border-[#192336]">
          <div className="font-semibold text-[#38bdf8] mb-1">
            Bước 1 (Sinh đề AI)
          </div>
          <p className="text-[#cbd5e1] leading-relaxed">
            Chọn Chủ đề + Kỹ năng + Độ khó -&gt; Model A (<strong>llama3</strong>) tự đọc 13 bảng DB để <strong>tự đặt Tiêu đề bài tập</strong> &amp; viết câu hỏi + đáp án SQL.
          </p>
        </div>
        <div className="p-2.5 rounded bg-[#090d16] border border-[#192336]">
          <div className="font-semibold text-amber-300 mb-1">
            Bước 2 (Kiểm tra &amp; Duyệt đề mới sinh)
          </div>
          <p className="text-[#cbd5e1] leading-relaxed">
            Model B (<strong>qwen2.5-coder:7b</strong>) tự giải kiểm chứng. Đề đạt chuẩn sẽ <strong>Tự động duyệt (approved)</strong>; đề cần cân nhắc sẽ vào <strong>Cần duyệt tay (needs_human)</strong>. Admin bấm vào từng bản nháp để sửa <strong>Tiêu đề bài tập / Nội dung</strong> hoặc bấm <strong>Duyệt lên kệ</strong>.
          </p>
        </div>
        <div className="p-2.5 rounded bg-[#090d16] border border-[#192336]">
          <div className="font-semibold text-emerald-300 mb-1">
            Bước 3 (Làm bài &amp; Ngân hàng đề)
          </div>
          <p className="text-[#cbd5e1] leading-relaxed">
            Ngay khi đề được duyệt, hệ thống tự động gắn mã bài mới (<strong>SQL21, SQL22... SQL26</strong>) và đưa thẳng sang tab <strong>Làm bài -&gt; mục &quot;Đề AI mới sinh&quot;</strong> để sinh viên làm ngay!
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        {/* Sub-navigation Bar */}
        <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg p-1 flex flex-wrap items-center gap-1">
          {[
            { id: 'jobs', label: 'Bước 1: Sinh đề AI' },
            {
              id: 'drafts',
              label: `Bước 2: Kiểm tra & Duyệt đề mới sinh (${drafts.length})`,
            },
            {
              id: 'questions',
              label: `Bước 3: Ngân hàng đề đã lên kệ (${liveQuestions.length})`,
            },
            { id: 'weekly', label: 'Bộ đề tuần' },
            { id: 'users', label: 'Người dùng' },
            { id: 'settings', label: 'Cấu hình' },
          ].map((t) => {
            const active = subTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setSubTab(t.id as any)}
                className={`px-3.5 py-1.5 rounded text-xs font-medium transition ${
                  active
                    ? 'bg-[#162238] text-white border border-[#293f66]'
                    : 'text-[#64748b] hover:text-white border border-transparent'
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {err && (
        <div className="p-3 rounded bg-red-950/40 border border-red-900/60 text-red-300 text-xs">
          {err}
        </div>
      )}
      {msg && (
        <div className="p-3 rounded bg-emerald-950/40 border border-emerald-900/60 text-emerald-300 text-xs">
          {msg}
        </div>
      )}

      {/* TAB 1: DRAFT REVIEW */}
      {subTab === 'drafts' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left Queue */}
          <div className="lg:col-span-4 bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
            <div className="p-3.5 bg-[#090d16] border-b border-[#1d283a] space-y-2.5">
              <div className="text-xs font-semibold text-white">
                Phân loại trạng thái bản nháp ({drafts.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { val: '', label: `Tất cả (${drafts.length})` },
                  {
                    val: 'needs_human',
                    label: `Cần duyệt tay (${drafts.filter((d) => d.status === 'needs_human').length})`,
                  },
                  {
                    val: 'approved',
                    label: `AI tự duyệt — Đã lên kệ (${drafts.filter((d) => d.status === 'approved').length})`,
                  },
                  {
                    val: 'pending',
                    label: `Đang chấm (${drafts.filter((d) => d.status === 'pending').length})`,
                  },
                  {
                    val: 'rejected',
                    label: `Đã từ chối (${drafts.filter((d) => d.status === 'rejected').length})`,
                  },
                ].map((pill) => {
                  const active = draftStatus === pill.val;
                  return (
                    <button
                      key={pill.val || 'all'}
                      onClick={() => setDraftStatus(pill.val)}
                      className={`px-2.5 py-1 rounded text-[11px] font-medium border transition ${
                        active
                          ? 'bg-[#162238] border-[#38bdf8] text-white'
                          : 'bg-[#0d1321] border-[#22304a] text-[#94a3b8] hover:text-white'
                      }`}
                    >
                      {pill.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="divide-y divide-[#162032] max-h-[640px] overflow-y-auto">
              {filteredDrafts.map((d) => {
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
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="text-[#64748b]">
                        DRAFT #{d.draft_id} · L{d.difficulty}
                        {d.weekly_position
                          ? ` · Mã bài: SQL${String(d.weekly_position).padStart(2, '0')}`
                          : ''}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded border ${statusBadge}`}>
                        {d.status}
                      </span>
                    </div>
                    <div className="text-xs font-medium text-white line-clamp-2">
                      {d.title}
                    </div>
                    {(d.job_topic || d.business_domain) && (
                      <div className="text-[11px] text-[#38bdf8] mt-1 truncate">
                        Chủ đề: {d.job_topic || d.business_domain}
                      </div>
                    )}
                    {Array.isArray(d.tables_used) && d.tables_used.length > 0 && (
                      <div className="text-[10px] text-[#94a3b8] mt-0.5 truncate">
                        Bảng: {d.tables_used.join(', ')}
                      </div>
                    )}
                    {d.status_reason && (
                      <div className="text-[11px] text-[#64748b] mt-1 line-clamp-2">
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
                    <div className="text-[11px] text-[#64748b]">
                      DRAFT REVIEW INSPECTOR · ID #{selectedDraft.draft_id}
                      {selectedDraft.job_id ? ` · TỪ JOB #${selectedDraft.job_id}` : ''}
                    </div>
                    <div className="text-sm font-semibold text-white mt-0.5">
                      Generator: {selectedDraft.gen_model} ({selectedDraft.gen_prompt_version})
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {selectedDraft.promoted_question?.weekly_position && (
                      <span className=" text-xs px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 font-semibold">
                        Đang ở tab Làm bài: Mã bài SQL
                        {String(selectedDraft.promoted_question.weekly_position).padStart(2, '0')}{' '}
                        (Live ID #{selectedDraft.promoted_question.question_id})
                      </span>
                    )}
                    <span className=" text-xs px-2.5 py-1 rounded bg-[#131c2e] border border-[#22304a] text-[#38bdf8]">
                      STATUS: {selectedDraft.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="p-5 space-y-4">
                  {/* Metadata Box: Topic, Skills, Tables, Live Question Position */}
                  <div className="p-3.5 rounded-lg bg-[#090d16] border border-[#192336] grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs">
                    <div>
                      <span className="text-[#64748b]">Chủ đề (Topic): </span>
                      <span className="text-white font-medium">
                        {selectedDraft.job_topic ||
                          selectedDraft.blueprint?.business_domain ||
                          'SQL Doanh nghiệp (Enterprise DB)'}
                      </span>
                    </div>
                    <div>
                      <span className="text-[#64748b]">Vị trí đề ngoài trang chủ: </span>
                      {selectedDraft.promoted_question?.weekly_position ? (
                        <span className="text-emerald-400 font-semibold">
                          Mã bài SQL
                          {String(selectedDraft.promoted_question.weekly_position).padStart(2, '0')}{' '}
                          (Live #{selectedDraft.promoted_question.question_id} · Bộ đề tuần hiện tại)
                        </span>
                      ) : selectedDraft.promoted_question?.question_id ? (
                        <span className="text-emerald-400">
                          Ngân hàng đề Live #{selectedDraft.promoted_question.question_id}
                        </span>
                      ) : (
                        <span className="text-amber-300">
                          Chưa lên trang chủ (Bấm &quot;Phê duyệt&quot; bên dưới để gắn mã SQL mới)
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="text-[#64748b]">Nhóm kỹ năng: </span>
                      <span className="text-[#38bdf8]">
                        {selectedDraft.skills?.length
                          ? selectedDraft.skills.map((s: any) => `${s.code} (${s.name})`).join(', ')
                          : `L${selectedDraft.difficulty}`}
                      </span>
                    </div>
                    <div>
                      <span className="text-[#64748b]">Bảng dữ liệu sử dụng: </span>
                      <span className="text-white">
                        {selectedDraft.tables_used?.length
                          ? selectedDraft.tables_used.join(', ')
                          : 'enterprise_db'}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {selectedDraft.status === 'approved' &&
                      (selectedDraft.weekly_position ||
                        selectedDraft.promoted_question?.weekly_position) && (
                        <div className="p-3 rounded-lg bg-emerald-950/50 border border-emerald-700/60 text-xs text-emerald-200 font-semibold leading-relaxed">
                          Đề này đã có mặt ở tab Làm bài với mã SQL
                          {String(
                            selectedDraft.weekly_position ||
                              selectedDraft.promoted_question?.weekly_position
                          ).padStart(2, '0')}
                          ! Bạn có thể bấm sang tab &quot;Làm bài&quot; -&gt; lọc &quot;Đề AI mới sinh&quot; để làm thử ngay.
                        </div>
                      )}
                    <div className="p-3 rounded-lg bg-[#090d16] border border-[#1d283a] space-y-1 text-xs">
                      <div className="font-semibold text-[#38bdf8]">
                        Chủ đề gốc yêu cầu (Job Topic):{' '}
                        {selectedDraft.job_topic || 'Tự động theo bảng'}
                      </div>
                      <div className="text-[#94a3b8]">
                        Dựa theo Chủ đề gốc lúc bấm tạo và 13 bảng DB, Model A (llama3) đã tự động sáng tạo tình huống và đặt Tiêu đề bài tập bên dưới.
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-white mb-1">
                        Tiêu đề bài tập (Do Model A llama3 tự đặt dựa theo Chủ đề Job #{selectedDraft.job_id || 1} — Admin có thể sửa lại tùy ý)
                      </label>
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[#94a3b8] mb-1">
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
                    <div className="flex items-center justify-between text-xs text-[#94a3b8] mb-1.5">
                      <span>Lời giải SQL tham chiếu & Kết quả đối sánh Model B</span>
                      <span>
                        Self-solve runs: {selectedDraft.self_solve_runs?.length || 0}
                      </span>
                    </div>
                    <pre className="p-3.5 rounded bg-[#080c14] border border-[#182235] text-xs text-[#cbd5e1] overflow-x-auto leading-relaxed">
                      {selectedDraft.reference_sql ||
                        selectedDraft.self_solve_runs?.[0]?.model_sql ||
                        '-- Chưa có SQL'}
                    </pre>
                  </div>

                  {selectedDraft.self_solve_runs?.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-white">
                        Kết quả AI Reviewer (Model B) giải độc lập ({selectedDraft.self_solve_runs.length} lượt):
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {selectedDraft.self_solve_runs.map((run: any) => (
                          <div
                            key={run.run_id}
                            className="p-3 rounded bg-[#090d16] border border-[#192336] text-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between text-[#94a3b8]">
                              <span className="font-semibold text-white">
                                Model B: {run.review_model}
                              </span>
                              <span className="text-emerald-400 font-semibold">
                                Khớp {run.matched_datasets}/{run.total_datasets} datasets
                              </span>
                            </div>
                            <div className="text-[#64748b]">
                              Trạng thái: {run.exec_status} · Số dòng: {run.row_count}
                            </div>
                            {run.model_sql && (
                              <pre className="p-2 rounded bg-[#080c14] border border-[#182235] text-[11px] overflow-x-auto text-[#cbd5e1]">
                                {run.model_sql}
                              </pre>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedDraft.review_logs?.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-white">
                        Nhật ký Kiểm định 7 Cổng (Automated & Semantic Review Gates):
                      </div>
                      <div className="space-y-1.5 max-h-48 overflow-y-auto">
                        {selectedDraft.review_logs.map((lg: any, idx: number) => (
                          <div
                            key={lg.log_id || idx}
                            className="p-2.5 rounded bg-[#090d16] border border-[#192336] text-xs flex flex-wrap items-center justify-between gap-2"
                          >
                            <div>
                              <span className="font-semibold text-[#38bdf8] mr-2">
                                [{lg.stage || lg.gate_name || 'GATE'}]
                              </span>
                              <span className="text-white">
                                {lg.message || lg.reason || lg.verdict}
                              </span>
                            </div>
                            <span className="text-[11px] text-[#64748b]">
                              {lg.passed !== false ? 'PASS' : 'WARN'}
                            </span>
                          </div>
                        ))}
                      </div>
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
                        className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium disabled:opacity-40 transition"
                      >
                        Phê duyệt & Đưa vào Ngân hàng đề
                      </button>
                      <button
                        onClick={handleEditDraft}
                        disabled={!['needs_human', 'rejected'].includes(selectedDraft.status)}
                        className="px-4 py-2 rounded bg-[#162238] hover:bg-[#1f304d] border border-[#293f66] text-white text-xs font-medium disabled:opacity-40 transition"
                      >
                        Lưu hiệu đính & Kiểm định lại
                      </button>
                      <button
                        onClick={handleRequeueDraft}
                        className="px-3.5 py-2 rounded bg-amber-950/50 hover:bg-amber-900/60 border border-amber-800/60 text-amber-200 text-xs font-medium transition"
                      >
                        Kiểm định lại (Requeue)
                      </button>
                      <button
                        onClick={handleRejectDraft}
                        disabled={selectedDraft.status !== 'needs_human'}
                        className="px-4 py-2 rounded bg-rose-950/50 hover:bg-rose-900/60 border border-rose-800/60 text-rose-200 text-xs font-medium disabled:opacity-40 transition"
                      >
                        Từ chối bản nháp
                      </button>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-xs text-[#64748b]">
                Chọn một bản nháp ở danh sách bên trái để kiểm tra.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 1B: LIVE QUESTIONS BANK */}
      {subTab === 'questions' && (() => {
        const isLiveAi = (q: any) =>
          q.source_type === 'ai_generated' ||
          Boolean(q.source_draft_id) ||
          Number(q.weekly_position || q.position || q.question_id) > 20;
        const aiLiveCount = liveQuestions.filter(isLiveAi).length;
        const seedLiveCount = liveQuestions.length - aiLiveCount;
        const shownLive = liveQuestions.filter((q: any) => {
          if (qSourceFilter === 'ai_generated') return isLiveAi(q);
          if (qSourceFilter === 'seed') return !isLiveAi(q);
          return true;
        });

        return (
          <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
            <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold text-white mr-2">
                  Bước 3: Ngân hàng đề đã lên kệ ({liveQuestions.length})
                </h3>
                {[
                  { id: 'ALL', label: `Tất cả (${liveQuestions.length})` },
                  { id: 'ai_generated', label: `Đề AI mới sinh (${aiLiveCount})` },
                  { id: 'seed', label: `Đề gốc chuẩn (${seedLiveCount})` },
                ].map((btn) => (
                  <button
                    key={btn.id}
                    onClick={() => setQSourceFilter(btn.id as any)}
                    className={`px-2.5 py-1 rounded text-xs font-medium border transition ${
                      qSourceFilter === btn.id
                        ? 'bg-[#162238] border-[#38bdf8] text-white'
                        : 'bg-[#0d1321] border-[#22304a] text-[#94a3b8] hover:text-white'
                    }`}
                  >
                    {btn.label}
                  </button>
                ))}
              </div>
              <select
                value={qStatusFilter}
                onChange={(e) => setQStatusFilter(e.target.value)}
                className="px-2.5 py-1 rounded bg-[#0d1321] border border-[#22304a] text-xs text-[#cbd5e1]"
              >
                <option value="">Tất cả trạng thái</option>
                <option value="ready">ready</option>
                <option value="archived">archived</option>
                <option value="retired">retired</option>
              </select>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#090d16] border-b border-[#1d283a] text-[#94a3b8] font-semibold">
                    <th className="py-3 px-4 w-28">Mã bài tuần</th>
                    <th className="py-3 px-4 w-40">Phân loại nguồn</th>
                    <th className="py-3 px-4 w-48">Chủ đề / Nghiệp vụ</th>
                    <th className="py-3 px-4">Tiêu đề bài tập</th>
                    <th className="py-3 px-4 w-44">Kỹ năng &amp; Độ khó</th>
                    <th className="py-3 px-4 w-44">Các bảng DB</th>
                    <th className="py-3 px-4 w-44">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#162032]">
                  {shownLive.map((q: any) => {
                    const ai = isLiveAi(q);
                    const code = `SQL${String(
                      q.weekly_position || q.position || q.question_id
                    ).padStart(2, '0')}`;
                    const skillsText =
                      Array.isArray(q.skills) && q.skills.length > 0
                        ? q.skills
                            .map((s: any) =>
                              typeof s === 'string' ? s : `${s.code || ''} ${s.name || ''}`.trim()
                            )
                            .join(', ')
                        : q.skill_code || `L${q.difficulty}`;
                    const tablesText =
                      Array.isArray(q.tables_used) && q.tables_used.length > 0
                        ? q.tables_used.join(', ')
                        : 'enterprise_db';
                    return (
                      <tr key={q.question_id} className="hover:bg-[#101829]">
                        <td className="py-3 px-4 font-bold text-[#38bdf8]">
                          {code}
                          <div className="text-[10px] text-[#64748b] font-normal">
                            Live #{q.question_id} · {q.status}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {ai ? (
                            <span className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-[11px] font-semibold">
                              Đề AI · Draft #{q.source_draft_id || q.question_id}
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded bg-[#131c2e] border border-[#22304a] text-[#94a3b8] text-[11px]">
                              Đề gốc chuẩn
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-[#cbd5e1]">
                          {q.domain_category || q.job_topic || q.topic || 'Nghiệp vụ Doanh nghiệp'}
                        </td>
                        <td className="py-3 px-4 font-semibold text-white">
                          {q.title}
                        </td>
                        <td className="py-3 px-4 text-[#94a3b8]">
                          <div>L{q.difficulty} · {skillsText}</div>
                          {q.pass_rate !== undefined && (
                            <div className="text-[11px] text-emerald-400">
                              Pass rate: {Math.round(q.pass_rate)}%
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4 text-[#94a3b8]">{tablesText}</td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <button
                              onClick={() =>
                                toggleAdminQuestionSource(q.question_id, !q.is_source)
                                  .then(() => {
                                    setMsg(`Đã cập nhật trạng thái Seed mẫu cho đề #${q.question_id}.`);
                                    loadLiveQuestions();
                                  })
                                  .catch(() => setErr('Lỗi cập nhật Seed mẫu'))
                              }
                              className={`px-2 py-1 rounded text-[11px] border ${
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
                                className="px-2 py-1 rounded bg-rose-950/60 border border-rose-800/60 text-rose-200 font-medium text-[11px]"
                              >
                                Thu hồi
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
                                className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-[11px]"
                              >
                                Khôi phục
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })()}

      {/* TAB 2: AI GENERATION JOBS */}
      {subTab === 'jobs' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          <form
            onSubmit={handleCreateJob}
            className="lg:col-span-5 bg-[#0d1321] border border-[#1d283a] rounded-lg p-5 space-y-4"
          >
            <div className="border-b border-[#1d283a] pb-3 space-y-1">
              <h3 className="text-sm font-semibold text-white">
                Khởi chạy Pipeline Sinh đề & Kiểm định AI 2-Model
              </h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">
                Model A (Generator) sinh đề &amp; câu lệnh SQL mẫu → Model B (Reviewer) giải độc lập 3 lần &amp; kiểm định qua 7 cổng trên PostgreSQL 17.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-white mb-1">
                Chủ đề nghiệp vụ (Topic)
              </label>
              <p className="text-[11px] text-[#94a3b8] mb-2 leading-relaxed">
                Bạn chỉ cần chọn Chủ đề định hướng (Topic). Dựa vào chủ đề này và 13 bảng dữ liệu thực tế, Model A (llama3) sẽ tự động sáng tạo tình huống và tự đặt <strong>Tiêu đề bài tập</strong> cụ thể.
              </p>
              <input
                value={jobTopic}
                onChange={(e) => setJobTopic(e.target.value)}
                placeholder="Nhập chủ đề tùy chỉnh hoặc chọn nhanh bên dưới (bỏ trống sẽ chọn ngẫu nhiên)..."
                className="w-full px-3 py-2 rounded bg-[#080c14] border border-[#1f2b42] text-xs text-white placeholder:text-[#475569]"
              />
              <div className="mt-2">
                <div className="text-[11px] text-[#64748b] mb-1.5">
                  Chủ đề gợi ý theo Enterprise DB (bấm để chọn nhanh):
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {TOPIC_PRESETS.map((preset) => {
                    const selected = jobTopic === preset;
                    return (
                      <button
                        type="button"
                        key={preset}
                        onClick={() => setJobTopic(preset)}
                        className={`px-2 py-1 rounded text-[11px] text-left border transition ${
                          selected
                            ? 'bg-[#162238] border-[#38bdf8] text-[#38bdf8]'
                            : 'bg-[#080c14] border-[#1d283a] text-[#94a3b8] hover:border-[#334155] hover:text-white'
                        }`}
                      >
                        {preset}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5">
                Nhóm kỹ năng mục tiêu (Skills S1–S6)
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                {skillOptions.map((sk) => {
                  const active = jobSkills.includes(sk.id);
                  return (
                    <button
                      type="button"
                      key={sk.id}
                      onClick={() => toggleSkill(sk.id)}
                      className={`px-2.5 py-1.5 rounded text-left text-xs border transition ${
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
              disabled={isGenerating}
              className={`w-full py-2.5 rounded font-medium text-xs transition ${
                isGenerating
                  ? 'bg-[#1e293b] border border-[#38bdf8]/50 text-[#38bdf8] cursor-wait animate-pulse'
                  : 'bg-[#0284c7] hover:bg-[#0369a1] text-white'
              }`}
            >
              {isGenerating
                ? activeRunningJob
                  ? `Đang sinh & kiểm định đề AI... (Job #${activeRunningJob.job_id} · ${activeRunningJob.created_count}/${activeRunningJob.requested_count} câu · ${elapsedSec}s)`
                  : 'Đang gửi yêu cầu khởi tạo Pipeline AI...'
                : 'Tạo đề AI'}
            </button>

            {isGenerating && (
              <div className="p-3.5 rounded-lg bg-[#090d16] border border-[#38bdf8]/50 space-y-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-[#38bdf8]">
                    Pipeline AI 2-Model đang hoạt động trực tiếp...
                  </span>
                  <span className=" text-[11px] px-2 py-0.5 rounded bg-[#162238] text-white">
                    Đã chạy: {elapsedSec}s
                  </span>
                </div>
                {activeRunningJob && (
                  <div className=" text-[11px] text-[#cbd5e1]">
                    Job #{activeRunningJob.job_id} · Chủ đề: {activeRunningJob.topic} · Tiến độ:{' '}
                    <strong className="text-emerald-400">
                      {activeRunningJob.created_count}/{activeRunningJob.requested_count} câu
                    </strong>
                  </div>
                )}
                <div className="w-full h-1.5 rounded-full bg-[#162032] overflow-hidden">
                  <div
                    className="h-full bg-[#38bdf8] transition-all duration-500 animate-pulse"
                    style={{
                      width: activeRunningJob
                        ? `${Math.max(
                            18,
                            Math.round(
                              ((activeRunningJob.created_count + 0.35) /
                                Math.max(1, activeRunningJob.requested_count)) *
                                100
                            )
                          )}%`
                        : '25%',
                    }}
                  />
                </div>
                <div className="text-[11px] text-[#94a3b8] leading-relaxed">
                  Bước 1: <strong>Model A (llama3)</strong> sinh câu hỏi tiếng Việt → Bước 2:{' '}
                  <strong>Model B (qwen2.5-coder:7b)</strong> tự giải SQL &amp; chạy thử trên PostgreSQL 17 → Bước 3: Kiểm định 7 cổng tự động.
                </div>
              </div>
            )}
          </form>

          <div className="lg:col-span-7 space-y-4">
            <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
              <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-white">
                  Lịch sử sinh đề
                </h3>
                <div className="flex items-center gap-2.5">
                  {llmUsage && (
                    <span className="text-xs text-[#38bdf8]">
                      LLM Budget:{' '}
                      {llmUsage.used_today ?? llmUsage.calls_used ?? 0}/
                      {llmUsage.daily_cap ?? llmUsage.daily_call_cap ?? 200} calls
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={handleRunWorker}
                    className="inline-flex items-center px-2.5 py-1 rounded bg-[#131c2e] hover:bg-[#1e293b] border border-[#22304a] text-[11px] font-medium text-[#38bdf8] transition"
                  >
                    Chạy hàng đợi ngay
                  </button>
                </div>
              </div>
              <div className="divide-y divide-[#162032] max-h-[380px] overflow-y-auto">
                {jobs.map((j) => {
                  const startedAt = formatVnDateTime(j.started_at || j.created_at);
                  const finishedAt = formatVnDateTime(j.finished_at || j.completed_at);
                  const createdAt = formatVnDateTime(j.created_at);
                  const jobDrafts =
                    Array.isArray(j.drafts) && j.drafts.length > 0
                      ? j.drafts
                      : drafts.filter((d: any) => d.job_id === j.job_id);
                  return (
                    <div
                      key={j.job_id}
                      className="p-4 flex flex-col gap-2.5 text-xs"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="font-medium text-white">
                            #{j.job_id} · {j.topic || 'SQL Generation'}
                          </div>
                          <div className=" text-[11px] text-[#64748b]">
                            L{j.difficulty} · {j.created_count}/{j.requested_count} câu
                          </div>
                          <div className=" text-[11px] text-[#94a3b8] flex flex-wrap gap-x-3 gap-y-0.5">
                            {startedAt ? (
                              <span>Bắt đầu: {startedAt}</span>
                            ) : (
                              createdAt && <span>Tạo lúc: {createdAt}</span>
                            )}
                            {finishedAt && <span>Hoàn thành: {finishedAt}</span>}
                          </div>
                          {j.status === 'failed' && j.error_message && (
                            <div className="text-[11px] text-rose-400 bg-rose-950/30 border border-rose-900/50 rounded px-2 py-1 mt-1">
                              Lỗi: {j.error_message}
                            </div>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-2 shrink-0">
                          <span className="text-[11px] px-2 py-0.5 rounded bg-[#131c2e] border border-[#22304a] text-[#cbd5e1] uppercase">
                            {j.status}
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setSubTab('drafts');
                              if (jobDrafts[0]?.draft_id) {
                                inspectDraft(jobDrafts[0].draft_id);
                              }
                            }}
                            className="px-2.5 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-700/60 text-[11px] font-semibold text-emerald-300 transition"
                          >
                            Xem bản nháp vừa sinh ở Bước 2
                          </button>
                        </div>
                      </div>

                      {jobDrafts.length > 0 && (
                        <div className="pt-2 border-t border-[#162032] space-y-1.5">
                          <div className="text-[11px] text-[#94a3b8]">
                            Đề vừa sinh từ Job #{j.job_id} ({jobDrafts.length} câu):
                          </div>
                          <div className="flex flex-col gap-1.5">
                            {jobDrafts.map((d: any) => (
                              <div
                                key={d.draft_id}
                                className="flex flex-wrap items-center justify-between gap-2 px-2.5 py-1.5 rounded bg-[#090d16] border border-[#1d283a]"
                              >
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className=" text-[11px] text-[#38bdf8] font-semibold shrink-0">
                                    #{d.draft_id}
                                  </span>
                                  <span className="text-xs text-white truncate">
                                    {d.title || 'Câu hỏi SQL mới'}
                                  </span>
                                  <span
                                    className={` text-[10px] px-1.5 py-0.5 rounded border uppercase shrink-0 ${
                                      d.status === 'approved'
                                        ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                                        : 'bg-amber-950/40 border-amber-800/60 text-amber-300'
                                    }`}
                                  >
                                    {d.status || 'needs_human'}
                                  </span>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSubTab('drafts');
                                    inspectDraft(d.draft_id);
                                  }}
                                  className="px-2.5 py-1 rounded bg-[#38bdf8]/15 hover:bg-[#38bdf8]/25 border border-[#38bdf8]/40 text-[11px] font-semibold text-[#38bdf8] transition shrink-0"
                                >
                                  Xem &amp; Duyệt câu #{d.draft_id}: {d.title}
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
              <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-white">
                  Nhật ký gọi AI thời gian thực (Live LLM Call Log — Model A &amp; Model B)
                </h3>
                <span className="text-[11px] px-2.5 py-1 rounded bg-[#131c2e] border border-[#38bdf8]/40 text-[#38bdf8]">
                  Pipeline AI: Model A (llama3) · Model B (qwen2.5-coder:7b)
                </span>
              </div>
              <div className="divide-y divide-[#162032] max-h-[340px] overflow-y-auto">
                {(!llmUsage?.recent_calls || llmUsage.recent_calls.length === 0) ? (
                  <div className="p-4 text-xs text-[#64748b]">
                    Chưa ghi nhận cuộc gọi LLM nào trong phiên hiện tại.
                  </div>
                ) : (
                  llmUsage.recent_calls.map((c: any, idx: number) => {
                    const rawStage = String(c.stage || c.purpose || c.role || '').toLowerCase();
                    const isModelB =
                      rawStage.includes('solve') ||
                      rawStage.includes('model_b') ||
                      rawStage.includes('review');
                    const isAudit =
                      rawStage.includes('audit') || rawStage.includes('semantic');
                    const stageLabel =
                      rawStage.includes('gen') || rawStage.includes('model_a') || rawStage.includes('blueprint')
                        ? 'Model A · Sinh đề'
                        : isModelB
                          ? 'Model B · Giải SQL'
                          : isAudit
                            ? 'Semantic Audit'
                            : c.stage || c.purpose || 'Model A · Sinh đề';
                    const defaultModel = isModelB || isAudit ? 'qwen2.5-coder:7b' : 'llama3';
                    const rawModel = String(c.model || c.model_name || '');
                    const displayModel =
                      rawModel.toLowerCase().includes('llama') ||
                      rawModel.toLowerCase().includes('qwen')
                        ? rawModel
                        : defaultModel;
                    const statusUpper = String(c.status || 'SUCCEEDED').toUpperCase();
                    const latencyMs = c.latency_ms ?? c.duration_ms ?? 0;
                    const latencyText =
                      latencyMs >= 1000
                        ? `${latencyMs} ms (${(latencyMs / 1000).toFixed(2)}s)`
                        : `${latencyMs} ms`;
                    const inTok = c.input_tokens ?? c.prompt_tokens ?? 0;
                    const outTok = c.output_tokens ?? c.completion_tokens ?? 0;
                    const matchedDraft = c.draft_id
                      ? drafts.find((d: any) => d.draft_id === c.draft_id)
                      : null;
                    const draftTitle = c.draft_title || matchedDraft?.title || '';
                    return (
                      <div
                        key={c.call_id || c.id || idx}
                        className="p-3.5 flex flex-wrap items-center justify-between gap-2 text-xs"
                      >
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2 text-[11px]">
                            <span className="text-[#94a3b8]">
                              {formatVnTime(c.created_at || c.started_at || c.timestamp)}
                            </span>
                            <span className="px-1.5 py-0.5 rounded bg-[#162238] text-[#38bdf8] font-semibold">
                              {stageLabel}
                            </span>
                            <span className="text-white font-medium">
                              {displayModel}
                            </span>
                          </div>
                          <div className=" text-[11px] text-[#64748b] flex flex-wrap gap-3">
                            <span>Phản hồi: {latencyText}</span>
                            <span>
                              Token: {inTok} -&gt; {outTok}
                            </span>
                          </div>
                          {c.draft_id && (
                            <div className="flex flex-wrap items-center gap-2 pt-0.5">
                              <span className="text-[11px] text-[#cbd5e1]">
                                Đề nháp #{c.draft_id}: {draftTitle}
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  setSubTab('drafts');
                                  inspectDraft(c.draft_id);
                                }}
                                className="px-2 py-0.5 rounded bg-[#38bdf8]/15 hover:bg-[#38bdf8]/25 border border-[#38bdf8]/40 text-[11px] font-semibold text-[#38bdf8] transition"
                              >
                                Mở đề #{c.draft_id}
                              </button>
                            </div>
                          )}
                        </div>
                        <span
                          className={` text-[11px] px-2 py-0.5 rounded border uppercase ${
                            statusUpper === 'SUCCEEDED' || statusUpper === 'DONE'
                              ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                              : statusUpper === 'FAILED' || statusUpper === 'ERROR'
                                ? 'bg-rose-950/40 border-rose-800/60 text-rose-300'
                                : 'bg-amber-950/40 border-amber-800/60 text-amber-300'
                          }`}
                        >
                          {statusUpper}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
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
              <label className="block text-[#94a3b8] mb-1">
                Tiêu đề bộ đề tuần mới
              </label>
              <input
                value={newWeekTitle}
                onChange={(e) => setNewWeekTitle(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-[#080c14] border border-[#1f2b42] text-white"
              />
            </div>
            <div>
              <label className="block text-[#94a3b8] mb-1">
                Ngày bắt đầu (week_start)
              </label>
              <input
                type="date"
                value={newWeekStart}
                onChange={(e) => setNewWeekStart(e.target.value)}
                className="px-3 py-1.5 rounded bg-[#080c14] border border-[#1f2b42] text-white"
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
                  <div className=" text-[11px] text-[#64748b] mt-0.5">
                    Week Start: {w.week_start} · Status: {w.status.toUpperCase()}
                  </div>
                </div>
                <div className="flex gap-2">
                  {w.status === 'draft' && (
                    <button
                      onClick={() => {
                        setMsg(null);
                        setErr(null);
                        publishAdminWeeklySet(w.set_id)
                          .then(() => {
                            setMsg(`Đã Publish bộ đề tuần #${w.set_id} (${w.title}).`);
                            loadWeekly();
                          })
                          .catch((e: any) =>
                            setErr(
                              e?.response?.data?.message ||
                                e?.response?.data?.error?.message ||
                                'Không thể Publish (hãy đóng bộ đề đang mở trước)'
                            )
                          );
                      }}
                      className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium"
                    >
                      Publish Bộ đề
                    </button>
                  )}
                  {w.status === 'published' && (
                    <button
                      onClick={() => {
                        setMsg(null);
                        setErr(null);
                        closeAdminWeeklySet(w.set_id)
                          .then(() => {
                            setMsg(`Đã đóng chu kỳ bộ đề tuần #${w.set_id} (${w.title}).`);
                            loadWeekly();
                          })
                          .catch((e: any) =>
                            setErr(
                              e?.response?.data?.message ||
                                e?.response?.data?.error?.message ||
                                'Không thể đóng chu kỳ tuần'
                            )
                          );
                      }}
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
                <tr className="bg-[#0a0f1a] border-b border-[#1d283a] text-[#64748b]">
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
                    <td className="py-2.5 px-4 text-[#64748b]">
                      #{u.user_id}
                    </td>
                    <td className="py-2.5 px-4 font-medium text-white">
                      {u.display_name || u.username}{' '}
                      <span className=" text-[#64748b]">(@{u.username})</span>
                    </td>
                    <td className="py-2.5 px-4 text-[#94a3b8]">{u.email}</td>
                    <td className="py-2.5 px-4">
                      <span
                        className={` px-2 py-0.5 rounded uppercase text-[10px] border ${
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
                        className={` px-2 py-0.5 rounded uppercase text-[10px] border ${
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
                        className="px-2.5 py-1 rounded bg-[#162032] hover:bg-[#1f2e47] text-[#cbd5e1] border border-[#263552]"
                      >
                        Đổi Role
                      </button>
                      <button
                        onClick={() => handleToggleUser(u, 'status')}
                        className="px-2.5 py-1 rounded bg-[#162032] hover:bg-rose-950/60 text-[#cbd5e1] hover:text-rose-200 border border-[#263552]"
                      >
                        {u.status === 'active' ? 'Khóa' : 'Mở khóa'}
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
                className="p-4 flex flex-wrap items-center justify-between gap-3 text-xs"
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
                    disabled={st.mutable === false}
                    onChange={(e) =>
                      setSettingEdits((prev) => ({
                        ...prev,
                        [st.key]: e.target.value,
                      }))
                    }
                    className={`px-3 py-1.5 rounded bg-[#080c14] border border-[#1f2b42] text-white w-64 ${
                      st.mutable === false ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  />
                  {st.mutable === false ? (
                    <span className="px-2.5 py-1.5 rounded bg-[#162032] border border-[#263552] text-[#64748b] text-[11px]">
                      Cố định
                    </span>
                  ) : (
                    <button
                      onClick={() => handleUpdateSetting(st.key)}
                      className="px-3 py-1.5 rounded bg-[#162238] hover:bg-[#1f304d] border border-[#293f66] text-[#38bdf8]"
                    >
                      Lưu
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
