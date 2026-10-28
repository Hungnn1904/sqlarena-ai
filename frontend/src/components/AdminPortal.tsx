'use client';

import React, { useEffect, useState } from 'react';
import {
  getGenerationJobs,
  createGenerationJob,
  getLlmUsage,
  getAdminDrafts,
  getAdminDraftDetail,
  editAdminDraft,
  approveAdminDraft,
  rejectAdminDraft,
  getAdminWeeklySets,
  publishAdminWeeklySet,
  closeAdminWeeklySet,
  getAdminUsers,
  updateAdminUser,
} from '../lib/api';

export default function AdminPortal({ isAdmin }: { isAdmin: boolean }) {
  const [subTab, setSubTab] = useState<'drafts' | 'jobs' | 'weekly' | 'users'>('drafts');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Drafts state
  const [draftStatus, setDraftStatus] = useState<string>('');
  const [drafts, setDrafts] = useState<any[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<any>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editQuestion, setEditQuestion] = useState('');
  const [reviewNote, setReviewNote] = useState('');

  // Generation jobs state
  const [jobs, setJobs] = useState<any[]>([]);
  const [llmUsage, setLlmUsage] = useState<any>(null);
  const [jobDiff, setJobDiff] = useState(2);
  const [jobCount, setJobCount] = useState(3);
  const [jobTopic, setJobTopic] = useState('Phân tích doanh thu & hành vi khách hàng B2B');
  const [jobSkills, setJobSkills] = useState<number[]>([2, 3]);

  // Weekly sets & Users state
  const [weeklySets, setWeeklySets] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [userSearch, setUserSearch] = useState('');

  const loadDrafts = async () => {
    try {
      const r = await getAdminDrafts({ status: draftStatus || undefined });
      setDrafts(r.items || []);
      if (r.items?.length > 0 && !selectedDraft) {
        inspectDraft(r.items[0].draft_id);
      }
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Cần quyền Admin để truy cập');
    }
  };

  const inspectDraft = async (draftId: number) => {
    try {
      const d = await getAdminDraftDetail(draftId);
      setSelectedDraft(d);
      setEditTitle(d.title || '');
      setEditQuestion(d.question || '');
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Không tải được chi tiết draft');
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

  useEffect(() => {
    if (!isAdmin) return;
    setErr(null);
    if (subTab === 'drafts') loadDrafts();
    if (subTab === 'jobs') loadJobs();
    if (subTab === 'weekly') loadWeekly();
    if (subTab === 'users') loadUsers();
  }, [subTab, draftStatus, isAdmin]);

  if (!isAdmin) {
    return (
      <div className="bg-[#111827] border border-[#ffb830]/40 rounded-xl p-8 text-center space-y-3">
        <div className="text-lg font-bold text-[#ffb830]">
          🛡️ Khu vực Quản trị AI Pipeline & Kiểm duyệt (Yêu cầu quyền ADMIN)
        </div>
        <p className="text-xs text-[#8ba3c7] max-w-lg mx-auto">
          Bạn đang đăng nhập với vai trò Học viên. Nhấn nút{' '}
          <strong className="text-[#ffb830]">&quot;🛡️ Admin (admin)&quot;</strong> trên thanh điều hướng phía trên để chuyển sang tài khoản Quản trị viên trong 1 click!
        </p>
      </div>
    );
  }

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
      setMsg(`Đã khởi tạo Generation Job #${job.job_id} (trạng thái: ${job.status})!`);
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
        note: reviewNote || 'Admin xác nhận đáp án hợp lệ',
      });
      setSelectedDraft(d);
      setMsg(`Đã phê duyệt Draft #${d.draft_id} -> Promote sang live.questions!`);
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi approve draft');
    }
  };

  const handleRejectDraft = async () => {
    if (!selectedDraft) return;
    setMsg(null);
    setErr(null);
    try {
      const d = await rejectAdminDraft(
        selectedDraft.draft_id,
        reviewNote || 'Đề chưa rõ nghĩa hoặc thiếu điều kiện biên'
      );
      setSelectedDraft(d);
      setMsg(`Đã từ chối Draft #${d.draft_id}`);
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi reject draft');
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
        note: reviewNote || 'Admin hiệu đính nội dung đề',
      });
      setSelectedDraft(d);
      setMsg(`Đã cập nhật nội dung Draft #${d.draft_id} và đưa lại hàng đợi kiểm duyệt!`);
      loadDrafts();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Lỗi cập nhật draft');
    }
  };

  const handleToggleUser = async (u: any, field: 'role' | 'status') => {
    try {
      const payload =
        field === 'role'
          ? { role: (u.role === 'admin' ? 'learner' : 'admin') as 'learner' | 'admin' }
          : { status: (u.status === 'active' ? 'locked' : 'active') as 'active' | 'locked' };
      await updateAdminUser(u.user_id, payload);
      setMsg(`Đã cập nhật tài khoản @${u.username}`);
      loadUsers();
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Không thể cập nhật tài khoản');
    }
  };

  return (
    <div className="space-y-4">
      {/* Sub-navigation */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-[#111827] border border-[#1e2d45] rounded-xl p-3">
        <div className="flex flex-wrap gap-2">
          {[
            { id: 'drafts', label: '🔍 Kiểm duyệt Câu hỏi nháp (Human-in-the-Loop)' },
            { id: 'jobs', label: '🤖 Khởi chạy AI Pipeline (Model A + Model B)' },
            { id: 'weekly', label: '📅 Quản lý Bộ đề Tuần' },
            { id: 'users', label: '👥 Quản lý Tài khoản & Phân quyền' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setSubTab(t.id as any)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
                subTab === t.id
                  ? 'bg-[#ffb830] text-[#0a0e17]'
                  : 'bg-[#0a0e17] text-[#8ba3c7] border border-[#1e2d45]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {err && (
        <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/30 text-red-300 text-xs">
          ❌ {err}
        </div>
      )}
      {msg && (
        <div className="p-3 rounded-lg bg-[#00e5a0]/15 border border-[#00e5a0]/30 text-[#00e5a0] text-xs">
          ✓ {msg}
        </div>
      )}

      {/* TAB 1: DRAFT REVIEW */}
      {subTab === 'drafts' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-5 bg-[#111827] border border-[#1e2d45] rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">Hàng đợi Draft AI</h3>
              <select
                value={draftStatus}
                onChange={(e) => setDraftStatus(e.target.value)}
                className="px-2.5 py-1 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
              >
                <option value="">Tất cả trạng thái</option>
                <option value="needs_human">⚠️ Cần người duyệt (needs_human)</option>
                <option value="pending">⏳ Đang chờ (pending)</option>
                <option value="approved">✓ Đã duyệt (approved)</option>
                <option value="rejected">✕ Đã từ chối (rejected)</option>
              </select>
            </div>

            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {drafts.map((d) => (
                <button
                  key={d.draft_id}
                  onClick={() => inspectDraft(d.draft_id)}
                  className={`w-full text-left p-3 rounded-lg border transition ${
                    selectedDraft?.draft_id === d.draft_id
                      ? 'bg-[#ffb830]/10 border-[#ffb830]'
                      : 'bg-[#0a0e17] border-[#1e2d45]'
                  }`}
                >
                  <div className="flex items-center justify-between text-[0.68rem] font-mono mb-1">
                    <span className="text-[#00d4ff]">Draft #{d.draft_id} · Job #{d.job_id}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded uppercase ${
                        d.status === 'needs_human'
                          ? 'bg-[#ffb830]/20 text-[#ffb830]'
                          : d.status === 'approved'
                          ? 'bg-[#00e5a0]/20 text-[#00e5a0]'
                          : 'bg-red-500/20 text-red-400'
                      }`}
                    >
                      {d.status}
                    </span>
                  </div>
                  <div className="text-xs font-bold text-white">{d.title}</div>
                  {d.status_reason && (
                    <div className="text-[0.68rem] text-[#8ba3c7] mt-1 line-clamp-2">
                      {d.status_reason}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-7 bg-[#111827] border border-[#1e2d45] rounded-xl p-5 space-y-4">
            {selectedDraft ? (
              <>
                <div className="flex items-center justify-between border-b border-[#1e2d45] pb-3">
                  <div>
                    <span className="font-mono text-xs text-[#ffb830]">
                      CHI TIẾT KIỂM DUYỆT DRAFT #{selectedDraft.draft_id}
                    </span>
                    <h3 className="text-base font-bold text-white mt-0.5">
                      Model sinh: {selectedDraft.gen_model} ({selectedDraft.gen_prompt_version})
                    </h3>
                  </div>
                  <span className="font-mono text-xs px-2.5 py-1 rounded bg-[#0a0e17] border border-[#1e2d45] text-[#00d4ff]">
                    Trạng thái: {selectedDraft.status.toUpperCase()}
                  </span>
                </div>

                <div className="space-y-2">
                  <label className="block text-xs font-mono text-[#8ba3c7]">Tiêu đề câu hỏi</label>
                  <input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
                  />
                  <label className="block text-xs font-mono text-[#8ba3c7]">Nội dung đề bài</label>
                  <textarea
                    rows={3}
                    value={editQuestion}
                    onChange={(e) => setEditQuestion(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
                  />
                </div>

                <div>
                  <div className="text-xs font-mono text-[#00e5a0] mb-1">
                    SQL Tham chiếu & Kết quả Self-Solve từ Model B:
                  </div>
                  <pre className="p-3 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs font-mono text-[#dbe7ff] overflow-x-auto">
                    {selectedDraft.reference_sql ||
                      selectedDraft.self_solve_runs?.[0]?.model_sql ||
                      '-- Chưa có SQL'}
                  </pre>
                </div>

                <div className="space-y-2 pt-2 border-t border-[#1e2d45]">
                  <input
                    value={reviewNote}
                    onChange={(e) => setReviewNote(e.target.value)}
                    placeholder="Ghi chú kiểm duyệt của Admin (lưu vào audit_logs & admin_overrides)..."
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={handleApproveDraft}
                      disabled={selectedDraft.status !== 'needs_human'}
                      className="px-4 py-2 rounded-lg bg-[#00e5a0] text-[#0a0e17] text-xs font-bold disabled:opacity-40"
                    >
                      ✓ Phê duyệt & Promote sang Ngân hàng Đề
                    </button>
                    <button
                      onClick={handleEditDraft}
                      disabled={!['needs_human', 'rejected'].includes(selectedDraft.status)}
                      className="px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0e17] text-xs font-bold disabled:opacity-40"
                    >
                      ✎ Lưu chỉnh sửa & Đưa lại hàng đợi
                    </button>
                    <button
                      onClick={handleRejectDraft}
                      disabled={selectedDraft.status !== 'needs_human'}
                      className="px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/40 text-red-300 text-xs font-bold disabled:opacity-40"
                    >
                      ✕ Từ chối Draft
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-xs text-[#8ba3c7]">Chọn một draft bên trái để xem chi tiết.</div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: AI GENERATION JOBS */}
      {subTab === 'jobs' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <form
            onSubmit={handleCreateJob}
            className="lg:col-span-5 bg-[#111827] border border-[#1e2d45] rounded-xl p-5 space-y-3"
          >
            <h3 className="text-sm font-bold text-white">
              🚀 Khởi chạy Pipeline Sinh đề AI (Model A + Model B)
            </h3>
            <div>
              <label className="block text-xs text-[#8ba3c7] mb-1">Chủ đề nghiệp vụ (Topic)</label>
              <input
                value={jobTopic}
                onChange={(e) => setJobTopic(e.target.value)}
                className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[#8ba3c7] mb-1">Độ khó</label>
                <select
                  value={jobDiff}
                  onChange={(e) => setJobDiff(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
                >
                  <option value={1}>1 — Easy</option>
                  <option value={2}>2 — Medium</option>
                  <option value={3}>3 — Hard</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-[#8ba3c7] mb-1">Số lượng câu sinh</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={jobCount}
                  onChange={(e) => setJobCount(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
                />
              </div>
            </div>
            <button
              type="submit"
              className="w-full py-2.5 rounded-lg bg-gradient-to-r from-[#ffb830] to-[#00e5a0] text-[#0a0e17] font-bold text-xs"
            >
              ⚡ Đẩy Job vào Hàng đợi Generation Worker
            </button>
          </form>

          <div className="lg:col-span-7 bg-[#111827] border border-[#1e2d45] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">Tiến độ các Job Sinh đề & Ngân sách LLM</h3>
              {llmUsage && (
                <span className="text-xs font-mono text-[#00d4ff]">
                  LLM Calls hôm nay: {llmUsage.calls_used ?? 0}/{llmUsage.daily_call_cap ?? 200}
                </span>
              )}
            </div>
            <div className="space-y-2">
              {jobs.map((j) => (
                <div
                  key={j.job_id}
                  className="p-3 rounded-lg bg-[#0a0e17] border border-[#1e2d45] flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-bold text-white">
                      Job #{j.job_id} — {j.topic || 'Enterprise SQL'}
                    </div>
                    <div className="font-mono text-[0.68rem] text-[#8ba3c7]">
                      Độ khó: {j.difficulty} · Đã tạo: {j.created_count}/{j.requested_count} câu
                    </div>
                  </div>
                  <span className="font-mono px-2 py-0.5 rounded bg-[#00e5a0]/15 text-[#00e5a0] uppercase">
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
        <div className="bg-[#111827] border border-[#1e2d45] rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-white">Danh sách Bộ đề Tuần (live.weekly_sets)</h3>
          <div className="space-y-2">
            {weeklySets.map((w) => (
              <div
                key={w.set_id}
                className="p-3.5 rounded-lg bg-[#0a0e17] border border-[#1e2d45] flex flex-wrap items-center justify-between gap-2 text-xs"
              >
                <div>
                  <div className="font-bold text-white">
                    #{w.set_id} · {w.title}
                  </div>
                  <div className="font-mono text-[#8ba3c7]">
                    Tuần bắt đầu: {w.week_start} · Trạng thái: {w.status.toUpperCase()}
                  </div>
                </div>
                <div className="flex gap-2">
                  {w.status === 'draft' && (
                    <button
                      onClick={() => publishAdminWeeklySet(w.set_id).then(loadWeekly)}
                      className="px-3 py-1 rounded bg-[#00e5a0] text-[#0a0e17] font-bold"
                    >
                      Xuất bản (Publish)
                    </button>
                  )}
                  {w.status === 'published' && (
                    <button
                      onClick={() => closeAdminWeeklySet(w.set_id).then(loadWeekly)}
                      className="px-3 py-1 rounded bg-red-500/20 text-red-300 border border-red-500/40"
                    >
                      Đóng bộ đề
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: USER MANAGEMENT */}
      {subTab === 'users' && (
        <div className="bg-[#111827] border border-[#1e2d45] rounded-xl p-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-white">
              👥 Quản lý Tài khoản & Phân quyền (live.users)
            </h3>
            <div className="flex gap-2">
              <input
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                placeholder="Tìm username hoặc email..."
                className="px-3 py-1.5 rounded bg-[#0a0e17] border border-[#1e2d45] text-xs text-white"
              />
              <button
                onClick={loadUsers}
                className="px-3 py-1.5 rounded bg-[#00d4ff] text-[#0a0e17] text-xs font-bold"
              >
                Tìm kiếm
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#1e2d45] text-[#8ba3c7] font-mono">
                  <th className="py-2 px-3">ID</th>
                  <th className="py-2 px-3">Tài khoản</th>
                  <th className="py-2 px-3">Email</th>
                  <th className="py-2 px-3">Vai trò</th>
                  <th className="py-2 px-3">Trạng thái</th>
                  <th className="py-2 px-3">Hành động</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} className="border-b border-[#1e2d45]/50">
                    <td className="py-2.5 px-3 font-mono text-[#5a7298]">#{u.user_id}</td>
                    <td className="py-2.5 px-3 font-bold text-white">
                      {u.display_name || u.username}{' '}
                      <span className="font-mono text-[#5a7298]">(@{u.username})</span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[#8ba3c7]">{u.email}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`font-mono px-2 py-0.5 rounded uppercase text-[0.68rem] ${
                          u.role === 'admin'
                            ? 'bg-[#ffb830]/20 text-[#ffb830]'
                            : 'bg-[#00d4ff]/20 text-[#00d4ff]'
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`font-mono px-2 py-0.5 rounded uppercase text-[0.68rem] ${
                          u.status === 'active'
                            ? 'bg-[#00e5a0]/20 text-[#00e5a0]'
                            : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        {u.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 flex gap-2">
                      <button
                        onClick={() => handleToggleUser(u, 'role')}
                        className="px-2 py-1 rounded bg-[#1e2d45] text-white hover:bg-[#00d4ff] hover:text-[#0a0e17]"
                      >
                        Đổi Role
                      </button>
                      <button
                        onClick={() => handleToggleUser(u, 'status')}
                        className="px-2 py-1 rounded bg-red-500/15 text-red-300 hover:bg-red-500/30"
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
    </div>
  );
}
