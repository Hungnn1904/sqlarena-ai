'use client';

import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  Search,
  GripVertical,
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  ArrowRight,
  FolderPlus,
  Send,
  Eye,
  FilePlus2,
  Sparkles,
  Layers,
  CalendarRange,
  Users,
  Settings,
  Database,
} from 'lucide-react';
import {
  getGenerationJobs,
  createGenerationJob,
  getLlmUsage,
  getAdminGatewayStatus,
  saveAdminGatewayKey,
  runAdminWorker,
  getAdminDrafts,
  getAdminDraftDetail,
  editAdminDraft,
  approveAdminDraft,
  bulkApproveAdminDrafts,
  rejectAdminDraft,
  requeueAdminDraft,
  createManualAdminQuestion,
  getAdminQuestions,
  getAdminQuestionDetail,
  retireAdminQuestion,
  restoreAdminQuestion,
  toggleAdminQuestionSource,
  getAdminQuestionGroups,
  getAdminQuestionGroupDetail,
  createAdminQuestionGroup,
  updateAdminQuestionGroupItems,
  addAdminQuestionGroupItems,
  deleteAdminQuestionGroup,
  publishAdminQuestionGroup,
  getAdminWeeklySets,
  getAdminWeeklySetDetail,
  createAdminWeeklySet,
  updateAdminWeeklySetItems,
  publishAdminWeeklySet,
  closeAdminWeeklySet,
  getAdminUsers,
  updateAdminUser,
  getAdminSettings,
  getAdminSkills,
  updateAdminSetting,
  getDatasetSchema,
  extractApiError,
} from '../lib/api';

const TOPIC_PRESETS = [
  'Phân tích hiệu suất nhân sự & lương thưởng theo phòng ban (HR)',
  'Rà soát tồn kho, sức chứa kho vận & điều chuyển hàng hóa (Inventory)',
  'Phân tích hành vi mua sắm & phân khúc khách hàng hoạt động (CRM)',
  'Đối soát đơn hàng giao trễ, hoàn tiền & cổng thanh toán (Orders & Payments)',
  'Đánh giá biên lợi nhuận sản phẩm & nhà cung cấp chủ lực (Catalog)',
  'Kiểm soát chi phí vận hành & ngân sách phê duyệt theo quý (Finance)',
];

const SKILL_OPTIONS = [
  { id: 1, code: 'S1', name: 'SELECT / WHERE' },
  { id: 2, code: 'S2', name: 'JOIN nhiều bảng' },
  { id: 3, code: 'S3', name: 'GROUP BY / HAVING' },
  { id: 4, code: 'S4', name: 'Subquery / CTE' },
  { id: 5, code: 'S5', name: 'Window Functions' },
  { id: 6, code: 'S6', name: 'Xử lý NULL & ngoại lệ' },
];

const DIFF_LABELS: Record<number, { text: string; badge: string }> = {
  1: { text: 'Dễ', badge: 'badge-easy' },
  2: { text: 'Trung bình', badge: 'badge-medium' },
  3: { text: 'Khó', badge: 'badge-hard' },
};

function formatVnDateTime(iso?: string | null): string {
  if (!iso) return 'Chưa ghi nhận';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString('vi-VN');
}

function normalizeGroupItem(it: any) {
  const q = it?.question || it || {};
  return {
    question_id: Number(q.question_id ?? it.question_id),
    position: it?.position ?? q?.position ?? 1,
    title: q.title || it?.title || `Câu hỏi #${q.question_id ?? it.question_id}`,
    difficulty: Number(q.difficulty ?? it?.difficulty ?? 1),
    status: q.status || it?.status || 'ready',
    tables_used: Array.isArray(q.tables_used)
      ? q.tables_used
      : Array.isArray(it?.tables_used)
      ? it.tables_used
      : [],
  };
}

export default function AdminPortal({
  isAdmin,
  onJumpToWorkbench,
}: {
  isAdmin: boolean;
  onJumpToWorkbench?: () => void;
}) {
  const [step, setStep] = useState<
    'step1_create' | 'step2_drafts' | 'step3_groups' | 'step4_system'
  >('step3_groups');
  const [step1Mode, setStep1Mode] = useState<'ai' | 'manual'>('ai');
  const [step4Tab, setStep4Tab] = useState<'weekly' | 'bank' | 'users' | 'settings'>('weekly');

  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Shared Skills & Schema
  const [skillOptions, setSkillOptions] = useState(SKILL_OPTIONS);
  const [schemaTables, setSchemaTables] = useState<any[]>([]);
  const [approvalMode, setApprovalMode] = useState<'calibrated' | 'strict'>('calibrated');
  const [savingApprovalMode, setSavingApprovalMode] = useState(false);

  // Step 1A: AI Generation Jobs & apithat.dev Secret-Blind Vault
  const [jobs, setJobs] = useState<any[]>([]);
  const [llmUsage, setLlmUsage] = useState<any>(null);
  const [gatewayStatus, setGatewayStatus] = useState<any>(null);
  const [gatewayKeyInput, setGatewayKeyInput] = useState('');
  const [gatewayModelInput, setGatewayModelInput] = useState('gpt-5.6-sol');
  const [savingGatewayKey, setSavingGatewayKey] = useState(false);
  const [showGatewayForm, setShowGatewayForm] = useState(false);
  const [jobDiff, setJobDiff] = useState(1);
  const [jobCount, setJobCount] = useState(3);
  const [jobTopic, setJobTopic] = useState('');
  const [jobSkills, setJobSkills] = useState<number[]>([1, 2]);
  const [submittingJob, setSubmittingJob] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);

  // Step 1B: Manual Question Composer
  const [manualTitle, setManualTitle] = useState('');
  const [manualQuestion, setManualQuestion] = useState('');
  const [manualSql, setManualSql] = useState(
    'SELECT category_id, name\nFROM categories\nORDER BY category_id ASC;'
  );
  const [manualDiff, setManualDiff] = useState<number>(1);
  const [manualCompareMode, setManualCompareMode] = useState<'unordered' | 'ordered'>('unordered');
  const [manualSkills, setManualSkills] = useState<number[]>([1]);
  const [savingManual, setSavingManual] = useState(false);
  const [lastManualQuestion, setLastManualQuestion] = useState<any>(null);

  // Step 2: Draft Review & Bulk Approve / Direct Group
  const [draftStatusFilter, setDraftStatusFilter] = useState<string>('');
  const [drafts, setDrafts] = useState<any[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<any>(null);
  const [checkedDraftIds, setCheckedDraftIds] = useState<number[]>([]);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [showBulkGroupPanel, setShowBulkGroupPanel] = useState(false);
  const [bulkGroupTargetId, setBulkGroupTargetId] = useState<string>('NEW');
  const [bulkGroupNewName, setBulkGroupNewName] = useState('');

  const [editTitle, setEditTitle] = useState('');
  const [editQuestion, setEditQuestion] = useState('');
  const [reviewNote, setReviewNote] = useState('');
  const [sqlSourceChoice, setSqlSourceChoice] = useState<'ref' | 'custom' | number>('ref');
  const [customSqlText, setCustomSqlText] = useState('');

  // Step 3: Question Groups (2-Column Drag & Pick Composer + 1-Click Publish)
  const [bankUnassignedOnly, setBankUnassignedOnly] = useState<boolean>(true);
  const [bankDiffFilter, setBankDiffFilter] = useState<number | undefined>(undefined);
  const [bankSearch, setBankSearch] = useState<string>('');
  const [bankQuestions, setBankQuestions] = useState<any[]>([]);
  const [pickedBankIds, setPickedBankIds] = useState<number[]>([]);

  const [groups, setGroups] = useState<any[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [groupDetail, setGroupDetail] = useState<any>(null);
  const [newGroupName, setNewGroupName] = useState('');
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [groupBusy, setGroupBusy] = useState(false);

  const [draggingQuestionId, setDraggingQuestionId] = useState<number | null>(null);
  const [draggingGroupItemIdx, setDraggingGroupItemIdx] = useState<number | null>(null);
  const [isOverDropZone, setIsOverDropZone] = useState<boolean>(false);

  const [publishMode, setPublishMode] = useState<'append_active' | 'new_weekly_set'>('append_active');
  const [publishSetTitle, setPublishSetTitle] = useState('');
  const [lastPublishReceipt, setLastPublishReceipt] = useState<any>(null);

  // Question Preview Cache (used in Step 3 & Step 4)
  const [previewQuestionId, setPreviewQuestionId] = useState<number | null>(null);
  const [previewCache, setPreviewCache] = useState<Record<number, any>>({});

  // Step 4: Weekly Sets, All Questions Bank, Users & Settings
  const [weeklySets, setWeeklySets] = useState<any[]>([]);
  const [selectedWeeklySetId, setSelectedWeeklySetId] = useState<number | null>(null);
  const [weeklySetDetail, setWeeklySetDetail] = useState<any>(null);
  const [loadingWeeklyDetail, setLoadingWeeklyDetail] = useState(false);
  const [newWeekTitle, setNewWeekTitle] = useState('Bộ đề thực hành SQL hàng tuần');
  const [newWeekStart, setNewWeekStart] = useState(() => new Date().toISOString().slice(0, 10));

  const [allBankStatusFilter, setAllBankStatusFilter] = useState<string>('');
  const [allBankQuestions, setAllBankQuestions] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [settingsList, setSettingsList] = useState<any[]>([]);
  const [settingEdits, setSettingEdits] = useState<Record<string, string>>({});

  // Data Loaders
  const loadSkillsAndSchema = async () => {
    try {
      const [skRes, scRes] = await Promise.all([
        getAdminSkills().catch(() => null),
        getDatasetSchema().catch(() => null),
      ]);
      const items = (skRes?.items || []).filter((s: any) => s.is_active !== false);
      if (items.length > 0) {
        const mapped = items.map((s: any) => ({
          id: s.skill_id ?? s.id,
          code: s.code,
          name: s.name,
        }));
        setSkillOptions(mapped);
        const validIds = new Set(mapped.map((m: any) => m.id));
        setJobSkills((prev) => {
          const kept = prev.filter((id) => validIds.has(id));
          return kept.length > 0 ? kept : mapped.slice(0, 2).map((m: any) => m.id);
        });
        setManualSkills((prev) => {
          const kept = prev.filter((id) => validIds.has(id));
          return kept.length > 0 ? kept : [mapped[0].id];
        });
      }
      if (scRes?.tables) {
        setSchemaTables(scRes.tables);
      }
    } catch {}
  };

  const loadSettings = async () => {
    try {
      const s = await getAdminSettings();
      const items = s?.items || [];
      setSettingsList(items);
      const map: Record<string, string> = {};
      items.forEach((it: any) => {
        map[it.key] = typeof it.value === 'string' ? it.value : JSON.stringify(it.value);
        if (it.key === 'review.approval_mode') {
          const val = String(it.value).replace(/^"|"$/g, '');
          if (val === 'strict' || val === 'calibrated') {
            setApprovalMode(val);
          }
        }
      });
      setSettingEdits(map);
    } catch {}
  };

  const inspectDraft = async (draftId: number) => {
    try {
      const d = await getAdminDraftDetail(draftId);
      setSelectedDraft(d);
      setEditTitle(d.title || '');
      setEditQuestion(d.question || '');
      const firstValidRun = (d.self_solve_runs || []).find(
        (r: any) => r.exec_status === 'ok' || r.matched_datasets > 0
      );
      if (d.reference_sql) {
        setSqlSourceChoice('ref');
        setCustomSqlText(d.reference_sql);
      } else if (firstValidRun) {
        setSqlSourceChoice(firstValidRun.run_id);
        setCustomSqlText(firstValidRun.model_sql || '');
      } else {
        setSqlSourceChoice('custom');
        setCustomSqlText(d.self_solve_runs?.[0]?.model_sql || '');
      }
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tải được chi tiết bản nháp'));
    }
  };

  const loadDrafts = async () => {
    try {
      const r = await getAdminDrafts({ page_size: 100 });
      const list = r?.items || [];
      setDrafts(list);
      if (list.length > 0 && !selectedDraft) {
        inspectDraft(list[0].draft_id);
      }
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tải được danh sách bản nháp'));
    }
  };

  const loadJobs = async () => {
    try {
      const [j, u, gw] = await Promise.all([
        getGenerationJobs().catch(() => ({ items: [] })),
        getLlmUsage().catch(() => null),
        getAdminGatewayStatus().catch(() => null),
      ]);
      setJobs(j?.items || []);
      if (u) setLlmUsage(u);
      if (gw) {
        setGatewayStatus(gw);
        if (gw.preferred_model) setGatewayModelInput(gw.preferred_model);
      }
    } catch {}
  };

  const handleSaveGatewayKey = async (ev: React.FormEvent) => {
    ev.preventDefault();
    const trimmed = gatewayKeyInput.trim();
    if (!trimmed) {
      setErr('Vui lòng dán khóa API từ trang https://apithat.dev/keys');
      return;
    }
    setSavingGatewayKey(true);
    setErr(null);
    setMsg(null);
    try {
      const info = await saveAdminGatewayKey({
        api_key: trimmed,
        base_url: 'https://apithat.dev/v1',
        preferred_model: gatewayModelInput.trim() || 'gpt-5.6-sol',
        persist_env: true,
      });
      setGatewayStatus(info);
      setGatewayKeyInput('');
      setShowGatewayForm(false);
      setMsg(
        `Đã kết nối apithat.dev thành công (${info.masked_key}) · Model chính: ${info.preferred_model}`
      );
      await loadJobs();
    } catch (e: any) {
      setErr(extractApiError(e, 'Không xác thực được khóa API trên apithat.dev'));
    } finally {
      setSavingGatewayKey(false);
    }
  };

  const loadBankQuestions = async () => {
    try {
      const res = await getAdminQuestions({
        status: 'ready',
        difficulty: bankDiffFilter,
        q: bankSearch.trim() || undefined,
        unassigned_only: bankUnassignedOnly ? true : undefined,
        page_size: 100,
      });
      setBankQuestions(res?.items || []);
    } catch {}
  };

  const loadAllBankQuestions = async () => {
    try {
      const res = await getAdminQuestions({
        status: allBankStatusFilter || undefined,
        page_size: 100,
      });
      setAllBankQuestions(res?.items || []);
    } catch {}
  };

  const loadGroupDetail = async (groupId: number) => {
    try {
      const d = await getAdminQuestionGroupDetail(groupId);
      setGroupDetail(d);
      setSelectedGroupId(groupId);
      if (!publishSetTitle) {
        setPublishSetTitle(d?.name || '');
      }
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tải được chi tiết nhóm đề'));
    }
  };

  const loadGroups = async (preferGroupId?: number) => {
    try {
      const res = await getAdminQuestionGroups();
      const list = res?.items || [];
      setGroups(list);
      const targetId =
        preferGroupId ??
        (selectedGroupId && list.some((g: any) => g.group_id === selectedGroupId)
          ? selectedGroupId
          : list.find((g: any) => g.status === 'draft')?.group_id ?? list[0]?.group_id ?? null);
      if (targetId) {
        await loadGroupDetail(targetId);
      } else {
        setSelectedGroupId(null);
        setGroupDetail(null);
      }
    } catch {}
  };

  const inspectWeeklySet = async (setId: number) => {
    setSelectedWeeklySetId(setId);
    setLoadingWeeklyDetail(true);
    try {
      const detail = await getAdminWeeklySetDetail(setId);
      setWeeklySetDetail(detail);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tải được danh sách câu hỏi trong bộ đề tuần'));
    } finally {
      setLoadingWeeklyDetail(false);
    }
  };

  const loadWeekly = async () => {
    try {
      const w = await getAdminWeeklySets();
      const list = w?.items || [];
      setWeeklySets(list);
      if (list.length > 0) {
        const activeOrFirst =
          (selectedWeeklySetId && list.find((x: any) => x.set_id === selectedWeeklySetId)?.set_id) ||
          list.find((x: any) => x.status === 'published')?.set_id ||
          list[0].set_id;
        inspectWeeklySet(activeOrFirst);
      }
    } catch {}
  };

  const loadUsers = async () => {
    try {
      const u = await getAdminUsers({ q: userSearch.trim() || undefined });
      setUsers(u?.items || []);
    } catch {}
  };

  useEffect(() => {
    if (!isAdmin) return;
    loadSkillsAndSchema();
    loadSettings();
    loadDrafts();
    loadGroups();
    loadBankQuestions();
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    loadBankQuestions();
  }, [bankUnassignedOnly, bankDiffFilter]);

  useEffect(() => {
    if (!isAdmin) return;
    if (step === 'step1_create') loadJobs();
    if (step === 'step2_drafts') {
      loadDrafts();
      loadGroups();
    }
    if (step === 'step3_groups') {
      loadBankQuestions();
      loadGroups();
    }
    if (step === 'step4_system') {
      if (step4Tab === 'weekly') loadWeekly();
      if (step4Tab === 'bank') loadAllBankQuestions();
      if (step4Tab === 'users') loadUsers();
      if (step4Tab === 'settings') loadSettings();
    }
  }, [step, step4Tab, allBankStatusFilter, isAdmin]);

  // Poll running AI job
  const activeRunningJob = jobs.find(
    (j: any) => j.status === 'queued' || j.status === 'running'
  );
  const isGenerating = Boolean(submittingJob || activeRunningJob);

  useEffect(() => {
    if (!isAdmin || !activeRunningJob) {
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
    }, 2500);
    return () => {
      clearInterval(tick);
      clearInterval(poll);
    };
  }, [activeRunningJob?.job_id, activeRunningJob?.status, isAdmin]);

  if (!isAdmin) {
    return (
      <div className="bg-surface border border-line rounded-xl p-8 text-center space-y-3">
        <div className="inline-flex items-center justify-center w-11 h-11 rounded-full badge-medium">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="text-base font-bold text-ink">
          Cổng Quản trị &amp; Ra đề yêu cầu quyền Giảng viên / Admin
        </div>
        <p className="text-sm text-text2 max-w-md mx-auto leading-relaxed">
          Bạn đang đăng nhập bằng tài khoản Sinh viên. Hãy mở menu <strong>Chế độ Demo</strong> ở góc phải phía trên để chuyển sang cổng Giảng viên.
        </p>
      </div>
    );
  }

  // Handlers — Approval Mode Toggle
  const handleSwitchApprovalMode = async (nextMode: 'calibrated' | 'strict') => {
    setSavingApprovalMode(true);
    setErr(null);
    setMsg(null);
    try {
      await updateAdminSetting('review.approval_mode', nextMode);
      setApprovalMode(nextMode);
      setMsg(
        nextMode === 'calibrated'
          ? 'Đã bật chế độ duyệt Thông minh / Nới lỏng hợp lý (vẫn đảm bảo SQL chạy đúng kết quả thực tế).'
          : 'Đã bật chế độ duyệt Khắt khe tuyệt đối (cả 3 lượt giải Model B phải đồng thuận hoàn toàn).'
      );
      loadSettings();
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể đổi chế độ kiểm duyệt'));
    } finally {
      setSavingApprovalMode(false);
    }
  };

  // Handlers — Step 1A: AI Job
  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating) return;
    setMsg(null);
    setErr(null);
    setSubmittingJob(true);
    const chosenTopic =
      jobTopic.trim() || TOPIC_PRESETS[Math.floor(Math.random() * TOPIC_PRESETS.length)];
    try {
      const job = await createGenerationJob({
        difficulty: jobDiff,
        skill_ids: jobSkills.length ? jobSkills : [skillOptions[0]?.id ?? 1],
        requested_count: jobCount,
        quantity: jobCount,
        topic: chosenTopic,
        auto_run: true,
      });
      setMsg(
        job.status === 'done'
          ? `Đã sinh xong Job #${job.job_id} (${job.created_count}/${job.requested_count} câu). Hãy sang Bước 2 hoặc Bước 3 để gom nhóm đăng lên kệ.`
          : `Đã khởi chạy Job #${job.job_id} (${job.requested_count} câu). Hệ thống AI đang sinh câu hỏi và tự giải kiểm chứng.`
      );
      await Promise.all([loadJobs(), loadDrafts(), loadBankQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tạo được tiến trình sinh đề AI'));
    } finally {
      setSubmittingJob(false);
    }
  };

  // Handlers — Step 1B: Manual Question Creation
  const handleCreateManualQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    setSavingManual(true);
    try {
      const created = await createManualAdminQuestion({
        title: manualTitle.trim(),
        question: manualQuestion.trim(),
        reference_sql: manualSql.trim(),
        difficulty: manualDiff,
        skill_ids: manualSkills.length ? manualSkills : [skillOptions[0]?.id ?? 1],
        compare_mode: manualCompareMode,
      });
      setLastManualQuestion(created);
      setMsg(
        `Đã kiểm tra trên Sandbox PostgreSQL 17 và lưu câu hỏi #${created.question_id} (${created.row_count} dòng kết quả) vào Kho Đề Đã Duyệt!`
      );
      setManualTitle('');
      setManualQuestion('');
      await loadBankQuestions();
    } catch (e: any) {
      setErr(
        extractApiError(
          e,
          'Câu lệnh SQL đáp án mẫu không chạy được hoặc trả về 0 dòng trên dữ liệu thực tế.'
        )
      );
    } finally {
      setSavingManual(false);
    }
  };

  // Handlers — Step 2: Single & Bulk Draft Review
  const filteredDrafts = draftStatusFilter
    ? drafts.filter((d) => d.status === draftStatusFilter)
    : drafts;

  const toggleDraftCheckbox = (draftId: number) => {
    setCheckedDraftIds((prev) =>
      prev.includes(draftId) ? prev.filter((x) => x !== draftId) : [...prev, draftId]
    );
  };

  const selectAllPendingDrafts = () => {
    const candidates = filteredDrafts
      .filter((d) => d.status === 'needs_human' || d.status === 'rejected')
      .map((d) => d.draft_id);
    const targetIds = candidates.length > 0 ? candidates : filteredDrafts.map((d) => d.draft_id);
    const allSelected =
      targetIds.length > 0 && targetIds.every((id) => checkedDraftIds.includes(id));
    if (allSelected) {
      setCheckedDraftIds([]);
    } else {
      setCheckedDraftIds(targetIds);
    }
  };

  const handleBulkApprove = async () => {
    const approvable = checkedDraftIds.filter((id) => {
      const found = drafts.find((d) => d.draft_id === id);
      return found && found.status !== 'approved';
    });
    if (approvable.length === 0) {
      setErr('Các đề bạn chọn đều đã được duyệt trước đó. Bạn có thể gộp thẳng vào Nhóm đề.');
      return;
    }
    setBulkBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await bulkApproveAdminDrafts(
        approvable,
        'Duyệt hàng loạt từ cổng Giảng viên'
      );
      setMsg(
        `Đã duyệt hàng loạt thành công ${res.approved_count ?? approvable.length} đề vào Kho Đề Đã Duyệt! Hãy sang Bước 3 để gom nhóm & đăng lên kệ.`
      );
      setCheckedDraftIds([]);
      await Promise.all([loadDrafts(), loadBankQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Duyệt hàng loạt không thành công'));
    } finally {
      setBulkBusy(false);
    }
  };

  const handleBulkApproveAndGroup = async () => {
    if (checkedDraftIds.length === 0) return;
    const unapprovedDraftIds: number[] = [];
    const alreadyPromotedQuestionIds: number[] = [];

    checkedDraftIds.forEach((did) => {
      const found = drafts.find((d) => d.draft_id === did);
      if (!found) return;
      const promotedQid = found.promoted_question_id || found.promoted_question?.question_id;
      if (found.status === 'approved' && promotedQid) {
        alreadyPromotedQuestionIds.push(Number(promotedQid));
      } else {
        unapprovedDraftIds.push(did);
      }
    });

    setBulkBusy(true);
    setErr(null);
    setMsg(null);
    try {
      let targetGid: number;
      if (bulkGroupTargetId === 'NEW') {
        const gName =
          bulkGroupNewName.trim() ||
          `Nhóm đề ngày ${new Date().toLocaleDateString('vi-VN')}`;
        const created = await createAdminQuestionGroup({
          name: gName,
          question_ids: alreadyPromotedQuestionIds,
          draft_ids: unapprovedDraftIds,
        });
        targetGid = created.group_id;
      } else {
        targetGid = Number(bulkGroupTargetId);
        await addAdminQuestionGroupItems(targetGid, {
          question_ids: alreadyPromotedQuestionIds,
          draft_ids: unapprovedDraftIds,
        });
      }
      setCheckedDraftIds([]);
      setShowBulkGroupPanel(false);
      setBulkGroupNewName('');
      await Promise.all([loadDrafts(), loadBankQuestions(), loadGroups(targetGid)]);
      setStep('step3_groups');
      setMsg(
        `Đã duyệt và đưa toàn bộ đề đã chọn vào Nhóm đề #${targetGid}. Bấm "Đăng toàn bộ lên kệ ngay" ở cột phải để hoàn tất!`
      );
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể duyệt & gộp vào nhóm đề'));
    } finally {
      setBulkBusy(false);
    }
  };

  const handleApproveSingleDraft = async () => {
    if (!selectedDraft) return;
    setMsg(null);
    setErr(null);
    try {
      const payload: { selected_run_id?: number; custom_sql?: string; note?: string } = {
        note: reviewNote || 'Giảng viên phê duyệt thủ công',
      };
      if (sqlSourceChoice === 'custom') {
        payload.custom_sql = customSqlText.trim();
      } else if (typeof sqlSourceChoice === 'number') {
        payload.selected_run_id = sqlSourceChoice;
      } else if (customSqlText.trim() && customSqlText.trim() !== (selectedDraft.reference_sql || '').trim()) {
        payload.custom_sql = customSqlText.trim();
      }
      const d = await approveAdminDraft(selectedDraft.draft_id, payload);
      setSelectedDraft(d);
      setMsg(
        `Đã phê duyệt bản nháp #${d.draft_id} vào Kho Đề Đã Duyệt. Bạn có thể đưa vào Nhóm đề ở Bước 3.`
      );
      await Promise.all([loadDrafts(), loadBankQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể phê duyệt bản nháp này. Kiểm tra lại câu SQL đáp án.'));
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
        note: reviewNote || 'Chỉnh sửa nội dung câu hỏi',
      });
      setSelectedDraft(d);
      setMsg(`Đã lưu nội dung chỉnh sửa bản nháp #${d.draft_id}.`);
      loadDrafts();
    } catch (e: any) {
      setErr(extractApiError(e, 'Lưu bản nháp không thành công'));
    }
  };

  const handleRejectDraft = async () => {
    if (!selectedDraft) return;
    setMsg(null);
    setErr(null);
    try {
      const d = await rejectAdminDraft(
        selectedDraft.draft_id,
        reviewNote || 'Chưa đạt yêu cầu chuyên môn'
      );
      setSelectedDraft(d);
      setMsg(`Đã đánh dấu từ chối bản nháp #${d.draft_id}.`);
      loadDrafts();
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể từ chối bản nháp'));
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
      setMsg(`Đã đưa bản nháp #${d.draft_id} vào hàng đợi kiểm định lại.`);
      loadDrafts();
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể kiểm định lại bản nháp'));
    }
  };

  // Handlers — Step 3: Question Groups (Drag & Pick Composer + 1-Click Publish)
  const draftGroups = groups.filter((g) => g.status === 'draft');
  const groupItems = (groupDetail?.items || []).map(normalizeGroupItem);
  const groupItemIdSet = new Set(groupItems.map((it: any) => it.question_id));
  const isSelectedGroupEditable = groupDetail?.status === 'draft';

  const ensureEditableGroupId = async (seedQuestionIds?: number[]): Promise<number | null> => {
    if (selectedGroupId && groupDetail?.status === 'draft') {
      return selectedGroupId;
    }
    const existingDraft = groups.find((g) => g.status === 'draft');
    if (existingDraft) {
      setSelectedGroupId(existingDraft.group_id);
      return existingDraft.group_id;
    }
    const autoName =
      newGroupName.trim() || `Nhóm đề mới (${new Date().toLocaleDateString('vi-VN')})`;
    const created = await createAdminQuestionGroup({
      name: autoName,
      question_ids: seedQuestionIds || [],
    });
    setNewGroupName('');
    await loadGroups(created.group_id);
    return created.group_id;
  };

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = newGroupName.trim();
    if (!cleanName) {
      setErr('Vui lòng nhập tên nhóm đề trước khi tạo.');
      return;
    }
    setCreatingGroup(true);
    setErr(null);
    setMsg(null);
    try {
      const created = await createAdminQuestionGroup({
        name: cleanName,
        question_ids: pickedBankIds.length > 0 ? pickedBankIds : [],
      });
      setNewGroupName('');
      setPublishSetTitle(cleanName);
      if (pickedBankIds.length > 0) {
        setPickedBankIds([]);
      }
      await Promise.all([loadGroups(created.group_id), loadBankQuestions()]);
      setMsg(
        created.question_count > 0
          ? `Đã tạo nhóm "${created.name}" kèm ${created.question_count} câu hỏi đã chọn!`
          : `Đã tạo nhóm "${created.name}". Hãy kéo thả hoặc bấm "+ Thêm" ở cột trái để đưa đề vào nhóm.`
      );
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể tạo nhóm đề mới'));
    } finally {
      setCreatingGroup(false);
    }
  };

  const handleAddQuestionsToGroup = async (questionIds: number[]) => {
    if (!questionIds.length) return;
    setGroupBusy(true);
    setErr(null);
    setMsg(null);
    try {
      if (!selectedGroupId || groupDetail?.status !== 'draft') {
        const existingDraft = groups.find((g) => g.status === 'draft');
        if (!existingDraft) {
          const autoName =
            newGroupName.trim() || `Nhóm đề thực hành (${new Date().toLocaleDateString('vi-VN')})`;
          const created = await createAdminQuestionGroup({
            name: autoName,
            question_ids: questionIds,
          });
          setNewGroupName('');
          setPickedBankIds((prev) => prev.filter((id) => !questionIds.includes(id)));
          await Promise.all([loadGroups(created.group_id), loadBankQuestions()]);
          setMsg(`Đã tự tạo nhóm "${created.name}" và thêm ${questionIds.length} câu hỏi!`);
          return;
        }
      }
      const gid = await ensureEditableGroupId();
      if (!gid) return;
      const updated = await addAdminQuestionGroupItems(gid, { question_ids: questionIds });
      setGroupDetail(updated);
      setPickedBankIds((prev) => prev.filter((id) => !questionIds.includes(id)));
      await Promise.all([loadGroups(gid), loadBankQuestions()]);
      setMsg(`Đã thêm ${questionIds.length} câu hỏi vào nhóm "${updated.name}".`);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể thêm câu hỏi vào nhóm'));
    } finally {
      setGroupBusy(false);
    }
  };

  const handleReorderGroupItems = async (nextIds: number[]) => {
    if (!selectedGroupId || !isSelectedGroupEditable) return;
    setGroupBusy(true);
    setErr(null);
    try {
      const updated = await updateAdminQuestionGroupItems(selectedGroupId, nextIds);
      setGroupDetail(updated);
      await Promise.all([loadGroups(selectedGroupId), loadBankQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Cập nhật danh sách câu trong nhóm không thành công'));
    } finally {
      setGroupBusy(false);
    }
  };

  const moveGroupItem = (idx: number, direction: -1 | 1) => {
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= groupItems.length) return;
    const ids = groupItems.map((it: any) => it.question_id);
    const swapped = [...ids];
    const tmp = swapped[idx];
    swapped[idx] = swapped[targetIdx];
    swapped[targetIdx] = tmp;
    handleReorderGroupItems(swapped);
  };

  const removeGroupItem = (qid: number) => {
    const nextIds = groupItems
      .map((it: any) => it.question_id)
      .filter((id: number) => id !== qid);
    handleReorderGroupItems(nextIds);
  };

  const handleDeleteGroup = async () => {
    if (!selectedGroupId || !isSelectedGroupEditable) return;
    setGroupBusy(true);
    setErr(null);
    setMsg(null);
    try {
      await deleteAdminQuestionGroup(selectedGroupId);
      setMsg('Đã xoá nhóm đề nháp.');
      setSelectedGroupId(null);
      setGroupDetail(null);
      await Promise.all([loadGroups(), loadBankQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể xoá nhóm đề này'));
    } finally {
      setGroupBusy(false);
    }
  };

  const handlePublishGroup = async () => {
    if (!selectedGroupId || groupItems.length === 0) return;
    setGroupBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await publishAdminQuestionGroup(selectedGroupId, {
        mode: publishMode,
        set_title: publishSetTitle.trim() || groupDetail?.name || undefined,
      });
      setLastPublishReceipt(res);
      setMsg(
        `Thành công! Đã đăng toàn bộ ${res.published_count ?? groupItems.length} câu hỏi lên kệ "${res.set_title || 'Bộ đề hiện hành'}". Sinh viên đã có thể vào làm bài ngay!`
      );
      await Promise.all([loadGroups(selectedGroupId), loadBankQuestions(), loadWeekly()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Đăng nhóm đề lên kệ không thành công'));
    } finally {
      setGroupBusy(false);
    }
  };

  const toggleQuestionPreview = async (questionId: number) => {
    if (previewQuestionId === questionId) {
      setPreviewQuestionId(null);
      return;
    }
    setPreviewQuestionId(questionId);
    if (!previewCache[questionId]) {
      try {
        const detail = await getAdminQuestionDetail(questionId);
        setPreviewCache((prev) => ({ ...prev, [questionId]: detail }));
      } catch {}
    }
  };

  // Handlers — Step 4: Weekly Sets, Users & Settings
  const handleCreateWeeklySet = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    try {
      const w = await createAdminWeeklySet({
        title: newWeekTitle.trim() || 'Bộ đề tuần SQL',
        week_start: newWeekStart,
      });
      setMsg(`Đã khởi tạo bộ đề tuần #${w.set_id} (${w.title}).`);
      await loadWeekly();
      inspectWeeklySet(w.set_id);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tạo được bộ đề tuần (kiểm tra ngày bắt đầu trùng chu kỳ)'));
    }
  };

  const handleRemoveFromWeeklySet = async (setId: number, removeQid: number) => {
    const items = weeklySetDetail?.items || [];
    const nextIds = items
      .map((it: any) => Number(it?.question?.question_id ?? it?.question_id))
      .filter((id: number) => id !== removeQid);
    try {
      await updateAdminWeeklySetItems(setId, nextIds);
      setMsg(`Đã gỡ câu hỏi #${removeQid} khỏi bộ đề tuần nháp #${setId}.`);
      await inspectWeeklySet(setId);
    } catch (e: any) {
      setErr(extractApiError(e, 'Chỉ bộ đề đang ở trạng thái Nháp (draft) mới chỉnh sửa được danh sách câu'));
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
      setErr(extractApiError(e, 'Cập nhật cấu hình không thành công'));
    }
  };

  const handleToggleUser = async (u: any, field: 'role' | 'status') => {
    try {
      const payload =
        field === 'role'
          ? { role: (u.role === 'admin' ? 'learner' : 'admin') as 'learner' | 'admin' }
          : { status: (u.status === 'active' ? 'locked' : 'active') as 'active' | 'locked' };
      await updateAdminUser(u.user_id, payload);
      setMsg(`Đã cập nhật tài khoản @${u.username}.`);
      loadUsers();
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể cập nhật tài khoản'));
    }
  };

  const pendingDraftCount = drafts.filter((d) => d.status === 'needs_human').length;

  return (
    <div className="space-y-5">
      {/* 4-Step Visual Stepper Header */}
      <div className="bg-surface border border-line rounded-2xl p-4 sm:p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-ink">
              Trung tâm Ra đề, Gom nhóm &amp; Phát hành Bài tập
            </h1>
            <p className="text-sm text-text2 mt-0.5">
              Quy trình 4 bước rõ ràng: Soạn đề mới, duyệt hàng loạt, kéo hoặc chọn nhiều đề vào một nhóm rồi đăng toàn bộ lên kệ trong 1 lần bấm.
            </p>
          </div>
          {onJumpToWorkbench && (
            <button
              type="button"
              onClick={onJumpToWorkbench}
              className="btn-secondary px-3.5 min-h-10 rounded-lg text-sm font-semibold"
            >
              Xem giao diện Làm bài của Sinh viên
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2.5">
          {[
            {
              id: 'step1_create',
              stepNum: 'Bước 1',
              title: 'Tạo đề mới',
              desc: 'AI tự sinh hoặc tự soạn thủ công',
              icon: Sparkles,
              badge: null,
            },
            {
              id: 'step2_drafts',
              stepNum: 'Bước 2',
              title: 'Kiểm duyệt đề nháp',
              desc: 'Duyệt hàng loạt & sửa SQL đáp án',
              icon: CheckCircle2,
              badge: pendingDraftCount > 0 ? `${pendingDraftCount} chờ duyệt` : `${drafts.length} nháp`,
            },
            {
              id: 'step3_groups',
              stepNum: 'Bước 3 (Trọng tâm)',
              title: 'Gom nhóm & Đăng 1 lần',
              desc: 'Kéo thả / Pick nhiều đề đăng cùng lúc',
              icon: Layers,
              badge: `${groups.length} nhóm`,
            },
            {
              id: 'step4_system',
              stepNum: 'Bước 4',
              title: 'Kệ đề tuần & Hệ thống',
              desc: 'Xem chi tiết bộ đề, kho đề & tài khoản',
              icon: CalendarRange,
              badge: null,
            },
          ].map((item) => {
            const Icon = item.icon;
            const active = step === item.id;
            return (
              <button
                key={item.id}
                type="button"
                data-solid-btn={active ? 'true' : undefined}
                onClick={() => setStep(item.id as any)}
                className={`p-3.5 rounded-xl text-left flex flex-col justify-between gap-2 min-h-20 ${
                  active ? 'btn-primary' : 'btn-subtle'
                }`}
              >
                <div className="flex items-center justify-between gap-2 w-full">
                  <span
                    className={`text-xs font-semibold flex items-center gap-1.5 ${
                      active ? 'text-on-brand' : 'text-brand'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.stepNum}</span>
                  </span>
                  {item.badge && (
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-semibold tabular-nums ${
                        active ? 'bg-surface text-ink' : 'badge-info'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
                <div>
                  <div className={`text-sm font-bold ${active ? 'text-on-brand' : 'text-ink'}`}>
                    {item.title}
                  </div>
                  <div className={`text-xs mt-0.5 ${active ? 'text-on-brand opacity-90' : 'text-muted'}`}>
                    {item.desc}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Feedback Banners */}
      {(err || msg) && (
        <div role="status" className="space-y-2">
          {err && (
            <div className="p-4 rounded-xl badge-hard text-base flex items-center justify-between gap-3">
              <p>{err}</p>
              <button
                type="button"
                onClick={() => setErr(null)}
                className="btn-secondary px-3 min-h-9 rounded-md text-sm font-semibold shrink-0"
              >
                Đóng
              </button>
            </div>
          )}
          {msg && (
            <div className="p-4 rounded-xl badge-easy text-base flex flex-wrap items-center justify-between gap-3">
              <p>{msg}</p>
              <div className="flex items-center gap-2 shrink-0">
                {onJumpToWorkbench && lastPublishReceipt && (
                  <button
                    type="button"
                    data-solid-btn="true"
                    onClick={onJumpToWorkbench}
                    className="btn-primary px-3.5 min-h-9 rounded-md text-sm font-semibold whitespace-nowrap"
                  >
                    Mở màn hình Làm bài
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setMsg(null)}
                  className="btn-secondary px-3 min-h-9 rounded-md text-sm font-semibold"
                >
                  Đóng
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          STEP 1: CREATE QUESTIONS (AI PIPELINE + MANUAL AUTHORING)
      ===================================================================== */}
      {step === 'step1_create' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-surface border border-line rounded-xl p-3">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                data-solid-btn={step1Mode === 'ai' ? 'true' : undefined}
                onClick={() => setStep1Mode('ai')}
                className={`px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-2 ${
                  step1Mode === 'ai' ? 'btn-primary' : 'btn-secondary'
                }`}
              >
                <Sparkles className="w-4 h-4" />
                <span>AI tự động sinh đề (2-Model)</span>
              </button>
              <button
                type="button"
                data-solid-btn={step1Mode === 'manual' ? 'true' : undefined}
                onClick={() => setStep1Mode('manual')}
                className={`px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-2 ${
                  step1Mode === 'manual' ? 'btn-primary' : 'btn-secondary'
                }`}
              >
                <FilePlus2 className="w-4 h-4" />
                <span>Tự soạn đề thủ công (Lưu thẳng vào Kho Đề)</span>
              </button>
            </div>
            <button
              type="button"
              onClick={() => setStep('step3_groups')}
              className="btn-subtle px-3.5 min-h-10 rounded-lg text-sm font-medium flex items-center gap-1.5"
            >
              <span>Đi tới Bước 3: Gom nhóm &amp; Đăng kệ</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {step1Mode === 'ai' ? (
            <div className="space-y-4">
              <div className="bg-surface border border-line rounded-xl p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-bold text-ink">
                        Cổng AI Gateway (apithat.dev/keys)
                      </span>
                      {gatewayStatus?.valid ? (
                        <span className="badge-easy px-2.5 py-0.5 rounded-full text-xs font-semibold">
                          Đã kết nối ({gatewayStatus.masked_key}) · {gatewayStatus.preferred_model}
                        </span>
                      ) : (
                        <span className="badge-medium px-2.5 py-0.5 rounded-full text-xs font-semibold">
                          {gatewayStatus?.configured
                            ? `Cần cập nhật khóa mới (${gatewayStatus.masked_key || '401'})`
                            : 'Chưa gắn khóa apithat.dev (đang dùng Local Ollama)'}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-text2">
                      Lấy khóa tại{' '}
                      <a
                        href="https://apithat.dev/keys"
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold underline text-ink"
                      >
                        https://apithat.dev/keys
                      </a>{' '}
                      rồi lưu trực tiếp vào két bảo mật máy chủ (không lộ khóa qua hội thoại).
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowGatewayForm((v) => !v)}
                    className="btn-secondary px-3.5 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap"
                  >
                    {showGatewayForm ? 'Ẩn khung nhập khóa' : 'Cập nhật khóa API Thật'}
                  </button>
                </div>

                {(showGatewayForm || (gatewayStatus && !gatewayStatus.valid)) && (
                  <form
                    onSubmit={handleSaveGatewayKey}
                    className="pt-3 border-t border-line grid grid-cols-1 md:grid-cols-12 gap-3 items-end"
                  >
                    <div className="md:col-span-6">
                      <label className="block text-sm font-medium text-ink mb-1">
                        Khóa API từ apithat.dev/keys (ẩn ký tự)
                      </label>
                      <input
                        type="password"
                        autoComplete="off"
                        value={gatewayKeyInput}
                        onChange={(e) => setGatewayKeyInput(e.target.value)}
                        placeholder="sk-..."
                        className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink font-mono"
                      />
                    </div>
                    <div className="md:col-span-3">
                      <label className="block text-sm font-medium text-ink mb-1">
                        Model ưu tiên
                      </label>
                      <select
                        value={gatewayModelInput}
                        onChange={(e) => setGatewayModelInput(e.target.value)}
                        className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                      >
                        {(gatewayStatus?.available_models?.length
                          ? gatewayStatus.available_models
                          : gatewayStatus?.rotation_pool || [
                              'gpt-5.6-sol',
                              'gpt-6.1-terra',
                              'gpt-6-sol',
                              'gpt-6-astra',
                              'claude-sonnet-5-5',
                            ]
                        ).map((m: string) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="md:col-span-3">
                      <button
                        type="submit"
                        data-solid-btn="true"
                        disabled={savingGatewayKey}
                        className="btn-primary w-full px-4 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap"
                      >
                        {savingGatewayKey ? 'Đang xác thực…' : 'Xác thực & Kích hoạt'}
                      </button>
                    </div>
                  </form>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              <form
                onSubmit={handleCreateJob}
                className="lg:col-span-5 bg-surface border border-line rounded-xl p-5 space-y-4"
              >
                <div className="border-b border-line pb-3 space-y-1">
                  <h2 className="text-base font-bold text-ink">
                    Sinh câu hỏi tự động bằng AI
                  </h2>
                  <p className="text-sm text-text2 leading-relaxed">
                    Model A soạn đề bài tiếng Việt &amp; đáp án SQL từ 13 bảng thực tế, sau đó Model B giải độc lập để kiểm chứng kết quả.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">
                    Chủ đề nghiệp vụ mong muốn
                  </label>
                  <input
                    value={jobTopic}
                    onChange={(e) => setJobTopic(e.target.value)}
                    placeholder="Nhập chủ đề hoặc bấm chọn gợi ý bên dưới..."
                    className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink placeholder:text-muted"
                  />
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {TOPIC_PRESETS.map((preset) => {
                      const selected = jobTopic === preset;
                      return (
                        <button
                          type="button"
                          key={preset}
                          data-solid-btn={selected ? 'true' : undefined}
                          onClick={() => setJobTopic(preset)}
                          className={`px-2.5 py-1.5 rounded-lg text-xs text-left font-medium ${
                            selected ? 'btn-primary' : 'btn-secondary'
                          }`}
                        >
                          {preset}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">
                    Kỹ năng SQL trọng tâm
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {skillOptions.map((sk) => {
                      const active = jobSkills.includes(sk.id);
                      return (
                        <button
                          type="button"
                          key={sk.id}
                          data-solid-btn={active ? 'true' : undefined}
                          onClick={() =>
                            setJobSkills((prev) =>
                              prev.includes(sk.id)
                                ? prev.filter((x) => x !== sk.id)
                                : [...prev, sk.id]
                            )
                          }
                          className={`px-3 min-h-10 rounded-lg text-left text-sm font-medium ${
                            active ? 'btn-primary' : 'btn-secondary'
                          }`}
                        >
                          {sk.code}: {sk.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-semibold text-ink mb-1">
                      Độ khó
                    </label>
                    <select
                      value={jobDiff}
                      onChange={(e) => setJobDiff(Number(e.target.value))}
                      className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                    >
                      <option value={1}>Mức 1: Dễ (Cơ bản)</option>
                      <option value={2}>Mức 2: Trung bình</option>
                      <option value={3}>Mức 3: Khó (Nâng cao)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-ink mb-1">
                      Số lượng câu cần sinh (1-10)
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={jobCount}
                      onChange={(e) => setJobCount(Number(e.target.value))}
                      className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink tabular-nums"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={isGenerating}
                  className="btn-primary w-full min-h-11 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-60"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>
                        {activeRunningJob
                          ? `Đang sinh đề Job #${activeRunningJob.job_id} (${activeRunningJob.created_count}/${activeRunningJob.requested_count} câu, ${elapsedSec}s)`
                          : 'Đang khởi tạo tiến trình AI...'}
                      </span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Bắt đầu sinh đề bằng AI</span>
                    </>
                  )}
                </button>
              </form>

              {/* Right Column: Job History */}
              <div className="lg:col-span-7 bg-surface border border-line rounded-xl overflow-hidden">
                <div className="px-5 py-3.5 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-base font-bold text-ink">
                    Lịch sử các đợt sinh đề AI
                  </h3>
                  <div className="flex items-center gap-2">
                    {llmUsage && (
                      <span className="text-xs text-muted tabular-nums">
                        Hạn mức hôm nay: {llmUsage.used_today ?? llmUsage.calls_used ?? 0}/
                        {llmUsage.daily_cap ?? llmUsage.daily_call_cap ?? 200} lượt gọi
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() =>
                        runAdminWorker()
                          .then((res) => {
                            setMsg(`Đã chạy hàng đợi xử lý (${res?.processed_jobs ?? 0} job).`);
                            loadJobs();
                            loadDrafts();
                          })
                          .catch((e) => setErr(extractApiError(e, 'Không chạy được worker')))
                      }
                      className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold"
                    >
                      Chạy hàng đợi ngay
                    </button>
                  </div>
                </div>

                <div className="divide-y divide-line max-h-[520px] overflow-y-auto">
                  {jobs.length === 0 ? (
                    <div className="p-8 text-center text-sm text-muted">
                      Chưa có đợt sinh đề AI nào. Hãy bấm nút sinh đề ở khung bên trái hoặc chuyển sang tab Tự soạn đề thủ công.
                    </div>
                  ) : (
                    jobs.map((j) => {
                      const jobDrafts =
                        Array.isArray(j.drafts) && j.drafts.length > 0
                          ? j.drafts
                          : drafts.filter((d: any) => d.job_id === j.job_id);
                      return (
                        <div key={j.job_id} className="p-4 space-y-2.5 text-sm">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <div className="font-semibold text-ink">
                                Đợt #{j.job_id}: {j.topic || 'Sinh câu hỏi SQL'}
                              </div>
                              <div className="text-xs text-muted mt-0.5 tabular-nums">
                                Mức độ: {DIFF_LABELS[j.difficulty]?.text || `Mức ${j.difficulty}`} | Tiến độ:{' '}
                                {j.created_count}/{j.requested_count} câu | Lúc: {formatVnDateTime(j.created_at)}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                                  j.status === 'done'
                                    ? 'badge-easy'
                                    : j.status === 'failed'
                                    ? 'badge-hard'
                                    : 'badge-info'
                                }`}
                              >
                                {j.status === 'done'
                                  ? 'Hoàn tất'
                                  : j.status === 'failed'
                                  ? 'Lỗi'
                                  : 'Đang chạy'}
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  setStep('step2_drafts');
                                  if (jobDrafts[0]?.draft_id) {
                                    inspectDraft(jobDrafts[0].draft_id);
                                  }
                                }}
                                className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold"
                              >
                                Kiểm duyệt ở Bước 2
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
              </div>
            </div>
          ) : (
            /* Step 1B: Manual Question Composer */
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              <form
                onSubmit={handleCreateManualQuestion}
                className="lg:col-span-8 bg-surface border border-line rounded-xl p-5 space-y-4"
              >
                <div className="border-b border-line pb-3">
                  <h2 className="text-base font-bold text-ink">
                    Tự soạn đề bài &amp; câu lệnh SQL đáp án mẫu
                  </h2>
                  <p className="text-sm text-text2 mt-0.5">
                    Hệ thống sẽ tự động chạy thử câu SQL đáp án trên PostgreSQL 17 Sandbox, trích xuất bộ Test Cases chuẩn và đưa thẳng vào Kho Đề Đã Duyệt.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1">
                    Tiêu đề câu hỏi
                  </label>
                  <input
                    required
                    value={manualTitle}
                    onChange={(e) => setManualTitle(e.target.value)}
                    placeholder="Ví dụ: Thống kê số lượng nhân viên đang làm việc tại từng phòng ban"
                    className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1">
                    Nội dung đề bài chi tiết (hiển thị cho sinh viên)
                  </label>
                  <textarea
                    required
                    rows={4}
                    value={manualQuestion}
                    onChange={(e) => setManualQuestion(e.target.value)}
                    placeholder="Mô tả rõ yêu cầu lọc dữ liệu, các cột kết quả cần trả về và thứ tự sắp xếp (nếu có)..."
                    className="w-full p-3.5 rounded-lg bg-canvas border border-line text-sm text-ink leading-relaxed"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-semibold text-ink mb-1">
                      Độ khó
                    </label>
                    <select
                      value={manualDiff}
                      onChange={(e) => setManualDiff(Number(e.target.value))}
                      className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                    >
                      <option value={1}>Mức 1: Dễ</option>
                      <option value={2}>Mức 2: Trung bình</option>
                      <option value={3}>Mức 3: Khó</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-ink mb-1">
                      Chế độ chấm thứ tự dòng
                    </label>
                    <select
                      value={manualCompareMode}
                      onChange={(e) => setManualCompareMode(e.target.value as any)}
                      className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                    >
                      <option value="unordered">Không bắt buộc thứ tự dòng (unordered)</option>
                      <option value="ordered">Bắt buộc đúng thứ tự ORDER BY (ordered)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">
                    Nhóm kỹ năng gắn kèm
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {skillOptions.map((sk) => {
                      const active = manualSkills.includes(sk.id);
                      return (
                        <button
                          type="button"
                          key={sk.id}
                          data-solid-btn={active ? 'true' : undefined}
                          onClick={() =>
                            setManualSkills((prev) =>
                              prev.includes(sk.id)
                                ? prev.filter((x) => x !== sk.id)
                                : [...prev, sk.id]
                            )
                          }
                          className={`px-3 min-h-9 rounded-lg text-xs font-semibold ${
                            active ? 'btn-primary' : 'btn-secondary'
                          }`}
                        >
                          {sk.code}: {sk.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1">
                    Câu lệnh SQL đáp án mẫu (phải trả về ít nhất 1 dòng dữ liệu)
                  </label>
                  <textarea
                    required
                    rows={5}
                    value={manualSql}
                    onChange={(e) => setManualSql(e.target.value)}
                    className="w-full p-3.5 rounded-lg bg-canvas border border-line font-mono text-sm text-ink leading-relaxed"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-1">
                  <button
                    type="submit"
                    data-solid-btn="true"
                    disabled={savingManual}
                    className="btn-primary px-6 min-h-11 rounded-xl text-sm font-semibold disabled:opacity-50"
                  >
                    {savingManual
                      ? 'Đang chạy kiểm tra trên Sandbox...'
                      : 'Kiểm tra trên Sandbox & Lưu vào Kho Đề'}
                  </button>

                  {lastManualQuestion && (
                    <button
                      type="button"
                      data-solid-btn="true"
                      onClick={() => {
                        setPickedBankIds((prev) =>
                          prev.includes(lastManualQuestion.question_id)
                            ? prev
                            : [...prev, lastManualQuestion.question_id]
                        );
                        setStep('step3_groups');
                      }}
                      className="btn-blue px-4 min-h-11 rounded-xl text-sm font-semibold flex items-center gap-2"
                    >
                      <span>Đưa câu #{lastManualQuestion.question_id} sang Bước 3 để đăng kệ</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </form>

              {/* Quick Schema Reference for Manual Authoring */}
              <div className="lg:col-span-4 bg-surface border border-line rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2 border-b border-line pb-2.5">
                  <Database className="w-4 h-4 text-brand" />
                  <h3 className="text-sm font-bold text-ink">
                    Tra cứu nhanh 13 bảng dữ liệu
                  </h3>
                </div>
                <p className="text-xs text-muted">
                  Bấm vào tên bảng để chèn nhanh câu mẫu <code className="text-ink">SELECT</code> vào ô đáp án.
                </p>
                <div className="space-y-2 max-h-[540px] overflow-y-auto pr-1">
                  {schemaTables.map((tb: any) => (
                    <div
                      key={tb.name}
                      className="p-2.5 rounded-lg bg-canvas border border-line space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <code className="text-xs font-bold text-brand">{tb.name}</code>
                        <button
                          type="button"
                          onClick={() =>
                            setManualSql(
                              `SELECT ${(tb.columns || [])
                                .slice(0, 3)
                                .map((c: any) => c.name)
                                .join(', ')}\nFROM ${tb.name}\nLIMIT 20;`
                            )
                          }
                          className="btn-secondary px-2 min-h-7 rounded text-xs font-medium"
                        >
                          Dùng bảng này
                        </button>
                      </div>
                      <div className="text-xs text-muted leading-relaxed">
                        {(tb.columns || []).map((c: any) => c.name).join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          STEP 2: DRAFT REVIEW, BULK APPROVE & DIRECT GROUPING
      ===================================================================== */}
      {step === 'step2_drafts' && (
        <div className="space-y-4">
          {/* Approval Mode Quick Switch Bar */}
          <div className="p-4 rounded-xl bg-surface border border-line flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="text-sm font-bold text-ink">
                Chế độ tự động kiểm duyệt AI (review.approval_mode)
              </div>
              <div className="text-xs text-muted">
                Chế độ Thông minh bỏ qua các khác biệt tên cột phụ vô hại nhưng vẫn bắt buộc kết quả chạy SQL chính xác tuyệt đối.
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-1.5 bg-soft p-1 rounded-lg border border-line">
              <button
                type="button"
                disabled={savingApprovalMode}
                data-solid-btn={approvalMode === 'calibrated' ? 'true' : undefined}
                onClick={() => handleSwitchApprovalMode('calibrated')}
                className={`px-3.5 min-h-9 rounded-md text-xs font-semibold ${
                  approvalMode === 'calibrated' ? 'btn-primary' : 'text-text2 hover:text-ink'
                }`}
              >
                Thông minh / Nới lỏng hợp lý (Khuyên dùng)
              </button>
              <button
                type="button"
                disabled={savingApprovalMode}
                data-solid-btn={approvalMode === 'strict' ? 'true' : undefined}
                onClick={() => handleSwitchApprovalMode('strict')}
                className={`px-3.5 min-h-9 rounded-md text-xs font-semibold ${
                  approvalMode === 'strict' ? 'btn-primary' : 'text-text2 hover:text-ink'
                }`}
              >
                Khắt khe tuyệt đối
              </button>
            </div>
          </div>

          {/* Floating Bulk Action Bar when Drafts are Checked */}
          {checkedDraftIds.length > 0 && (
            <div className="p-4 rounded-xl bg-surface border-2 border-brand space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm font-bold text-ink tabular-nums">
                  Đã chọn {checkedDraftIds.length} đề nháp
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    data-solid-btn="true"
                    disabled={bulkBusy}
                    onClick={handleBulkApprove}
                    className="btn-primary px-4 min-h-10 rounded-lg text-sm font-semibold disabled:opacity-50"
                  >
                    {bulkBusy
                      ? 'Đang xử lý...'
                      : `Duyệt hàng loạt (${checkedDraftIds.length} đề)`}
                  </button>
                  <button
                    type="button"
                    data-solid-btn="true"
                    disabled={bulkBusy}
                    onClick={() => setShowBulkGroupPanel((v) => !v)}
                    className="btn-blue px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <FolderPlus className="w-4 h-4" />
                    <span>Duyệt &amp; Gộp thẳng vào Nhóm đề...</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCheckedDraftIds([]);
                      setShowBulkGroupPanel(false);
                    }}
                    className="btn-secondary px-3 min-h-10 rounded-lg text-sm font-medium"
                  >
                    Bỏ chọn
                  </button>
                </div>
              </div>

              {showBulkGroupPanel && (
                <div className="p-3.5 rounded-xl bg-soft border border-line flex flex-wrap items-end gap-3">
                  <div className="min-w-[220px]">
                    <label className="block text-xs font-semibold text-ink mb-1">
                      Chọn nhóm đích
                    </label>
                    <select
                      value={bulkGroupTargetId}
                      onChange={(e) => setBulkGroupTargetId(e.target.value)}
                      className="w-full px-3 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                    >
                      <option value="NEW">+ Tạo một nhóm đề mới</option>
                      {draftGroups.map((g) => (
                        <option key={g.group_id} value={String(g.group_id)}>
                          Nhóm #{g.group_id}: {g.name} ({g.question_count} câu)
                        </option>
                      ))}
                    </select>
                  </div>

                  {bulkGroupTargetId === 'NEW' && (
                    <div className="flex-1 min-w-[240px]">
                      <label className="block text-xs font-semibold text-ink mb-1">
                        Tên nhóm đề mới
                      </label>
                      <input
                        value={bulkGroupNewName}
                        onChange={(e) => setBulkGroupNewName(e.target.value)}
                        placeholder="Ví dụ: Nhóm bài tập tuần này"
                        className="w-full px-3.5 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                      />
                    </div>
                  )}

                  <button
                    type="button"
                    data-solid-btn="true"
                    disabled={bulkBusy}
                    onClick={handleBulkApproveAndGroup}
                    className="btn-primary px-5 min-h-10 rounded-lg text-sm font-semibold"
                  >
                    Xác nhận duyệt &amp; chuyển sang Bước 3
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left Draft List */}
            <div className="lg:col-span-5 bg-surface border border-line rounded-xl overflow-hidden">
              <div className="p-4 bg-soft border-b border-line space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-bold text-ink tabular-nums">
                    Danh sách bản nháp ({filteredDrafts.length})
                  </span>
                  <button
                    type="button"
                    onClick={selectAllPendingDrafts}
                    className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold"
                  >
                    Chọn tất cả đề chờ duyệt
                  </button>
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
                      label: `Đã duyệt (${drafts.filter((d) => d.status === 'approved').length})`,
                    },
                    {
                      val: 'rejected',
                      label: `Đã từ chối (${drafts.filter((d) => d.status === 'rejected').length})`,
                    },
                  ].map((pill) => {
                    const active = draftStatusFilter === pill.val;
                    return (
                      <button
                        key={pill.val || 'all'}
                        type="button"
                        data-solid-btn={active ? 'true' : undefined}
                        onClick={() => setDraftStatusFilter(pill.val)}
                        className={`px-3 min-h-8 rounded-lg text-xs font-semibold ${
                          active ? 'btn-primary' : 'btn-secondary'
                        }`}
                      >
                        {pill.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="divide-y divide-line max-h-[680px] overflow-y-auto">
                {filteredDrafts.length === 0 ? (
                  <div className="p-8 text-center text-sm text-muted">
                    Không có bản nháp nào trong mục này.
                  </div>
                ) : (
                  filteredDrafts.map((d) => {
                    const active = selectedDraft?.draft_id === d.draft_id;
                    const checked = checkedDraftIds.includes(d.draft_id);
                    const statusBadge =
                      d.status === 'approved'
                        ? 'badge-easy'
                        : d.status === 'needs_human'
                        ? 'badge-medium'
                        : d.status === 'rejected'
                        ? 'badge-hard'
                        : 'badge-neutral';
                    const statusText =
                      d.status === 'approved'
                        ? 'Đã duyệt'
                        : d.status === 'needs_human'
                        ? 'Chờ duyệt tay'
                        : d.status === 'rejected'
                        ? 'Đã từ chối'
                        : d.status;
                    return (
                      <div
                        key={d.draft_id}
                        onClick={() => inspectDraft(d.draft_id)}
                        className={`p-3.5 cursor-pointer flex items-start gap-3 transition-colors ${
                          active ? 'bg-soft' : 'hover:bg-canvas'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleDraftCheckbox(d.draft_id)}
                          onClick={(e) => e.stopPropagation()}
                          aria-label={`Chọn bản nháp #${d.draft_id}`}
                          className="mt-1 w-4 h-4 accent-[var(--green)] cursor-pointer shrink-0"
                        />
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-muted tabular-nums">
                              Nháp #{d.draft_id} | {DIFF_LABELS[d.difficulty]?.text || `Mức ${d.difficulty}`}
                            </span>
                            <span className={`px-2 py-0.5 rounded-md text-xs font-semibold ${statusBadge}`}>
                              {statusText}
                            </span>
                          </div>
                          <div className="text-sm font-semibold text-ink line-clamp-2">
                            {d.title}
                          </div>
                          {d.status_reason && (
                            <div className="text-xs text-muted line-clamp-1">
                              Lý do: {d.status_reason}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Draft Detail & Custom SQL Editor */}
            <div className="lg:col-span-7 bg-surface border border-line rounded-xl overflow-hidden">
              {selectedDraft ? (
                <div className="divide-y divide-line">
                  <div className="px-5 py-4 bg-soft flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-xs text-muted tabular-nums">
                        Chi tiết bản nháp #{selectedDraft.draft_id}
                      </div>
                      <div className="text-base font-bold text-ink">
                        Kiểm tra nội dung đề &amp; chọn câu SQL đáp án chuẩn
                      </div>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-md text-xs font-semibold ${
                        selectedDraft.status === 'approved'
                          ? 'badge-easy'
                          : selectedDraft.status === 'rejected'
                          ? 'badge-hard'
                          : 'badge-medium'
                      }`}
                    >
                      Trạng thái: {selectedDraft.status}
                    </span>
                  </div>

                  <div className="p-5 space-y-4">
                    <div>
                      <label className="block text-sm font-semibold text-ink mb-1">
                        Tiêu đề câu hỏi
                      </label>
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-ink mb-1">
                        Nội dung đề bài tiếng Việt
                      </label>
                      <textarea
                        rows={3}
                        value={editQuestion}
                        onChange={(e) => setEditQuestion(e.target.value)}
                        className="w-full p-3.5 rounded-lg bg-canvas border border-line text-sm text-ink leading-relaxed"
                      />
                    </div>

                    {/* Choose Self-Solve Run OR Custom SQL */}
                    <div className="space-y-2.5">
                      <div className="text-sm font-semibold text-ink">
                        Chọn câu lệnh SQL đáp án dùng để chấm điểm:
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {selectedDraft.reference_sql && (
                          <label className="p-3 rounded-lg bg-canvas border border-line flex items-start gap-2.5 cursor-pointer text-xs">
                            <input
                              type="radio"
                              name="sqlSource"
                              checked={sqlSourceChoice === 'ref'}
                              onChange={() => {
                                setSqlSourceChoice('ref');
                                setCustomSqlText(selectedDraft.reference_sql || '');
                              }}
                              className="mt-0.5 accent-[var(--green)]"
                            />
                            <div>
                              <div className="font-semibold text-ink">SQL chuẩn đã chốt</div>
                              <div className="text-muted">Từ bản nháp gốc</div>
                            </div>
                          </label>
                        )}

                        {(selectedDraft.self_solve_runs || []).map((run: any, rIdx: number) => (
                          <label
                            key={run.run_id}
                            className="p-3 rounded-lg bg-canvas border border-line flex items-start gap-2.5 cursor-pointer text-xs"
                          >
                            <input
                              type="radio"
                              name="sqlSource"
                              checked={sqlSourceChoice === run.run_id}
                              onChange={() => {
                                setSqlSourceChoice(run.run_id);
                                if (run.model_sql) setCustomSqlText(run.model_sql);
                              }}
                              className="mt-0.5 accent-[var(--green)]"
                            />
                            <div className="min-w-0">
                              <div className="font-semibold text-ink">
                                Mẫu giải #{rIdx + 1} ({run.review_model || 'Model B'})
                              </div>
                              <div className="text-muted tabular-nums">
                                Khớp {run.matched_datasets}/{run.total_datasets} bộ dữ liệu | {run.row_count ?? 0} dòng
                              </div>
                            </div>
                          </label>
                        ))}

                        <label className="p-3 rounded-lg bg-canvas border border-line flex items-start gap-2.5 cursor-pointer text-xs">
                          <input
                            type="radio"
                            name="sqlSource"
                            checked={sqlSourceChoice === 'custom'}
                            onChange={() => setSqlSourceChoice('custom')}
                            className="mt-0.5 accent-[var(--green)]"
                          />
                          <div>
                            <div className="font-semibold text-ink">Tự sửa trực tiếp SQL đáp án</div>
                            <div className="text-muted">Chỉnh sửa câu lệnh ngay bên dưới</div>
                          </div>
                        </label>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-muted mb-1">
                          Câu lệnh SQL đáp án (sửa trực tiếp tại đây sẽ tự chuyển sang chế độ SQL tùy chỉnh):
                        </label>
                        <textarea
                          rows={5}
                          value={customSqlText}
                          onChange={(e) => {
                            setCustomSqlText(e.target.value);
                            setSqlSourceChoice('custom');
                          }}
                          placeholder="SELECT ... FROM ..."
                          className="w-full p-3 rounded-lg bg-canvas border border-line font-mono text-xs text-ink leading-relaxed"
                        />
                      </div>
                    </div>

                    <div>
                      <input
                        value={reviewNote}
                        onChange={(e) => setReviewNote(e.target.value)}
                        placeholder="Ghi chú kiểm duyệt (tùy chọn)..."
                        className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                      />
                    </div>

                    <div className="flex flex-wrap gap-2.5 pt-1">
                      <button
                        type="button"
                        data-solid-btn="true"
                        disabled={!['needs_human', 'rejected'].includes(selectedDraft.status)}
                        onClick={handleApproveSingleDraft}
                        className="btn-primary px-5 min-h-10 rounded-lg text-sm font-semibold disabled:opacity-40"
                      >
                        Phê duyệt vào Kho Đề
                      </button>

                      <button
                        type="button"
                        disabled={!['needs_human', 'rejected'].includes(selectedDraft.status)}
                        onClick={handleEditDraft}
                        className="btn-secondary px-4 min-h-10 rounded-lg text-sm font-semibold disabled:opacity-40"
                      >
                        Lưu nội dung &amp; Chấm lại
                      </button>

                      <button
                        type="button"
                        onClick={handleRequeueDraft}
                        className="btn-subtle px-3.5 min-h-10 rounded-lg text-sm font-medium"
                      >
                        Kiểm định lại (Requeue)
                      </button>

                      <button
                        type="button"
                        data-solid-btn="true"
                        disabled={selectedDraft.status !== 'needs_human'}
                        onClick={handleRejectDraft}
                        className="btn-danger px-4 min-h-10 rounded-lg text-sm font-semibold disabled:opacity-40"
                      >
                        Từ chối
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-10 text-center text-sm text-muted">
                  Chọn một bản nháp ở cột bên trái để kiểm tra chi tiết.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          STEP 3 (CENTERPIECE): QUESTION GROUPS — DRAG & PICK + 1-CLICK PUBLISH
      ===================================================================== */}
      {step === 'step3_groups' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* LEFT COLUMN: APPROVED QUESTION BANK (DRAGGABLE & MULTI-PICK) */}
          <div className="lg:col-span-6 bg-surface border border-line rounded-2xl overflow-hidden">
            <div className="p-4 bg-soft border-b border-line space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-bold text-ink">
                    Kho Đề Đã Duyệt (Chờ gom nhóm)
                  </h2>
                  <p className="text-xs text-muted mt-0.5">
                    Tick chọn nhiều câu, bấm nút <strong>+ Thêm</strong>, hoặc nắm biểu tượng kéo thả sang Nhóm bên phải.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setStep('step1_create')}
                  className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Tạo thêm đề</span>
                </button>
              </div>

              {/* Unassigned vs All + Difficulty Filters */}
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  data-solid-btn={bankUnassignedOnly ? 'true' : undefined}
                  onClick={() => setBankUnassignedOnly(true)}
                  className={`px-3 min-h-9 rounded-lg text-xs font-semibold ${
                    bankUnassignedOnly ? 'btn-primary' : 'btn-secondary'
                  }`}
                >
                  Chưa đăng lên kệ
                </button>
                <button
                  type="button"
                  data-solid-btn={!bankUnassignedOnly ? 'true' : undefined}
                  onClick={() => setBankUnassignedOnly(false)}
                  className={`px-3 min-h-9 rounded-lg text-xs font-semibold ${
                    !bankUnassignedOnly ? 'btn-primary' : 'btn-secondary'
                  }`}
                >
                  Tất cả đề đã duyệt
                </button>

                <span className="mx-1 text-line">|</span>

                {[
                  { label: 'Mọi độ khó', val: undefined },
                  { label: 'Dễ', val: 1 },
                  { label: 'Trung bình', val: 2 },
                  { label: 'Khó', val: 3 },
                ].map((d) => {
                  const active = bankDiffFilter === d.val;
                  return (
                    <button
                      key={d.label}
                      type="button"
                      data-solid-btn={active ? 'true' : undefined}
                      onClick={() => setBankDiffFilter(d.val)}
                      className={`px-2.5 min-h-9 rounded-lg text-xs font-semibold ${
                        active ? 'btn-blue' : 'btn-secondary'
                      }`}
                    >
                      {d.label}
                    </button>
                  );
                })}
              </div>

              {/* Search + Select All Bar */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="w-4 h-4 text-muted absolute left-3 top-3" />
                  <input
                    value={bankSearch}
                    onChange={(e) => setBankSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && loadBankQuestions()}
                    placeholder="Tìm tiêu đề câu hỏi..."
                    className="w-full pl-9 pr-3 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                  />
                </div>
                <button
                  type="button"
                  onClick={loadBankQuestions}
                  className="btn-secondary px-3 min-h-10 rounded-lg text-sm font-medium"
                >
                  Tìm
                </button>
              </div>

              {/* Batch Pick Toolbar */}
              <div className="pt-2 border-t border-line flex flex-wrap items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const pageIds = bankQuestions.map((q) => q.question_id);
                    const allChecked =
                      pageIds.length > 0 && pageIds.every((id) => pickedBankIds.includes(id));
                    setPickedBankIds(allChecked ? [] : pageIds);
                  }}
                  className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold"
                >
                  Chọn tất cả trang này ({bankQuestions.length} câu)
                </button>

                {pickedBankIds.length > 0 && (
                  <button
                    type="button"
                    data-solid-btn="true"
                    disabled={groupBusy}
                    onClick={() => handleAddQuestionsToGroup(pickedBankIds)}
                    className="btn-primary px-4 min-h-9 rounded-lg text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <span>Đưa {pickedBankIds.length} câu đã chọn vào Nhóm</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Left Question Rows */}
            <div className="divide-y divide-line max-h-[640px] overflow-y-auto">
              {bankQuestions.length === 0 ? (
                <div className="p-8 text-center space-y-3">
                  <div className="text-sm text-muted">
                    {bankUnassignedOnly
                      ? 'Hiện không có câu hỏi mới nào chưa đăng lên kệ.'
                      : 'Kho đề hiện chưa có câu hỏi nào.'}
                  </div>
                  <div className="flex flex-wrap justify-center gap-2">
                    {bankUnassignedOnly && (
                      <button
                        type="button"
                        onClick={() => setBankUnassignedOnly(false)}
                        className="btn-secondary px-3.5 min-h-9 rounded-lg text-xs font-semibold"
                      >
                        Xem tất cả đề đã duyệt
                      </button>
                    )}
                    <button
                      type="button"
                      data-solid-btn="true"
                      onClick={() => setStep('step1_create')}
                      className="btn-primary px-3.5 min-h-9 rounded-lg text-xs font-semibold"
                    >
                      Soạn câu hỏi mới (Bước 1)
                    </button>
                  </div>
                </div>
              ) : (
                bankQuestions.map((q) => {
                  const qid = q.question_id;
                  const checked = pickedBankIds.includes(qid);
                  const alreadyInGroup = groupItemIdSet.has(qid);
                  const diff = DIFF_LABELS[q.difficulty] || DIFF_LABELS[1];
                  const tables = Array.isArray(q.tables_used) ? q.tables_used : [];
                  const preview = previewCache[qid];
                  return (
                    <div
                      key={qid}
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData('text/plain', String(qid));
                        e.dataTransfer.effectAllowed = 'copy';
                        setDraggingQuestionId(qid);
                      }}
                      onDragEnd={() => {
                        setDraggingQuestionId(null);
                        setIsOverDropZone(false);
                      }}
                      className={`p-3.5 space-y-2 transition-colors ${
                        draggingQuestionId === qid ? 'opacity-60 bg-soft' : 'hover:bg-canvas'
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            setPickedBankIds((prev) =>
                              prev.includes(qid) ? prev.filter((x) => x !== qid) : [...prev, qid]
                            )
                          }
                          aria-label={`Chọn câu hỏi #${qid}`}
                          className="mt-1 w-4 h-4 accent-[var(--green)] cursor-pointer shrink-0"
                        />
                        <div
                          className="mt-0.5 text-muted cursor-grab active:cursor-grabbing shrink-0"
                          title="Nắm kéo sang cột Nhóm đề bên phải"
                        >
                          <GripVertical className="w-4 h-4" />
                        </div>

                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="text-sm font-semibold text-ink leading-snug">
                            <code className="text-xs text-muted mr-1.5">#{qid}</code>
                            {q.title}
                          </div>

                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${diff.badge}`}>
                              {diff.text}
                            </span>
                            {tables.slice(0, 3).map((tb: string) => (
                              <code
                                key={tb}
                                className="px-1.5 py-0.5 rounded bg-soft text-xs text-text2"
                              >
                                {tb}
                              </code>
                            ))}
                            {q.in_published_set && (
                              <span className="px-2 py-0.5 rounded badge-info text-xs font-medium">
                                Đang trên kệ
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => toggleQuestionPreview(qid)}
                            className="btn-secondary px-2.5 min-h-9 rounded-lg text-xs font-medium flex items-center gap-1"
                            title="Xem đề bài & SQL đáp án"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Xem</span>
                          </button>

                          {alreadyInGroup ? (
                            <span className="px-2.5 py-1.5 rounded-lg badge-easy text-xs font-semibold">
                              Đã trong nhóm
                            </span>
                          ) : (
                            <button
                              type="button"
                              data-solid-btn="true"
                              disabled={groupBusy}
                              onClick={() => handleAddQuestionsToGroup([qid])}
                              className="btn-primary px-3 min-h-9 rounded-lg text-xs font-semibold flex items-center gap-1 disabled:opacity-50"
                            >
                              <Plus className="w-3.5 h-3.5" />
                              <span>Thêm</span>
                            </button>
                          )}
                        </div>
                      </div>

                      {previewQuestionId === qid && (
                        <div className="ml-8 p-3 rounded-xl bg-canvas border border-line space-y-2 text-xs">
                          <div className="text-sm text-ink leading-relaxed">
                            {preview?.question || 'Đang tải nội dung đề bài...'}
                          </div>
                          {preview?.reference_sql && (
                            <pre className="p-2.5 rounded-lg bg-surface border border-line text-xs text-ink overflow-x-auto">
                              {preview.reference_sql}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* RIGHT COLUMN: GROUP COMPOSER, DROP ZONE & 1-CLICK BATCH PUBLISH */}
          <div className="lg:col-span-6 bg-surface border border-line rounded-2xl overflow-hidden flex flex-col">
            {/* Group Selector & Quick Create */}
            <div className="p-4 bg-soft border-b border-line space-y-3">
              <div>
                <h2 className="text-base font-bold text-ink">
                  Nhóm Đề Đã Gom &amp; Đăng Toàn Bộ
                </h2>
                <p className="text-xs text-muted mt-0.5">
                  Tạo hoặc chọn một nhóm đề, sắp xếp thứ tự câu hỏi rồi bấm đăng toàn bộ lên kệ cùng lúc.
                </p>
              </div>

              <form onSubmit={handleCreateGroup} className="flex flex-wrap gap-2">
                <input
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="Nhập tên nhóm đề mới (VD: Bài kiểm tra SQL đợt 1)..."
                  className="flex-1 min-w-[220px] px-3.5 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                />
                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={creatingGroup}
                  className="btn-primary px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-1.5 shrink-0"
                >
                  <FolderPlus className="w-4 h-4" />
                  <span>{creatingGroup ? 'Đang tạo...' : '+ Tạo nhóm'}</span>
                </button>
              </form>

              {/* Group Pills */}
              {groups.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {groups.map((g) => {
                    const active = selectedGroupId === g.group_id;
                    const isPub = g.status === 'published';
                    return (
                      <button
                        key={g.group_id}
                        type="button"
                        data-solid-btn={active ? 'true' : undefined}
                        onClick={() => {
                          setPublishSetTitle(g.name || '');
                          loadGroupDetail(g.group_id);
                        }}
                        className={`px-3 min-h-9 rounded-lg text-xs font-semibold flex items-center gap-2 ${
                          active ? 'btn-blue' : 'btn-secondary'
                        }`}
                      >
                        <span>{g.name}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-xs tabular-nums ${
                            active
                              ? 'bg-surface text-ink'
                              : isPub
                              ? 'badge-easy'
                              : 'badge-medium'
                          }`}
                        >
                          {g.question_count} câu ({isPub ? 'Đã đăng' : 'Nháp'})
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Interactive Drop Zone + Group Items List */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                if (!isOverDropZone) setIsOverDropZone(true);
              }}
              onDragLeave={() => setIsOverDropZone(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsOverDropZone(false);
                const rawQid = e.dataTransfer.getData('text/plain');
                const parsedQid = Number(rawQid);
                if (parsedQid && !Number.isNaN(parsedQid)) {
                  handleAddQuestionsToGroup([parsedQid]);
                }
              }}
              className={`p-4 space-y-4 transition-colors ${
                isOverDropZone ? 'bg-soft' : 'bg-surface'
              }`}
            >
              {/* Visual Drop Target Banner */}
              <div
                className={`p-4 rounded-xl border-2 border-dashed text-center text-sm ${
                  isOverDropZone
                    ? 'border-brand bg-canvas text-brand font-bold'
                    : 'border-line bg-canvas text-muted'
                }`}
              >
                {groupDetail ? (
                  isSelectedGroupEditable ? (
                    <span>
                      Kéo câu hỏi từ cột bên trái thả vào đây để đưa vào nhóm{' '}
                      <strong className="text-ink">&quot;{groupDetail.name}&quot;</strong>
                    </span>
                  ) : (
                    <span>
                      Nhóm <strong className="text-ink">&quot;{groupDetail.name}&quot;</strong> đã được phát hành lên kệ. Hãy tạo nhóm mới ở trên nếu muốn gom đợt đề tiếp theo.
                    </span>
                  )
                ) : (
                  <span>
                    Kéo thả câu hỏi bất kỳ vào khung này (hệ thống sẽ tự tạo nhóm nháp mới ngay lập tức)
                  </span>
                )}
              </div>

              {groupDetail && (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-ink">
                        {groupDetail.name} ({groupItems.length} câu hỏi)
                      </h3>
                      <span
                        className={`px-2 py-0.5 rounded-md text-xs font-semibold ${
                          groupDetail.status === 'published' ? 'badge-easy' : 'badge-medium'
                        }`}
                      >
                        {groupDetail.status === 'published' ? 'Đã đăng lên kệ' : 'Nhóm nháp'}
                      </span>
                    </div>

                    {isSelectedGroupEditable && (
                      <button
                        type="button"
                        disabled={groupBusy}
                        onClick={handleDeleteGroup}
                        className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold text-danger flex items-center gap-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Xoá nhóm nháp</span>
                      </button>
                    )}
                  </div>

                  {/* Items inside Group */}
                  {groupItems.length === 0 ? (
                    <div className="p-6 rounded-xl bg-canvas border border-line text-center text-sm text-muted">
                      Nhóm này chưa có câu hỏi nào. Hãy bấm <strong>+ Thêm</strong> hoặc kéo thả câu hỏi từ cột trái sang.
                    </div>
                  ) : (
                    <div className="divide-y divide-line border border-line rounded-xl overflow-hidden max-h-[360px] overflow-y-auto">
                      {groupItems.map((it: any, idx: number) => {
                        const diff = DIFF_LABELS[it.difficulty] || DIFF_LABELS[1];
                        const preview = previewCache[it.question_id];
                        return (
                          <div
                            key={it.question_id}
                            draggable={isSelectedGroupEditable}
                            onDragStart={() => setDraggingGroupItemIdx(idx)}
                            onDragOver={(e) => {
                              if (draggingGroupItemIdx !== null) e.preventDefault();
                            }}
                            onDrop={(e) => {
                              if (
                                draggingGroupItemIdx !== null &&
                                draggingGroupItemIdx !== idx &&
                                isSelectedGroupEditable
                              ) {
                                e.stopPropagation();
                                const ids = groupItems.map((x: any) => x.question_id);
                                const moved = ids[draggingGroupItemIdx];
                                const remaining = ids.filter(
                                  (_: number, i: number) => i !== draggingGroupItemIdx
                                );
                                remaining.splice(idx, 0, moved);
                                setDraggingGroupItemIdx(null);
                                handleReorderGroupItems(remaining);
                              }
                            }}
                            onDragEnd={() => setDraggingGroupItemIdx(null)}
                            className="p-3 bg-surface hover:bg-canvas space-y-2"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2.5 min-w-0">
                                <span className="w-7 h-7 rounded-md bg-soft border border-line text-xs font-bold text-ink flex items-center justify-center shrink-0 tabular-nums">
                                  {idx + 1}
                                </span>
                                <div className="min-w-0">
                                  <div className="text-sm font-semibold text-ink truncate">
                                    {it.title}
                                  </div>
                                  <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                                    <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${diff.badge}`}>
                                      {diff.text}
                                    </span>
                                    <code className="text-xs text-muted">ID #{it.question_id}</code>
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center gap-1 shrink-0">
                                <button
                                  type="button"
                                  onClick={() => toggleQuestionPreview(it.question_id)}
                                  className="btn-secondary px-2 min-h-9 rounded-md text-xs font-medium"
                                  title="Xem trước nội dung & SQL"
                                >
                                  Xem
                                </button>
                                {isSelectedGroupEditable && (
                                  <>
                                    <button
                                      type="button"
                                      disabled={idx === 0 || groupBusy}
                                      onClick={() => moveGroupItem(idx, -1)}
                                      aria-label="Đưa câu này lên trên"
                                      className="btn-secondary min-w-9 min-h-9 rounded-md flex items-center justify-center disabled:opacity-30"
                                    >
                                      <ArrowUp className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                      type="button"
                                      disabled={idx === groupItems.length - 1 || groupBusy}
                                      onClick={() => moveGroupItem(idx, 1)}
                                      aria-label="Đưa câu này xuống dưới"
                                      className="btn-secondary min-w-9 min-h-9 rounded-md flex items-center justify-center disabled:opacity-30"
                                    >
                                      <ArrowDown className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                      type="button"
                                      disabled={groupBusy}
                                      onClick={() => removeGroupItem(it.question_id)}
                                      aria-label="Gỡ câu hỏi khỏi nhóm"
                                      className="btn-secondary px-2.5 min-h-9 rounded-md text-xs font-semibold text-danger"
                                    >
                                      Gỡ
                                    </button>
                                  </>
                                )}
                              </div>
                            </div>

                            {previewQuestionId === it.question_id && (
                              <div className="p-3 rounded-lg bg-canvas border border-line space-y-2 text-xs">
                                <div className="text-sm text-ink leading-relaxed">
                                  {preview?.question || 'Đang tải đề bài...'}
                                </div>
                                {preview?.reference_sql && (
                                  <pre className="p-2.5 rounded bg-surface border border-line text-xs text-ink overflow-x-auto">
                                    {preview.reference_sql}
                                  </pre>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Prominent 1-Click Batch Publish Panel */}
                  {isSelectedGroupEditable && (
                    <div className="p-4 rounded-xl bg-soft border border-line space-y-3.5">
                      <div className="text-sm font-bold text-ink">
                        Chọn cách đăng toàn bộ nhóm đề lên kệ bài tập:
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <label
                          className={`p-3 rounded-xl border cursor-pointer flex items-start gap-2.5 ${
                            publishMode === 'append_active'
                              ? 'bg-surface border-brand'
                              : 'bg-canvas border-line'
                          }`}
                        >
                          <input
                            type="radio"
                            name="publishMode"
                            checked={publishMode === 'append_active'}
                            onChange={() => setPublishMode('append_active')}
                            className="mt-1 accent-[var(--green)]"
                          />
                          <div className="text-xs space-y-0.5">
                            <div className="text-sm font-semibold text-ink">
                              Đẩy gộp ngay vào Kệ Đang Mở
                            </div>
                            <div className="text-muted leading-relaxed">
                              Mặc định khuyên dùng: Nối thêm toàn bộ câu trong nhóm vào kệ đang mở để sinh viên thấy ngay.
                            </div>
                          </div>
                        </label>

                        <label
                          className={`p-3 rounded-xl border cursor-pointer flex items-start gap-2.5 ${
                            publishMode === 'new_weekly_set'
                              ? 'bg-surface border-brand'
                              : 'bg-canvas border-line'
                          }`}
                        >
                          <input
                            type="radio"
                            name="publishMode"
                            checked={publishMode === 'new_weekly_set'}
                            onChange={() => setPublishMode('new_weekly_set')}
                            className="mt-1 accent-[var(--green)]"
                          />
                          <div className="text-xs space-y-0.5">
                            <div className="text-sm font-semibold text-ink">
                              Phát hành thành Bộ Đề Tuần Mới
                            </div>
                            <div className="text-muted leading-relaxed">
                              Đóng bộ đề cũ và mở kệ mới độc lập chỉ gồm đúng các câu trong nhóm này.
                            </div>
                          </div>
                        </label>
                      </div>

                      {publishMode === 'new_weekly_set' && (
                        <div>
                          <label className="block text-xs font-semibold text-ink mb-1">
                            Tên Bộ đề tuần mới khi phát hành
                          </label>
                          <input
                            value={publishSetTitle}
                            onChange={(e) => setPublishSetTitle(e.target.value)}
                            placeholder={groupDetail.name}
                            className="w-full px-3.5 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                          />
                        </div>
                      )}

                      <button
                        type="button"
                        data-solid-btn="true"
                        disabled={groupBusy || groupItems.length === 0}
                        onClick={handlePublishGroup}
                        className="btn-primary w-full min-h-12 px-5 rounded-xl text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-40"
                      >
                        <Send className="w-4 h-4" />
                        <span>
                          {groupBusy
                            ? 'Đang phát hành nhóm đề...'
                            : `Đăng toàn bộ ${groupItems.length} câu trong nhóm lên kệ ngay`}
                        </span>
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          STEP 4: WEEKLY SETS INSPECTOR, FULL BANK, USERS & SYSTEM SETTINGS
      ===================================================================== */}
      {step === 'step4_system' && (
        <div className="space-y-4">
          {/* Step 4 Sub-tabs */}
          <div className="bg-surface border border-line rounded-xl p-2 flex flex-wrap gap-1.5">
            {[
              { id: 'weekly', label: 'Bộ đề tuần & Kệ đang mở', icon: CalendarRange },
              { id: 'bank', label: 'Toàn bộ Ngân hàng đề', icon: Database },
              { id: 'users', label: 'Người dùng & Phân quyền', icon: Users },
              { id: 'settings', label: 'Cấu hình hệ thống', icon: Settings },
            ].map((t) => {
              const Icon = t.icon;
              const active = step4Tab === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  data-solid-btn={active ? 'true' : undefined}
                  onClick={() => setStep4Tab(t.id as any)}
                  className={`px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-2 ${
                    active ? 'btn-primary' : 'btn-secondary'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{t.label}</span>
                </button>
              );
            })}
          </div>

          {/* 4A: WEEKLY SETS WITH FULL QUESTION DETAIL INSPECTOR */}
          {step4Tab === 'weekly' && (
            <div className="space-y-4">
              <form
                onSubmit={handleCreateWeeklySet}
                className="bg-surface border border-line rounded-xl p-4 flex flex-wrap items-end gap-3"
              >
                <div className="flex-1 min-w-[220px]">
                  <label className="block text-xs font-semibold text-muted mb-1">
                    Tiêu đề bộ đề tuần mới
                  </label>
                  <input
                    value={newWeekTitle}
                    onChange={(e) => setNewWeekTitle(e.target.value)}
                    className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-muted mb-1">
                    Ngày bắt đầu tuần (week_start)
                  </label>
                  <input
                    type="date"
                    value={newWeekStart}
                    onChange={(e) => setNewWeekStart(e.target.value)}
                    className="px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  />
                </div>
                <button
                  type="submit"
                  data-solid-btn="true"
                  className="btn-primary px-5 min-h-10 rounded-lg text-sm font-semibold"
                >
                  + Khởi tạo bộ đề tuần tự động
                </button>
              </form>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                {/* Left Weekly Sets List */}
                <div className="lg:col-span-5 bg-surface border border-line rounded-xl overflow-hidden">
                  <div className="px-4 py-3.5 bg-soft border-b border-line text-sm font-bold text-ink">
                    Danh sách các Bộ đề tuần ({weeklySets.length})
                  </div>
                  <div className="divide-y divide-line max-h-[540px] overflow-y-auto">
                    {weeklySets.length === 0 ? (
                      <div className="p-8 text-center text-sm text-muted">
                        Chưa có bộ đề tuần nào.
                      </div>
                    ) : (
                      weeklySets.map((w) => {
                        const active = selectedWeeklySetId === w.set_id;
                        const badgeCls =
                          w.status === 'published'
                            ? 'badge-easy'
                            : w.status === 'draft'
                            ? 'badge-medium'
                            : 'badge-neutral';
                        return (
                          <div
                            key={w.set_id}
                            onClick={() => inspectWeeklySet(w.set_id)}
                            className={`p-4 cursor-pointer space-y-2 transition-colors ${
                              active ? 'bg-soft' : 'hover:bg-canvas'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <div className="text-sm font-bold text-ink">
                                  Bộ #{w.set_id}: {w.title}
                                </div>
                                <div className="text-xs text-muted mt-0.5 tabular-nums">
                                  Tuần bắt đầu: {w.week_start}
                                </div>
                              </div>
                              <span className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${badgeCls}`}>
                                {w.status === 'published'
                                  ? 'Đang mở'
                                  : w.status === 'draft'
                                  ? 'Bản nháp'
                                  : 'Đã đóng'}
                              </span>
                            </div>

                            <div
                              className="flex flex-wrap gap-2 pt-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {w.status === 'draft' && (
                                <button
                                  type="button"
                                  data-solid-btn="true"
                                  onClick={() =>
                                    publishAdminWeeklySet(w.set_id)
                                      .then(() => {
                                        setMsg(`Đã phát hành bộ đề tuần #${w.set_id} lên kệ bài tập!`);
                                        loadWeekly();
                                      })
                                      .catch((e) =>
                                        setErr(
                                          extractApiError(
                                            e,
                                            'Không thể phát hành (hãy đóng bộ đề đang mở trước)'
                                          )
                                        )
                                      )
                                  }
                                  className="btn-primary px-3 min-h-9 rounded-lg text-xs font-semibold"
                                >
                                  Phát hành bộ đề này
                                </button>
                              )}
                              {w.status === 'published' && (
                                <button
                                  type="button"
                                  data-solid-btn="true"
                                  onClick={() =>
                                    closeAdminWeeklySet(w.set_id)
                                      .then(() => {
                                        setMsg(`Đã đóng chu kỳ bộ đề tuần #${w.set_id}.`);
                                        loadWeekly();
                                      })
                                      .catch((e) =>
                                        setErr(extractApiError(e, 'Không thể đóng bộ đề tuần'))
                                      )
                                  }
                                  className="btn-danger px-3 min-h-9 rounded-lg text-xs font-semibold"
                                >
                                  Đóng chu kỳ tuần
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Right Weekly Set Questions Detail */}
                <div className="lg:col-span-7 bg-surface border border-line rounded-xl overflow-hidden">
                  <div className="px-5 py-3.5 bg-soft border-b border-line flex items-center justify-between">
                    <h3 className="text-sm font-bold text-ink">
                      {weeklySetDetail
                        ? `Các câu hỏi bên trong Bộ #${weeklySetDetail.set_id}: ${weeklySetDetail.title} (${
                            weeklySetDetail.items?.length || 0
                          } câu)`
                        : 'Chi tiết câu hỏi trong Bộ đề tuần'}
                    </h3>
                  </div>

                  {loadingWeeklyDetail ? (
                    <div className="p-10 text-center text-sm text-muted">
                      Đang tải danh sách câu hỏi trong bộ đề...
                    </div>
                  ) : !weeklySetDetail ? (
                    <div className="p-10 text-center text-sm text-muted">
                      Bấm vào một bộ đề tuần ở bên trái để xem danh sách câu hỏi bên trong.
                    </div>
                  ) : (weeklySetDetail.items || []).length === 0 ? (
                    <div className="p-10 text-center text-sm text-muted">
                      Bộ đề này hiện chưa có câu hỏi nào.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-sm tabular-nums">
                        <thead>
                          <tr className="bg-canvas border-b border-line text-text2 font-semibold">
                            <th className="py-3 px-4 w-20">Vị trí</th>
                            <th className="py-3 px-4">Câu hỏi</th>
                            <th className="py-3 px-4 w-32">Độ khó</th>
                            {weeklySetDetail.status === 'draft' && (
                              <th className="py-3 px-4 w-24">Thao tác</th>
                            )}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-line">
                          {(weeklySetDetail.items || []).map((raw: any, idx: number) => {
                            const item = normalizeGroupItem(raw);
                            const diff = DIFF_LABELS[item.difficulty] || DIFF_LABELS[1];
                            return (
                              <tr key={`${item.question_id}-${idx}`} className="hover:bg-soft">
                                <td className="py-3 px-4 font-bold text-brand">
                                  <code>SQL{item.position || idx + 1}</code>
                                </td>
                                <td className="py-3 px-4">
                                  <div className="font-semibold text-ink">{item.title}</div>
                                  <div className="text-xs text-muted">ID #{item.question_id}</div>
                                </td>
                                <td className="py-3 px-4">
                                  <span
                                    className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${diff.badge}`}
                                  >
                                    {diff.text}
                                  </span>
                                </td>
                                {weeklySetDetail.status === 'draft' && (
                                  <td className="py-3 px-4">
                                    <button
                                      type="button"
                                      onClick={() =>
                                        handleRemoveFromWeeklySet(
                                          weeklySetDetail.set_id,
                                          item.question_id
                                        )
                                      }
                                      className="btn-secondary px-2.5 min-h-8 rounded-md text-xs font-semibold text-danger"
                                    >
                                      Gỡ
                                    </button>
                                  </td>
                                )}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 4B: FULL LIVE QUESTIONS BANK */}
          {step4Tab === 'bank' && (
            <div className="bg-surface border border-line rounded-xl overflow-hidden">
              <div className="px-5 py-4 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-base font-bold text-ink">
                  Toàn bộ Ngân hàng đề ({allBankQuestions.length} câu)
                </h3>
                <select
                  value={allBankStatusFilter}
                  onChange={(e) => setAllBankStatusFilter(e.target.value)}
                  className="px-3 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                >
                  <option value="">Tất cả trạng thái</option>
                  <option value="ready">Đang sẵn sàng (ready)</option>
                  <option value="retired">Đã thu hồi (retired)</option>
                </select>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm tabular-nums">
                  <thead>
                    <tr className="bg-canvas border-b border-line text-text2 font-semibold">
                      <th className="py-3 px-4 w-24">ID</th>
                      <th className="py-3 px-4">Tiêu đề câu hỏi</th>
                      <th className="py-3 px-4 w-32">Độ khó</th>
                      <th className="py-3 px-4 w-48">Bảng sử dụng</th>
                      <th className="py-3 px-4 w-56">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {allBankQuestions.map((q: any) => {
                      const diff = DIFF_LABELS[q.difficulty] || DIFF_LABELS[1];
                      return (
                        <tr key={q.question_id} className="hover:bg-soft">
                          <td className="py-3 px-4 font-bold text-brand">
                            <code>#{q.question_id}</code>
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-semibold text-ink">{q.title}</div>
                            <div className="text-xs text-muted mt-0.5">
                              Trạng thái: {q.status}
                              {q.in_published_set ? ' | Đang mở trên kệ' : ''}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${diff.badge}`}>
                              {diff.text}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-xs text-text2">
                            {Array.isArray(q.tables_used) ? q.tables_used.join(', ') : '-'}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <button
                                type="button"
                                onClick={() =>
                                  toggleAdminQuestionSource(q.question_id, !q.is_source)
                                    .then(() => {
                                      setMsg(`Đã cập nhật trạng thái Seed mẫu cho câu #${q.question_id}.`);
                                      loadAllBankQuestions();
                                    })
                                    .catch((e) => setErr(extractApiError(e, 'Lỗi cập nhật Seed mẫu')))
                                }
                                className={`px-2.5 min-h-8 rounded-md text-xs font-semibold ${
                                  q.is_source ? 'badge-easy' : 'btn-secondary'
                                }`}
                              >
                                Đề mẫu AI: {q.is_source ? 'Bật' : 'Tắt'}
                              </button>

                              {q.status !== 'retired' ? (
                                <button
                                  type="button"
                                  onClick={() =>
                                    retireAdminQuestion(q.question_id, 'Giảng viên thu hồi')
                                      .then(() => {
                                        setMsg(`Đã thu hồi câu hỏi #${q.question_id}.`);
                                        loadAllBankQuestions();
                                        loadBankQuestions();
                                      })
                                      .catch((e) => setErr(extractApiError(e, 'Không thể thu hồi câu hỏi')))
                                  }
                                  className="btn-secondary px-2.5 min-h-8 rounded-md text-xs font-semibold text-danger"
                                >
                                  Thu hồi
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  data-solid-btn="true"
                                  onClick={() =>
                                    restoreAdminQuestion(q.question_id)
                                      .then(() => {
                                        setMsg(`Đã khôi phục câu hỏi #${q.question_id}.`);
                                        loadAllBankQuestions();
                                        loadBankQuestions();
                                      })
                                      .catch((e) => setErr(extractApiError(e, 'Không thể khôi phục câu hỏi')))
                                  }
                                  className="btn-primary px-2.5 min-h-8 rounded-md text-xs font-semibold"
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
          )}

          {/* 4C: USERS MANAGEMENT */}
          {step4Tab === 'users' && (
            <div className="bg-surface border border-line rounded-xl overflow-hidden">
              <div className="px-5 py-4 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-base font-bold text-ink">
                  Danh sách Tài khoản &amp; Phân quyền
                </h3>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="w-4 h-4 text-muted absolute left-3 top-3" />
                    <input
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && loadUsers()}
                      placeholder="Tìm tên đăng nhập hoặc email..."
                      className="pl-9 pr-3 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={loadUsers}
                    className="btn-secondary px-3.5 min-h-10 rounded-lg text-sm font-semibold"
                  >
                    Lọc
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm tabular-nums">
                  <thead>
                    <tr className="bg-canvas border-b border-line text-text2 font-semibold">
                      <th className="py-3 px-4">ID</th>
                      <th className="py-3 px-4">Tài khoản</th>
                      <th className="py-3 px-4">Email</th>
                      <th className="py-3 px-4">Vai trò</th>
                      <th className="py-3 px-4">Trạng thái</th>
                      <th className="py-3 px-4">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {users.map((u) => (
                      <tr key={u.user_id} className="hover:bg-soft">
                        <td className="py-3 px-4 text-muted">
                          <code>#{u.user_id}</code>
                        </td>
                        <td className="py-3 px-4 font-semibold text-ink">
                          {u.display_name || u.username}{' '}
                          <span className="text-muted font-normal">(@{u.username})</span>
                        </td>
                        <td className="py-3 px-4 text-text2">{u.email}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                              u.role === 'admin' ? 'badge-medium' : 'badge-info'
                            }`}
                          >
                            {u.role === 'admin' ? 'Admin' : 'Sinh viên'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                              u.status === 'active' ? 'badge-easy' : 'badge-hard'
                            }`}
                          >
                            {u.status === 'active' ? 'Đang hoạt động' : 'Đã khóa'}
                          </span>
                        </td>
                        <td className="py-3 px-4 flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => handleToggleUser(u, 'role')}
                            className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold"
                          >
                            Đổi vai trò
                          </button>
                          <button
                            type="button"
                            onClick={() => handleToggleUser(u, 'status')}
                            className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold"
                          >
                            {u.status === 'active' ? 'Khóa tài khoản' : 'Mở khóa'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 4D: SYSTEM SETTINGS */}
          {step4Tab === 'settings' && (
            <div className="bg-surface border border-line rounded-xl overflow-hidden">
              <div className="px-5 py-4 bg-soft border-b border-line">
                <h3 className="text-base font-bold text-ink">
                  Tham số Cấu hình Hệ thống (live.system_settings)
                </h3>
              </div>
              <div className="divide-y divide-line">
                {settingsList.map((st: any) => (
                  <div
                    key={st.key}
                    className="p-4 flex flex-wrap items-center justify-between gap-3 text-sm"
                  >
                    <div>
                      <code className="text-ink font-bold">{st.key}</code>
                      {st.description && (
                        <div className="text-xs text-muted mt-0.5">{st.description}</div>
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
                        className="px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink w-64 disabled:opacity-50"
                      />
                      {st.mutable === false ? (
                        <span className="px-3 min-h-10 rounded-lg badge-neutral text-xs font-medium inline-flex items-center">
                          Cố định
                        </span>
                      ) : (
                        <button
                          type="button"
                          data-solid-btn="true"
                          onClick={() => handleUpdateSetting(st.key)}
                          className="btn-primary px-4 min-h-10 rounded-lg text-sm font-semibold"
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
      )}
    </div>
  );
}
