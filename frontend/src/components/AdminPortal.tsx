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
  ArrowRight,
  FolderPlus,
  Send,
  Eye,
  FilePlus2,
  Sparkles,
  CalendarRange,
  Users,
  Settings,
  Database,
  RotateCcw,
  X,
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
  returnAdminDraftNeedsHuman,
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
  updateAdminWeeklySetItems,
  removeAdminWeeklySetItem,
  publishAdminWeeklySet,
  closeAdminWeeklySet,
  getAdminUsers,
  getAdminUserDetail,
  updateAdminUser,
  getAdminSettings,
  getAdminSkills,
  updateAdminSetting,
  getDatasetSchema,
  extractApiError,
} from '../lib/api';
import { matchesVisibleRecord } from '../lib/search';

type AdminTabId = 'users' | 'generate' | 'drafts' | 'weekly' | 'bank' | 'settings';

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

function formatAiStageLabel(stage?: string | null): string {
  const s = String(stage || '').toLowerCase();
  if (s.includes('gen') || s.includes('blueprint') || s.includes('author')) {
    return 'Model A · Sinh đề';
  }
  return 'Model B · Kiểm duyệt';
}

function formatDraftStatusBadge(status?: string | null): { text: string; cls: string } {
  switch (status) {
    case 'approved':
      return { text: 'Đã duyệt', cls: 'badge-easy' };
    case 'needs_human':
      return { text: 'Cần duyệt', cls: 'badge-medium' };
    case 'rejected':
      return { text: 'Đã từ chối', cls: 'badge-hard' };
    case 'pending':
    case 'reviewing':
      return { text: 'Đang chấm AI', cls: 'badge-info' };
    default:
      return { text: String(status || 'Đang xử lý'), cls: 'badge-neutral' };
  }
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

interface UnifiedApprovedItem {
  key: string;
  question_id: number | null;
  draft_id: number | null;
  title: string;
  difficulty: number;
  tables_used: string[];
  in_published_set: boolean;
}

export default function AdminPortal({
  isAdmin,
}: {
  isAdmin: boolean;
  onJumpToWorkbench?: () => void;
}) {
  // Default tab is strictly 'users' (Người dùng — leftmost first tab!)
  const [activeTab, setActiveTab] = useState<AdminTabId>('users');
  const [createMode, setCreateMode] = useState<'ai' | 'manual'>('ai');

  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Shared Skills & Schema
  const [skillOptions, setSkillOptions] = useState(SKILL_OPTIONS);
  const [schemaTables, setSchemaTables] = useState<any[]>([]);

  // Tab 1: Users
  const [users, setUsers] = useState<any[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [selectedUserDetail, setSelectedUserDetail] = useState<any | null>(null);
  const [loadingUserDetail, setLoadingUserDetail] = useState(false);
  const userDetailReqRef = React.useRef(0);

  // Tab 2: AI Generation + Per-Skill Quantities + Secret-Blind Gateway Vault
  const [jobs, setJobs] = useState<any[]>([]);
  const [llmUsage, setLlmUsage] = useState<any>(null);
  const [gatewayStatus, setGatewayStatus] = useState<any>(null);
  const [gatewayKeyInput, setGatewayKeyInput] = useState('');
  const [gatewayModelInput, setGatewayModelInput] = useState('gpt-5.6-sol');
  const [savingGatewayKey, setSavingGatewayKey] = useState(false);
  const [showGatewayForm, setShowGatewayForm] = useState(false);
  const [jobDiff, setJobDiff] = useState(1);
  const [jobTopic, setJobTopic] = useState('');
  const [jobSkills, setJobSkills] = useState<number[]>([1, 2]);
  const [skillQuantities, setSkillQuantities] = useState<Record<number, number>>({
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 1,
    6: 1,
  });
  const [submittingJob, setSubmittingJob] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);

  // Manual Question Authoring
  const [manualTitle, setManualTitle] = useState('');
  const [manualQuestion, setManualQuestion] = useState('');
  const [manualSql, setManualSql] = useState(
    'SELECT category_id, category_name\nFROM categories\nORDER BY category_id ASC;'
  );
  const [manualDiff, setManualDiff] = useState<number>(1);
  const [manualCompareMode, setManualCompareMode] = useState<'unordered' | 'ordered'>('unordered');
  const [manualSkills, setManualSkills] = useState<number[]>([1]);
  const [savingManual, setSavingManual] = useState(false);

  // Tab 3: Draft Review
  const [draftStatusFilter, setDraftStatusFilter] = useState<string>('');
  const [draftSearch, setDraftSearch] = useState<string>('');
  const [drafts, setDrafts] = useState<any[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<any>(null);
  const [checkedDraftIds, setCheckedDraftIds] = useState<number[]>([]);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [draftActionBusy, setDraftActionBusy] = useState(false);

  const [editTitle, setEditTitle] = useState('');
  const [editQuestion, setEditQuestion] = useState('');
  const [reviewNote, setReviewNote] = useState('');
  const [sqlSourceChoice, setSqlSourceChoice] = useState<'ref' | 'custom' | number>('ref');
  const [customSqlText, setCustomSqlText] = useState('');

  // Tab 4: Weekly Sets + Approved Questions Pool + Batch Group Publish
  const [approvedShelfTab, setApprovedShelfTab] = useState<'unassigned' | 'on_shelf'>('unassigned');
  const [approvedDiffFilter, setApprovedDiffFilter] = useState<number | undefined>(undefined);
  const [approvedSearch, setApprovedSearch] = useState<string>('');
  const [readyQuestions, setReadyQuestions] = useState<any[]>([]);
  const [pickedApprovedKeys, setPickedApprovedKeys] = useState<string[]>([]);

  const [groups, setGroups] = useState<any[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [groupDetail, setGroupDetail] = useState<any>(null);
  const [newGroupName, setNewGroupName] = useState('');
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [groupBusy, setGroupBusy] = useState(false);

  const [draggingApprovedKey, setDraggingApprovedKey] = useState<string | null>(null);
  const [draggingGroupItemIdx, setDraggingGroupItemIdx] = useState<number | null>(null);
  const [isOverDropZone, setIsOverDropZone] = useState<boolean>(false);

  const [publishMode, setPublishMode] = useState<'append_active' | 'new_weekly_set'>('append_active');
  const [publishSetTitle, setPublishSetTitle] = useState('');

  const [previewQuestionId, setPreviewQuestionId] = useState<number | null>(null);
  const [previewCache, setPreviewCache] = useState<Record<number, any>>({});

  const [weeklySets, setWeeklySets] = useState<any[]>([]);
  const [selectedWeeklySetId, setSelectedWeeklySetId] = useState<number | null>(null);
  const [weeklySetDetail, setWeeklySetDetail] = useState<any>(null);
  const [loadingWeeklyDetail, setLoadingWeeklyDetail] = useState(false);

  // Tab 5 & 6: Bank & Settings
  const [allBankStatusFilter, setAllBankStatusFilter] = useState<string>('');
  const [bankSearch, setBankSearch] = useState<string>('');
  const [allBankQuestions, setAllBankQuestions] = useState<any[]>([]);
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
      const items = (s?.items || []).filter((it: any) => it.key !== 'review.approval_mode');
      setSettingsList(items);
      const map: Record<string, string> = {};
      items.forEach((it: any) => {
        map[it.key] = typeof it.value === 'string' ? it.value : JSON.stringify(it.value);
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
      } else if (selectedDraft) {
        const updatedRow = list.find((d: any) => d.draft_id === selectedDraft.draft_id);
        if (updatedRow && updatedRow.status !== selectedDraft.status) {
          inspectDraft(updatedRow.draft_id);
        }
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

  const loadReadyQuestions = async () => {
    try {
      const res = await getAdminQuestions({
        status: 'ready',
        page_size: 100,
      });
      setReadyQuestions(res?.items || []);
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
      const draftList = list.filter((g: any) => g.status === 'draft');
      const targetId =
        (preferGroupId && draftList.some((g: any) => g.group_id === preferGroupId)
          ? preferGroupId
          : null) ??
        (selectedGroupId && draftList.some((g: any) => g.group_id === selectedGroupId)
          ? selectedGroupId
          : draftList[0]?.group_id ?? null);
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

  const loadUsers = async (queryOverride?: string) => {
    try {
      const qVal = (queryOverride !== undefined ? queryOverride : userSearch).trim();
      const u = await getAdminUsers({ page_size: 100, q: qVal || undefined });
      setUsers(u?.items || []);
    } catch {}
  };

  const inspectUser = async (userId: number) => {
    const reqId = ++userDetailReqRef.current;
    setLoadingUserDetail(true);
    setErr(null);
    try {
      const d = await getAdminUserDetail(userId);
      if (reqId === userDetailReqRef.current) {
        setSelectedUserDetail(d);
      }
    } catch (e: any) {
      if (reqId === userDetailReqRef.current) {
        setErr(extractApiError(e, 'Không tải được thông tin chi tiết người dùng'));
      }
    } finally {
      if (reqId === userDetailReqRef.current) {
        setLoadingUserDetail(false);
      }
    }
  };

  useEffect(() => {
    if (!selectedUserDetail && !loadingUserDetail) return;
    const onKeyDown = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') {
        userDetailReqRef.current += 1;
        setLoadingUserDetail(false);
        setSelectedUserDetail(null);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedUserDetail, loadingUserDetail]);

  useEffect(() => {
    if (!isAdmin) return;
    loadUsers();
    loadSkillsAndSchema();
    loadSettings();
    loadDrafts();
    loadJobs();
    loadGroups();
    loadReadyQuestions();
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    if (activeTab === 'users') loadUsers();
    if (activeTab === 'generate') {
      loadJobs();
      loadDrafts();
    }
    if (activeTab === 'drafts') {
      loadDrafts();
    }
    if (activeTab === 'weekly') {
      loadDrafts();
      loadReadyQuestions();
      loadGroups();
      loadWeekly();
    }
    if (activeTab === 'bank') loadAllBankQuestions();
    if (activeTab === 'settings') loadSettings();
  }, [activeTab, allBankStatusFilter, isAdmin]);

  // Real-time 2s polling whenever ANY job is queued/running OR ANY draft is pending/reviewing!
  const activeRunningJob = jobs.find(
    (j: any) => j.status === 'queued' || j.status === 'running'
  );
  const hasReviewingDrafts = drafts.some(
    (d: any) => d.status === 'pending' || d.status === 'reviewing'
  );
  const shouldPollPipeline = Boolean(activeRunningJob || hasReviewingDrafts);
  const isGenerating = Boolean(submittingJob || activeRunningJob);

  useEffect(() => {
    if (!isAdmin || !shouldPollPipeline) {
      setElapsedSec(0);
      return;
    }
    const updateElapsed = () => {
      const refTime =
        activeRunningJob?.started_at ||
        activeRunningJob?.created_at ||
        drafts.find((d: any) => d.status === 'pending' || d.status === 'reviewing')?.created_at ||
        Date.now();
      const startMs = new Date(refTime).getTime();
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
  }, [shouldPollPipeline, activeRunningJob?.job_id, activeRunningJob?.status, isAdmin]);

  if (!isAdmin) {
    return (
      <div className="bg-surface border border-line rounded-xl p-8 text-center space-y-3">
        <div className="inline-flex items-center justify-center w-11 h-11 rounded-full badge-medium">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="text-base font-bold text-ink">
          Cổng Quản trị yêu cầu tài khoản Quản trị viên
        </div>
      </div>
    );
  }

  // Gateway Key Handler
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
        `Đã kết nối API Thật (apithat.dev) thành công (${info.masked_key}) · ${info.preferred_model}`
      );
      await loadJobs();
    } catch (e: any) {
      setErr(extractApiError(e, 'Không xác thực được khóa API trên apithat.dev'));
    } finally {
      setSavingGatewayKey(false);
    }
  };

  // Ordered selected skills & per-skill quantities
  const sortedSelectedSkills = skillOptions.filter((sk) => jobSkills.includes(sk.id));
  const skillQuantitiesPayload = sortedSelectedSkills.map((sk) => ({
    skill_id: sk.id,
    quantity: Math.max(1, Math.min(10, Number(skillQuantities[sk.id] || 1))),
  }));
  const totalRequestedCount = skillQuantitiesPayload.reduce((acc, item) => acc + item.quantity, 0);

  const toggleJobSkill = (skillId: number) => {
    setJobSkills((prev) => {
      if (prev.includes(skillId)) {
        if (prev.length <= 1) return prev; // Always keep at least 1 selected skill
        return prev.filter((id) => id !== skillId);
      }
      setSkillQuantities((qMap) => ({ ...qMap, [skillId]: qMap[skillId] || 1 }));
      return [...prev, skillId];
    });
  };

  // Create AI Generation Job with skill_quantities
  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating || skillQuantitiesPayload.length === 0) return;
    setMsg(null);
    setErr(null);
    setSubmittingJob(true);
    const chosenTopic =
      jobTopic.trim() || TOPIC_PRESETS[Math.floor(Math.random() * TOPIC_PRESETS.length)];
    try {
      const job = await createGenerationJob({
        difficulty: jobDiff,
        skill_ids: skillQuantitiesPayload.map((item) => item.skill_id),
        skill_quantities: skillQuantitiesPayload,
        requested_count: totalRequestedCount,
        quantity: totalRequestedCount,
        topic: chosenTopic,
        auto_run: true,
      });
      setMsg(
        job.status === 'done'
          ? `Đã sinh xong ${job.created_count}/${job.requested_count} câu hỏi mới.`
          : `Đã khởi tạo tiến trình sinh ${job.requested_count} câu hỏi AI.`
      );
      await Promise.all([loadJobs(), loadDrafts(), loadReadyQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tạo được tiến trình sinh đề AI'));
    } finally {
      setSubmittingJob(false);
    }
  };

  // Manual Question Creation
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
      setMsg(
        `Đã kiểm tra trên Sandbox PostgreSQL 17 và lưu câu hỏi #${created.question_id} (${created.row_count} dòng kết quả) vào mục Chưa có trên kệ.`
      );
      setManualTitle('');
      setManualQuestion('');
      await Promise.all([loadReadyQuestions(), loadAllBankQuestions()]);
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

  // Draft Review Handlers
  const filteredDrafts = drafts.filter((d) => {
    if (draftStatusFilter && d.status !== draftStatusFilter) return false;
    const stText = formatDraftStatusBadge(d.status).text;
    const diffText = DIFF_LABELS[d.difficulty]?.text || `Mức ${d.difficulty}`;
    return matchesVisibleRecord(draftSearch, `#${d.draft_id}`, diffText, stText, d.title);
  });

  const visibleUsers = users.filter((u) =>
    matchesVisibleRecord(
      userSearch,
      `#${u.user_id}`,
      u.display_name || u.username,
      `@${u.username}`,
      u.email,
      u.role === 'admin' ? 'Admin' : 'Học viên',
      u.status === 'active' ? 'Hoạt động' : 'Đã khóa'
    )
  );

  const visibleBankQuestions = allBankQuestions.filter((q) =>
    matchesVisibleRecord(
      bankSearch,
      `#${q.question_id}`,
      q.title,
      q.tables_used,
      DIFF_LABELS[q.difficulty]?.text,
      q.status,
      q.in_published_set ? 'Đang mở trên kệ' : ''
    )
  );

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
    setCheckedDraftIds(allSelected ? [] : targetIds);
  };

  const handleBulkApprove = async () => {
    const approvable = checkedDraftIds.filter((id) => {
      const found = drafts.find((d) => d.draft_id === id);
      return found && found.status !== 'approved';
    });
    if (approvable.length === 0) {
      setErr('Các bản nháp đã chọn đều đang ở trạng thái Đã duyệt.');
      return;
    }
    setBulkBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await bulkApproveAdminDrafts(approvable, 'Phê duyệt hàng loạt bởi Quản trị viên');
      setMsg(`Đã phê duyệt thành công ${res.approved_count ?? approvable.length} bản nháp.`);
      setCheckedDraftIds([]);
      await Promise.all([loadDrafts(), loadReadyQuestions(), loadWeekly()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Duyệt hàng loạt không thành công'));
    } finally {
      setBulkBusy(false);
    }
  };

  const handleSaveDraftContent = async () => {
    if (!selectedDraft) return;
    setDraftActionBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const d = await editAdminDraft(selectedDraft.draft_id, {
        title: editTitle.trim(),
        question: editQuestion.trim(),
        note: reviewNote || 'Cập nhật nội dung đề bài',
      });
      setSelectedDraft(d);
      setMsg(`Đã lưu nội dung bản nháp #${d.draft_id}.`);
      await loadDrafts();
    } catch (e: any) {
      setErr(extractApiError(e, 'Lưu nội dung bản nháp không thành công'));
    } finally {
      setDraftActionBusy(false);
    }
  };

  const handleApproveSingleDraft = async () => {
    if (!selectedDraft) return;
    setDraftActionBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const payload: { selected_run_id?: number; custom_sql?: string; note?: string } = {
        note: reviewNote || 'Quản trị viên phê duyệt',
      };
      if (sqlSourceChoice === 'custom') {
        payload.custom_sql = customSqlText.trim();
      } else if (typeof sqlSourceChoice === 'number') {
        payload.selected_run_id = sqlSourceChoice;
      } else if (
        customSqlText.trim() &&
        customSqlText.trim() !== (selectedDraft.reference_sql || '').trim()
      ) {
        payload.custom_sql = customSqlText.trim();
      }
      const d = await approveAdminDraft(selectedDraft.draft_id, payload);
      setSelectedDraft(d);
      setMsg(
        `Đã phê duyệt bản nháp #${d.draft_id}. Câu hỏi đã vào mục Chưa có trên kệ trong Bộ đề tuần.`
      );
      await Promise.all([loadDrafts(), loadReadyQuestions(), loadAllBankQuestions(), loadWeekly()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể phê duyệt bản nháp này. Kiểm tra lại câu SQL đáp án.'));
    } finally {
      setDraftActionBusy(false);
    }
  };

  const handleReturnNeedsHuman = async () => {
    if (!selectedDraft) return;
    setDraftActionBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const d = await returnAdminDraftNeedsHuman(
        selectedDraft.draft_id,
        reviewNote || 'Chuyển về trạng thái Cần duyệt bởi Quản trị viên'
      );
      setSelectedDraft(d);
      setMsg(
        `Đã gỡ câu hỏi của bản nháp #${d.draft_id} khỏi Web Học Viên và chuyển về trạng thái Cần duyệt (needs_human).`
      );
      await Promise.all([loadDrafts(), loadReadyQuestions(), loadAllBankQuestions(), loadWeekly()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể chuyển bản nháp về trạng thái Cần duyệt'));
    } finally {
      setDraftActionBusy(false);
    }
  };

  const handleRejectDraft = async () => {
    if (!selectedDraft) return;
    setDraftActionBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const d = await rejectAdminDraft(
        selectedDraft.draft_id,
        reviewNote.trim().length >= 3 ? reviewNote.trim() : 'Từ chối bản nháp bởi Quản trị viên'
      );
      setSelectedDraft(d);
      setMsg(`Đã từ chối bản nháp #${d.draft_id} và gỡ khỏi danh sách mở.`);
      await Promise.all([loadDrafts(), loadReadyQuestions(), loadAllBankQuestions(), loadWeekly()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể từ chối bản nháp'));
    } finally {
      setDraftActionBusy(false);
    }
  };

  // Build Unfiltered Approved Pool first so KPI cards never zero out under difficulty/search filters
  const rawApprovedPool: (UnifiedApprovedItem & { weekly_position: number })[] = (() => {
    const items: (UnifiedApprovedItem & { weekly_position: number })[] = [];
    const seenQuestionIds = new Set<number>();
    const seenDraftIds = new Set<number>();

    readyQuestions.forEach((q: any) => {
      const qid = Number(q.question_id);
      const wpos = Number(q.weekly_position || 0);
      seenQuestionIds.add(qid);
      if (q.source_draft_id) seenDraftIds.add(Number(q.source_draft_id));
      items.push({
        key: `q-${qid}`,
        question_id: qid,
        draft_id: q.source_draft_id ? Number(q.source_draft_id) : null,
        title: q.title,
        difficulty: Number(q.difficulty || 1),
        tables_used: Array.isArray(q.tables_used) ? q.tables_used : [],
        in_published_set: Boolean(q.in_published_set),
        weekly_position: wpos,
      });
    });

    drafts
      .filter((d: any) => d.status === 'approved')
      .forEach((d: any) => {
        const did = Number(d.draft_id);
        const promotedQid = Number(
          d.live_question_id ?? d.promoted_question_id ?? d.promoted_question?.question_id ?? 0
        );
        if (seenDraftIds.has(did) || (promotedQid && seenQuestionIds.has(promotedQid))) {
          return;
        }
        // If already promoted to a live question that isn't in readyQuestions (e.g. retired), skip
        if (promotedQid) {
          return;
        }
        items.push({
          key: `d-${did}`,
          question_id: null,
          draft_id: did,
          title: d.title || `Bản nháp #${did}`,
          difficulty: Number(d.difficulty || 1),
          tables_used: Array.isArray(d.tables_used) ? d.tables_used : [],
          in_published_set: Boolean(d.weekly_position),
          weekly_position: Number(d.weekly_position || 0),
        });
      });

    return items;
  })();

  const rawUnassignedPool = rawApprovedPool.filter((it) => !it.in_published_set);
  const rawOnShelfPool = rawApprovedPool.filter((it) => it.in_published_set);

  const filterPoolItems = (list: typeof rawApprovedPool): UnifiedApprovedItem[] => {
    return list.filter((it) => {
      if (approvedDiffFilter !== undefined && it.difficulty !== approvedDiffFilter) {
        return false;
      }
      const visibleCode = it.question_id ? `#${it.question_id}` : `Nháp #${it.draft_id}`;
      const visibleTables = Array.isArray(it.tables_used) ? it.tables_used.slice(0, 2) : [];
      return matchesVisibleRecord(
        approvedSearch,
        visibleCode,
        it.title,
        visibleTables,
        DIFF_LABELS[it.difficulty]?.text,
        'Approved',
        it.in_published_set ? 'Đang trên kệ' : ''
      );
    });
  };

  const allApprovedPool = rawApprovedPool;
  const unassignedApprovedPool = filterPoolItems(rawUnassignedPool);
  const onShelfApprovedPool = filterPoolItems(rawOnShelfPool);
  const unifiedApprovedPool =
    approvedShelfTab === 'on_shelf' ? onShelfApprovedPool : unassignedApprovedPool;
  const draftGroups = groups.filter((g: any) => g.status === 'draft');

  const groupItems = (groupDetail?.items || []).map(normalizeGroupItem);
  const groupItemIdSet = new Set(groupItems.map((it: any) => it.question_id));
  const isSelectedGroupEditable = groupDetail?.status === 'draft';

  const splitKeysToIds = (keys: string[]) => {
    const question_ids: number[] = [];
    const draft_ids: number[] = [];
    keys.forEach((k) => {
      const found = allApprovedPool.find((x) => x.key === k);
      if (found) {
        if (found.question_id) question_ids.push(found.question_id);
        else if (found.draft_id) draft_ids.push(found.draft_id);
      } else if (k.startsWith('q-')) {
        const n = Number(k.slice(2));
        if (n) question_ids.push(n);
      } else if (k.startsWith('d-')) {
        const n = Number(k.slice(2));
        if (n) draft_ids.push(n);
      }
    });
    return { question_ids, draft_ids };
  };

  const ensureEditableGroupId = async (seedPayload?: {
    question_ids?: number[];
    draft_ids?: number[];
  }): Promise<number | null> => {
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
      question_ids: seedPayload?.question_ids || [],
      draft_ids: seedPayload?.draft_ids || [],
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
      const { question_ids, draft_ids } = splitKeysToIds(pickedApprovedKeys);
      const created = await createAdminQuestionGroup({
        name: cleanName,
        question_ids,
        draft_ids,
      });
      setNewGroupName('');
      setPublishSetTitle(cleanName);
      setPickedApprovedKeys([]);
      await Promise.all([loadGroups(created.group_id), loadReadyQuestions(), loadDrafts()]);
      setMsg(`Đã tạo nhóm "${created.name}" (${created.question_count ?? 0} câu).`);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể tạo nhóm đề mới'));
    } finally {
      setCreatingGroup(false);
    }
  };

  const handleAddApprovedKeysToGroup = async (keys: string[]) => {
    if (!keys.length) return;
    const { question_ids, draft_ids } = splitKeysToIds(keys);
    if (!question_ids.length && !draft_ids.length) return;
    setGroupBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const typedName = newGroupName.trim();
      if (typedName) {
        const created = await createAdminQuestionGroup({
          name: typedName,
          question_ids,
          draft_ids,
        });
        setNewGroupName('');
        setPublishSetTitle(typedName);
        setPickedApprovedKeys((prev) => prev.filter((k) => !keys.includes(k)));
        await Promise.all([loadGroups(created.group_id), loadReadyQuestions(), loadDrafts(), loadWeekly()]);
        setMsg(`Đã tạo đợt đề "${created.name}" và thêm ${created.question_count ?? 1} câu hỏi.`);
        return;
      }
      if (!selectedGroupId || groupDetail?.status !== 'draft') {
        const existingDraft = groups.find((g) => g.status === 'draft');
        if (!existingDraft) {
          const autoName = `Đợt bài tập SQL (${new Date().toLocaleDateString('vi-VN')})`;
          const created = await createAdminQuestionGroup({
            name: autoName,
            question_ids,
            draft_ids,
          });
          setPublishSetTitle(autoName);
          setPickedApprovedKeys((prev) => prev.filter((k) => !keys.includes(k)));
          await Promise.all([loadGroups(created.group_id), loadReadyQuestions(), loadDrafts(), loadWeekly()]);
          setMsg(`Đã tạo "${created.name}" và thêm câu hỏi Approved.`);
          return;
        }
      }
      const gid = await ensureEditableGroupId();
      if (!gid) return;
      const updated = await addAdminQuestionGroupItems(gid, { question_ids, draft_ids });
      setGroupDetail(updated);
      setPickedApprovedKeys((prev) => prev.filter((k) => !keys.includes(k)));
      await Promise.all([loadGroups(gid), loadReadyQuestions(), loadDrafts(), loadWeekly()]);
      setMsg(`Đã thêm câu hỏi vào "${updated.name}" (${updated.question_count ?? 0} câu).`);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể thêm câu hỏi vào nhóm'));
    } finally {
      setGroupBusy(false);
    }
  };

  const handleAddPickedToDraftWeeklySet = async () => {
    if (!weeklySetDetail || weeklySetDetail.status !== 'draft' || pickedApprovedKeys.length === 0) {
      return;
    }
    const { question_ids } = splitKeysToIds(pickedApprovedKeys);
    if (question_ids.length === 0) {
      setErr('Hãy gom qua Nhóm đề bên cạnh để hệ thống tự kích hoạt bản nháp thành câu hỏi.');
      return;
    }
    setGroupBusy(true);
    setErr(null);
    try {
      const existingIds = (weeklySetDetail.items || []).map((it: any) =>
        Number(it?.question?.question_id ?? it?.question_id)
      );
      const merged = Array.from(new Set([...existingIds, ...question_ids]));
      await updateAdminWeeklySetItems(weeklySetDetail.set_id, merged);
      setPickedApprovedKeys([]);
      await inspectWeeklySet(weeklySetDetail.set_id);
      setMsg(`Đã thêm câu hỏi Approved vào Bộ đề tuần nháp #${weeklySetDetail.set_id}.`);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể cập nhật câu hỏi cho bộ đề tuần nháp'));
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
      await Promise.all([loadGroups(selectedGroupId), loadReadyQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Cập nhật danh sách câu trong nhóm không thành công'));
    } finally {
      setGroupBusy(false);
    }
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
      await Promise.all([loadGroups(), loadReadyQuestions()]);
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
      setMsg(
        `Đã đăng toàn bộ ${res.published_count ?? groupItems.length} câu hỏi lên kệ "${
          res.set_title || 'Bộ đề hiện hành'
        }". Bộ đề đã chuyển xuống Danh sách Bộ đề tuần bên dưới.`
      );
      setSelectedGroupId(null);
      setGroupDetail(null);
      setPublishSetTitle('');
      await Promise.all([loadGroups(), loadReadyQuestions(), loadWeekly()]);
      if (res?.set_id) {
        await inspectWeeklySet(Number(res.set_id));
      }
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

  const handleRemoveFromWeeklySet = async (setId: number, removeQid: number) => {
    setErr(null);
    setMsg(null);
    try {
      await removeAdminWeeklySetItem(setId, removeQid);
      setMsg(`Đã gỡ câu hỏi #${removeQid} khỏi Bộ đề tuần #${setId} và đánh lại thứ tự SQL.`);
      await Promise.all([inspectWeeklySet(setId), loadWeekly(), loadReadyQuestions()]);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể gỡ câu hỏi khỏi bộ đề tuần này'));
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
      await loadUsers();
      if (selectedUserDetail && selectedUserDetail.user_id === u.user_id) {
        await inspectUser(u.user_id);
      }
    } catch (e: any) {
      setErr(extractApiError(e, 'Không thể cập nhật tài khoản'));
    }
  };

  const jobTopicById = new Map<number, string>();
  jobs.forEach((j: any) => {
    if (j.job_id && j.topic) jobTopicById.set(Number(j.job_id), String(j.topic));
  });

  const pendingDraftCount = drafts.filter((d) => d.status === 'needs_human').length;
  const hasDraftTextEdited =
    selectedDraft &&
    (editTitle.trim() !== String(selectedDraft.title || '').trim() ||
      editQuestion.trim() !== String(selectedDraft.question || '').trim());

  const adminNavTabs: {
    id: AdminTabId;
    label: string;
    icon: typeof Users;
    badge?: string | null;
  }[] = [
    { id: 'users', label: 'Người dùng', icon: Users },
    { id: 'generate', label: 'Sinh đề AI', icon: Sparkles },
    {
      id: 'drafts',
      label: 'Duyệt đề',
      icon: CheckCircle2,
      badge: pendingDraftCount > 0 ? String(pendingDraftCount) : null,
    },
    {
      id: 'weekly',
      label: 'Bộ đề tuần',
      icon: CalendarRange,
      badge: unassignedApprovedPool.length > 0 ? String(unassignedApprovedPool.length) : null,
    },
    { id: 'bank', label: 'Ngân hàng đề', icon: Database },
    { id: 'settings', label: 'Cấu hình', icon: Settings },
  ];

  return (
    <div className="space-y-4">
      {/* Clean Flat Top Navigation Bar — 'Người dùng' First & Default */}
      <div className="bg-surface border border-line rounded-xl p-2 flex flex-wrap items-center gap-1.5">
        {adminNavTabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              data-solid-btn={active ? 'true' : undefined}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-2 whitespace-nowrap ${
                active ? 'btn-primary' : 'btn-secondary'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.badge && (
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-semibold tabular-nums ${
                    active ? 'bg-surface text-ink' : 'badge-info'
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Feedback Banners */}
      {(err || msg) && (
        <div role="status" className="space-y-2">
          {err && (
            <div className="p-3.5 rounded-xl badge-hard text-sm flex items-center justify-between gap-3">
              <p>{err}</p>
              <button
                type="button"
                onClick={() => setErr(null)}
                className="btn-secondary px-3 min-h-8 rounded-md text-xs font-semibold shrink-0 whitespace-nowrap"
              >
                Đóng
              </button>
            </div>
          )}
          {msg && (
            <div className="p-3.5 rounded-xl badge-easy text-sm flex items-center justify-between gap-3">
              <p>{msg}</p>
              <button
                type="button"
                onClick={() => setMsg(null)}
                className="btn-secondary px-3 min-h-8 rounded-md text-xs font-semibold shrink-0 whitespace-nowrap"
              >
                Đóng
              </button>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          TAB 1 (DEFAULT): NGƯỜI DÙNG
      ===================================================================== */}
      {activeTab === 'users' && (
        <div className="bg-surface border border-line rounded-xl overflow-hidden">
          <div className="px-5 py-4 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-bold text-ink">
              Quản lý Người dùng &amp; Phân quyền ({visibleUsers.length}/{users.length})
            </h2>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-4 h-4 text-muted absolute left-3 top-3" />
                <input
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadUsers(userSearch)}
                  placeholder="Lọc ID, tên, tài khoản, email, vai trò…"
                  className="pl-9 pr-3 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                />
              </div>
              {userSearch && (
                <button
                  type="button"
                  onClick={() => {
                    setUserSearch('');
                    loadUsers('');
                  }}
                  className="btn-secondary px-3 min-h-10 rounded-lg text-xs font-semibold whitespace-nowrap"
                >
                  Xóa lọc
                </button>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm tabular-nums">
              <thead>
                <tr className="bg-canvas border-b border-line text-text2 font-semibold">
                  <th className="py-3 px-4 w-20">ID</th>
                  <th className="py-3 px-4">Tài khoản</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4 w-32">Vai trò</th>
                  <th className="py-3 px-4 w-36">Trạng thái</th>
                  <th className="py-3 px-4 w-60">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {visibleUsers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-sm text-muted">
                      Không tìm thấy tài khoản người dùng phù hợp.
                    </td>
                  </tr>
                ) : (
                  visibleUsers.map((u) => (
                    <tr
                      key={u.user_id}
                      onClick={() => inspectUser(u.user_id)}
                      className="hover:bg-soft cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 text-muted">
                        <code>#{u.user_id}</code>
                      </td>
                      <td className="py-3 px-4 font-semibold text-ink">
                        <span className="underline decoration-dotted underline-offset-4 hover:text-brand">
                          {u.display_name || u.username}
                        </span>{' '}
                        <span className="text-muted font-normal">(@{u.username})</span>
                      </td>
                      <td className="py-3 px-4 text-text2">{u.email}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                            u.role === 'admin' ? 'badge-medium' : 'badge-info'
                          }`}
                        >
                          {u.role === 'admin' ? 'Admin' : 'Học viên'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                            u.status === 'active' ? 'badge-easy' : 'badge-hard'
                          }`}
                        >
                          {u.status === 'active' ? 'Hoạt động' : 'Đã khóa'}
                        </span>
                      </td>
                      <td
                        className="py-3 px-4 flex flex-wrap gap-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={() => inspectUser(u.user_id)}
                          className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                        >
                          Chi tiết
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleUser(u, 'role')}
                          className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                        >
                          Đổi vai trò
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleUser(u, 'status')}
                          className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                        >
                          {u.status === 'active' ? 'Khóa tài khoản' : 'Mở khóa'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {(loadingUserDetail || selectedUserDetail) && (
            <div
              role="dialog"
              aria-modal="true"
              aria-label="Thông tin chi tiết tài khoản"
              onClick={() => !loadingUserDetail && setSelectedUserDetail(null)}
              className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
            >
              <div
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-3xl max-h-[88vh] overflow-y-auto bg-surface border border-line rounded-2xl"
              >
                <div className="px-5 py-4 bg-soft border-b border-line flex items-center justify-between gap-3 sticky top-0 z-10">
                  <div>
                    <h3 className="text-base font-bold text-ink">
                      {loadingUserDetail && !selectedUserDetail
                        ? 'Đang tải thông tin tài khoản…'
                        : `Hồ sơ tài khoản #${selectedUserDetail?.user_id} · ${
                            selectedUserDetail?.display_name || selectedUserDetail?.username
                          }`}
                    </h3>
                    {selectedUserDetail && (
                      <p className="text-xs text-muted">
                        @{selectedUserDetail.username} · {selectedUserDetail.email}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedUserDetail(null)}
                    aria-label="Đóng thông tin tài khoản"
                    className="btn-secondary min-w-9 min-h-9 rounded-lg flex items-center justify-center"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {selectedUserDetail && (
                  <div className="p-5 space-y-5">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                      <div className="p-3 rounded-xl bg-canvas border border-line space-y-1">
                        <div className="text-xs text-muted">Tên hiển thị &amp; Định danh</div>
                        <div className="font-semibold text-ink">
                          {selectedUserDetail.display_name || selectedUserDetail.username}{' '}
                          <span className="text-muted font-normal">
                            (@{selectedUserDetail.username})
                          </span>
                        </div>
                        <div className="text-xs text-text2">{selectedUserDetail.email}</div>
                      </div>

                      <div className="p-3 rounded-xl bg-canvas border border-line space-y-1.5">
                        <div className="text-xs text-muted">Phân quyền &amp; Trạng thái</div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                              selectedUserDetail.role === 'admin' ? 'badge-medium' : 'badge-info'
                            }`}
                          >
                            {selectedUserDetail.role === 'admin' ? 'Quản trị viên (Admin)' : 'Học viên'}
                          </span>
                          <span
                            className={`px-2.5 py-0.5 rounded-md text-xs font-semibold ${
                              selectedUserDetail.status === 'active' ? 'badge-easy' : 'badge-hard'
                            }`}
                          >
                            {selectedUserDetail.status === 'active' ? 'Đang hoạt động' : 'Đã khóa'}
                          </span>
                        </div>
                        <div className="text-xs text-muted tabular-nums">
                          Tạo ngày:{' '}
                          {selectedUserDetail.created_at
                            ? new Date(selectedUserDetail.created_at).toLocaleString('vi-VN')
                            : '—'}
                          {' · '}Đăng nhập gần nhất:{' '}
                          {selectedUserDetail.last_login_at
                            ? new Date(selectedUserDetail.last_login_at).toLocaleString('vi-VN')
                            : 'Chưa ghi nhận'}
                        </div>
                      </div>
                    </div>

                    {selectedUserDetail.bio && (
                      <div className="p-3 rounded-xl bg-canvas border border-line text-sm text-text2">
                        <span className="font-semibold text-ink">Giới thiệu: </span>
                        {selectedUserDetail.bio}
                      </div>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 tabular-nums">
                      <div className="p-3 rounded-xl bg-soft border border-line">
                        <div className="text-xs text-muted">Câu đã giải đúng</div>
                        <div className="text-lg font-bold text-brand mt-0.5">
                          {selectedUserDetail.stats?.solved_questions ?? 0}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-soft border border-line">
                        <div className="text-xs text-muted">Tổng lượt nộp</div>
                        <div className="text-lg font-bold text-ink mt-0.5">
                          {selectedUserDetail.stats?.total_submissions ?? 0}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-soft border border-line">
                        <div className="text-xs text-muted">Lượt nộp Đạt / Chưa đạt</div>
                        <div className="text-lg font-bold text-ink mt-0.5">
                          {selectedUserDetail.stats?.passed_submissions ?? 0} /{' '}
                          {selectedUserDetail.stats?.failed_submissions ?? 0}
                        </div>
                      </div>
                      <div className="p-3 rounded-xl bg-soft border border-line">
                        <div className="text-xs text-muted">Tỷ lệ chính xác</div>
                        <div className="text-lg font-bold text-ink mt-0.5">
                          {selectedUserDetail.stats?.accuracy_percent ?? 0}%
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                      <h4 className="text-sm font-bold text-ink">
                        Lịch sử nộp bài gần đây ({selectedUserDetail.recent_submissions?.length ?? 0})
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => handleToggleUser(selectedUserDetail, 'role')}
                          className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                        >
                          Đổi sang {selectedUserDetail.role === 'admin' ? 'Học viên' : 'Admin'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleUser(selectedUserDetail, 'status')}
                          className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                        >
                          {selectedUserDetail.status === 'active' ? 'Khóa tài khoản' : 'Mở khóa'}
                        </button>
                      </div>
                    </div>

                    {!selectedUserDetail.recent_submissions ||
                    selectedUserDetail.recent_submissions.length === 0 ? (
                      <div className="p-6 rounded-xl bg-canvas border border-line text-center text-sm text-muted">
                        Tài khoản này chưa có lượt nộp bài nào.
                      </div>
                    ) : (
                      <div className="border border-line rounded-xl overflow-hidden overflow-x-auto">
                        <table className="w-full text-left border-collapse text-xs tabular-nums">
                          <thead>
                            <tr className="bg-canvas border-b border-line text-text2 font-semibold">
                              <th className="py-2.5 px-3">Mã nộp</th>
                              <th className="py-2.5 px-3">Câu hỏi</th>
                              <th className="py-2.5 px-3">Kết quả</th>
                              <th className="py-2.5 px-3">Thời gian chạy</th>
                              <th className="py-2.5 px-3">Thời điểm</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-line">
                            {selectedUserDetail.recent_submissions.map((sub: any) => (
                              <tr key={sub.submission_id} className="hover:bg-canvas">
                                <td className="py-2 px-3 text-muted">
                                  <code>#{sub.submission_id}</code>
                                </td>
                                <td className="py-2 px-3 font-medium text-ink">
                                  #{sub.question_id} · {sub.question_title || 'Câu hỏi SQL'}
                                </td>
                                <td className="py-2 px-3">
                                  <span
                                    className={`px-2 py-0.5 rounded font-semibold ${
                                      sub.submission_status === 'passed'
                                        ? 'badge-easy'
                                        : 'badge-hard'
                                    }`}
                                  >
                                    {sub.submission_status === 'passed'
                                      ? 'Làm được'
                                      : 'Chưa làm được'}
                                  </span>
                                </td>
                                <td className="py-2 px-3 text-text2">
                                  {sub.runtime_ms != null ? `${sub.runtime_ms} ms` : '—'}
                                </td>
                                <td className="py-2 px-3 text-muted">
                                  {sub.submitted_at
                                    ? new Date(sub.submitted_at).toLocaleString('vi-VN')
                                    : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          TAB 2: SINH ĐỀ AI
      ===================================================================== */}
      {activeTab === 'generate' && (
        <div className="space-y-4">
          <div className="bg-surface border border-line rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                data-solid-btn={createMode === 'ai' ? 'true' : undefined}
                onClick={() => setCreateMode('ai')}
                className={`px-4 min-h-9 rounded-lg text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap ${
                  createMode === 'ai' ? 'btn-primary' : 'btn-secondary'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Sinh đề AI</span>
              </button>
              <button
                type="button"
                data-solid-btn={createMode === 'manual' ? 'true' : undefined}
                onClick={() => setCreateMode('manual')}
                className={`px-4 min-h-9 rounded-lg text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap ${
                  createMode === 'manual' ? 'btn-primary' : 'btn-secondary'
                }`}
              >
                <FilePlus2 className="w-3.5 h-3.5" />
                <span>Soạn đề thủ công</span>
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {gatewayStatus?.valid ? (
                <span className="badge-easy px-2.5 py-1 rounded-full text-xs font-semibold">
                  API Thật (apithat.dev): {gatewayStatus.masked_key}
                </span>
              ) : (
                <span className="badge-medium px-2.5 py-1 rounded-full text-xs font-semibold">
                  API Thật (apithat.dev): Chưa kết nối khóa
                </span>
              )}
              <button
                type="button"
                onClick={() => setShowGatewayForm((v) => !v)}
                className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
              >
                {showGatewayForm ? 'Ẩn cấu hình khóa' : 'Cập nhật khóa API Thật'}
              </button>
            </div>
          </div>

          {showGatewayForm && (
            <form
              onSubmit={handleSaveGatewayKey}
              className="bg-surface border border-line rounded-xl p-4 grid grid-cols-1 md:grid-cols-12 gap-3 items-end"
            >
              <div className="md:col-span-6">
                <label className="block text-xs font-semibold text-ink mb-1">
                  Khóa API Thật (apithat.dev/keys)
                </label>
                <input
                  type="password"
                  autoComplete="off"
                  value={gatewayKeyInput}
                  onChange={(e) => setGatewayKeyInput(e.target.value)}
                  placeholder="sk-…"
                  className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink font-mono"
                />
              </div>
              <div className="md:col-span-3">
                <label className="block text-xs font-semibold text-ink mb-1">
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
                  {savingGatewayKey ? 'Đang xác thực…' : 'Lưu & Kích hoạt'}
                </button>
              </div>
            </form>
          )}

          {createMode === 'ai' ? (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              {/* Left Column: Clean AI Generation Form (No Redundant Prose, Per-Skill Quantities) */}
              <form
                onSubmit={handleCreateJob}
                className="lg:col-span-5 bg-surface border border-line rounded-xl p-5 space-y-4"
              >
                <div className="border-b border-line pb-2.5 flex items-center justify-between">
                  <h2 className="text-base font-bold text-ink">Tạo đề AI</h2>
                  <span className="text-xs font-semibold text-brand tabular-nums">
                    Tổng: {totalRequestedCount} câu
                  </span>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">
                    Chủ đề nghiệp vụ
                  </label>
                  <input
                    value={jobTopic}
                    onChange={(e) => setJobTopic(e.target.value)}
                    placeholder="Nhập chủ đề hoặc chọn nhanh bên dưới…"
                    className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink placeholder:text-muted"
                  />
                  <div className="mt-2 flex flex-wrap gap-1.5">
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
                  <label className="block text-sm font-semibold text-ink mb-1">
                    Độ khó
                  </label>
                  <select
                    value={jobDiff}
                    onChange={(e) => setJobDiff(Number(e.target.value))}
                    className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  >
                    <option value={1}>Mức 1: Dễ</option>
                    <option value={2}>Mức 2: Trung bình</option>
                    <option value={3}>Mức 3: Khó</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">
                    Kỹ năng SQL (S1–S6)
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {skillOptions.map((sk) => {
                      const active = jobSkills.includes(sk.id);
                      return (
                        <button
                          type="button"
                          key={sk.id}
                          data-solid-btn={active ? 'true' : undefined}
                          onClick={() => toggleJobSkill(sk.id)}
                          className={`px-3 min-h-9 rounded-lg text-left text-xs font-semibold ${
                            active ? 'btn-primary' : 'btn-secondary'
                          }`}
                        >
                          {sk.code} · {sk.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Per-Skill Question Quantity Rows */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold text-ink">
                      Số lượng câu hỏi theo từng kỹ năng
                    </label>
                    <span className="text-xs text-muted tabular-nums">
                      {sortedSelectedSkills.length} kỹ năng đã chọn
                    </span>
                  </div>

                  <div className="rounded-xl border border-line bg-canvas divide-y divide-line overflow-hidden">
                    {sortedSelectedSkills.map((sk) => {
                      const qty = skillQuantities[sk.id] ?? 1;
                      return (
                        <div
                          key={sk.id}
                          className="px-3.5 py-2.5 flex items-center justify-between gap-3"
                        >
                          <span className="text-sm font-medium text-ink">
                            <code className="text-xs font-bold text-brand mr-1.5">
                              {sk.code}
                            </code>
                            · {sk.name}
                          </span>
                          <input
                            type="number"
                            min={1}
                            max={10}
                            aria-label={`Số lượng câu hỏi cho ${sk.code}`}
                            value={qty}
                            onChange={(e) => {
                              const val = Math.max(1, Math.min(10, Number(e.target.value) || 1));
                              setSkillQuantities((prev) => ({
                                ...prev,
                                [sk.id]: val,
                              }));
                            }}
                            className="w-20 px-2.5 min-h-9 rounded-lg bg-surface border border-line text-sm text-ink text-center font-semibold tabular-nums"
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>

                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={isGenerating}
                  className="btn-primary w-full min-h-11 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-60 whitespace-nowrap"
                >
                  {isGenerating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>
                        {activeRunningJob
                          ? `Đang sinh đề (${activeRunningJob.created_count}/${activeRunningJob.requested_count} câu · ${elapsedSec}s)…`
                          : 'Đang khởi tạo…'}
                      </span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Tạo đề AI ({totalRequestedCount} câu)</span>
                    </>
                  )}
                </button>
              </form>

              {/* Right Column: Danh sách sinh đề + Compact Nhật ký gọi AI */}
              <div className="lg:col-span-7 space-y-4">
                <div className="bg-surface border border-line rounded-xl overflow-hidden">
                  <div className="px-5 py-3.5 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-ink">Danh sách sinh đề</h3>
                      <span className="badge-neutral px-2 py-0.5 rounded-full text-xs font-semibold tabular-nums">
                        {drafts.length} câu
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {shouldPollPipeline && (
                        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand tabular-nums">
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          <span>Đồng bộ tự động ({elapsedSec}s)</span>
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={() =>
                          runAdminWorker()
                            .then(() => {
                              loadJobs();
                              loadDrafts();
                            })
                            .catch((e) => setErr(extractApiError(e, 'Không chạy được hàng đợi')))
                        }
                        className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                      >
                        Làm mới tiến trình
                      </button>
                    </div>
                  </div>

                  {activeRunningJob && (
                    <div className="px-4 py-2.5 bg-canvas border-b border-line flex items-center justify-between gap-2 text-xs">
                      <span className="font-semibold text-ink">
                        Đang chạy Đợt #{activeRunningJob.job_id}: đã tạo{' '}
                        {activeRunningJob.created_count}/{activeRunningJob.requested_count} câu
                      </span>
                      <span className="badge-info px-2 py-0.5 rounded font-semibold">
                        Model A &amp; Model B đang xử lý
                      </span>
                    </div>
                  )}

                  <div className="divide-y divide-line max-h-[420px] overflow-y-auto">
                    {drafts.length === 0 ? (
                      <div className="p-8 text-center text-sm text-muted">
                        Chưa có câu hỏi nào được sinh. Hãy chọn kỹ năng và bấm Tạo đề AI ở khung bên trái.
                      </div>
                    ) : (
                      drafts.map((d: any) => {
                        const st = formatDraftStatusBadge(d.status);
                        const diff = DIFF_LABELS[d.difficulty] || DIFF_LABELS[1];
                        const minorTopic = d.job_id ? jobTopicById.get(Number(d.job_id)) : null;
                        return (
                          <div
                            key={d.draft_id}
                            className="px-4 py-3 hover:bg-canvas transition-colors flex items-start justify-between gap-3"
                          >
                            <div className="min-w-0 flex-1 space-y-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <code className="text-xs font-bold text-brand">
                                  #{d.draft_id}
                                </code>
                                <span className="text-sm font-bold text-ink leading-snug">
                                  {d.title || `Câu hỏi nháp #${d.draft_id}`}
                                </span>
                              </div>
                              <div className="flex flex-wrap items-center gap-2 text-xs text-muted tabular-nums">
                                <span className={`px-1.5 py-0.5 rounded font-semibold ${diff.badge}`}>
                                  {diff.text}
                                </span>
                                <span>{formatVnDateTime(d.updated_at || d.created_at)}</span>
                                {minorTopic && (
                                  <span className="truncate max-w-[260px] opacity-75">
                                    · {minorTopic}
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <span className={`px-2.5 py-1 rounded-md text-xs font-semibold whitespace-nowrap ${st.cls}`}>
                                {st.text}
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  inspectDraft(d.draft_id);
                                  setActiveTab('drafts');
                                }}
                                className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                              >
                                Xem đề
                              </button>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Compact AI Call Log (max-h-36, text-xs, 1 slim line per call, zero internal model names) */}
                <div className="bg-surface border border-line rounded-xl overflow-hidden">
                  <div className="px-4 py-2.5 bg-soft border-b border-line flex items-center justify-between gap-2 text-xs">
                    <span className="font-bold text-ink">Nhật ký gọi AI</span>
                    <span className="text-muted tabular-nums">
                      API Thật (apithat.dev) · Hôm nay: {llmUsage?.used_today ?? 0}/
                      {llmUsage?.daily_cap ?? 300} lượt
                    </span>
                  </div>

                  <div className="max-h-36 overflow-y-auto divide-y divide-line text-xs tabular-nums">
                    {(llmUsage?.recent_calls || []).length === 0 ? (
                      <div className="px-4 py-3 text-muted text-center">
                        Chưa ghi nhận lượt gọi AI nào trong phiên này.
                      </div>
                    ) : (
                      (llmUsage.recent_calls as any[]).map((c: any) => {
                        const ok = c.status === 'succeeded';
                        const failed = c.status === 'failed' || c.status === 'timed_out';
                        return (
                          <div
                            key={c.call_id}
                            className="px-3.5 py-1.5 flex items-center justify-between gap-2 hover:bg-canvas"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <code className="text-muted shrink-0">#{c.call_id}</code>
                              <span className="font-semibold text-ink shrink-0">
                                {formatAiStageLabel(c.stage)}
                              </span>
                              {c.draft_id && (
                                <span className="text-muted truncate">
                                  · Nháp #{c.draft_id}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              {c.latency_ms !== null && c.latency_ms !== undefined && (
                                <span className="text-muted">{c.latency_ms} ms</span>
                              )}
                              <span
                                className={`px-1.5 py-0.5 rounded font-semibold ${
                                  ok ? 'badge-easy' : failed ? 'badge-hard' : 'badge-info'
                                }`}
                              >
                                {ok ? 'Hoàn tất' : failed ? 'Lỗi' : 'Đang gọi'}
                              </span>
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
            /* Manual Question Composer */
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              <form
                onSubmit={handleCreateManualQuestion}
                className="lg:col-span-8 bg-surface border border-line rounded-xl p-5 space-y-4"
              >
                <div className="border-b border-line pb-2.5">
                  <h2 className="text-base font-bold text-ink">
                    Soạn đề bài &amp; câu lệnh SQL đáp án mẫu
                  </h2>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1">
                    Tiêu đề bài tập
                  </label>
                  <input
                    required
                    value={manualTitle}
                    onChange={(e) => setManualTitle(e.target.value)}
                    placeholder="Nhập tiêu đề bài tập SQL…"
                    className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1">
                    Nội dung đề bài
                  </label>
                  <textarea
                    required
                    rows={4}
                    value={manualQuestion}
                    onChange={(e) => setManualQuestion(e.target.value)}
                    placeholder="Mô tả yêu cầu truy vấn, các cột kết quả cần trả về và thứ tự sắp xếp…"
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
                      Chế độ so khớp thứ tự dòng
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
                    Kỹ năng gắn kèm
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
                                ? prev.length > 1
                                  ? prev.filter((x) => x !== sk.id)
                                  : prev
                                : [...prev, sk.id]
                            )
                          }
                          className={`px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap ${
                            active ? 'btn-primary' : 'btn-secondary'
                          }`}
                        >
                          {sk.code} · {sk.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-ink mb-1">
                    Câu lệnh SQL đáp án mẫu
                  </label>
                  <textarea
                    required
                    rows={5}
                    value={manualSql}
                    onChange={(e) => setManualSql(e.target.value)}
                    className="w-full p-3.5 rounded-lg bg-canvas border border-line font-mono text-sm text-ink leading-relaxed"
                  />
                </div>

                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={savingManual}
                  className="btn-primary px-6 min-h-11 rounded-xl text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
                >
                  {savingManual ? 'Đang kiểm tra trên Sandbox…' : 'Kiểm tra & Lưu câu hỏi'}
                </button>
              </form>

              <div className="lg:col-span-4 bg-surface border border-line rounded-xl p-4 space-y-3">
                <div className="flex items-center gap-2 border-b border-line pb-2.5">
                  <Database className="w-4 h-4 text-brand" />
                  <h3 className="text-sm font-bold text-ink">Sơ đồ 13 bảng dữ liệu</h3>
                </div>
                <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
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
                          className="btn-secondary px-2 min-h-7 rounded text-xs font-medium whitespace-nowrap"
                        >
                          Chèn mẫu
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
          TAB 3: DUYỆT ĐỀ (THUẦN ADMIN KIỂM CHỨNG — KHÔNG CÓ AI CAN THIỆP)
      ===================================================================== */}
      {activeTab === 'drafts' && (
        <div className="space-y-4">
          {checkedDraftIds.length > 0 && (
            <div className="p-3.5 rounded-xl bg-surface border-2 border-brand flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm font-bold text-ink tabular-nums">
                Đã chọn {checkedDraftIds.length} bản nháp
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  data-solid-btn="true"
                  disabled={bulkBusy}
                  onClick={handleBulkApprove}
                  className="btn-primary px-4 min-h-9 rounded-lg text-xs font-semibold disabled:opacity-50 whitespace-nowrap"
                >
                  {bulkBusy ? 'Đang xử lý…' : `Phê duyệt hàng loạt (${checkedDraftIds.length})`}
                </button>
                <button
                  type="button"
                  onClick={() => setCheckedDraftIds([])}
                  className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-medium whitespace-nowrap"
                >
                  Bỏ chọn
                </button>
              </div>
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
                    className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                  >
                    Chọn đề chờ duyệt
                  </button>
                </div>

                <div className="relative">
                  <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
                  <input
                    value={draftSearch}
                    onChange={(e) => setDraftSearch(e.target.value)}
                    placeholder="Lọc mã nháp, tiêu đề, bảng dữ liệu, độ khó…"
                    className="w-full pl-9 pr-3 min-h-9 rounded-lg bg-surface border border-line text-sm text-ink"
                  />
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {[
                    { val: '', label: `Tất cả (${drafts.length})` },
                    {
                      val: 'needs_human',
                      label: `Cần duyệt (${drafts.filter((d) => d.status === 'needs_human').length})`,
                    },
                    {
                      val: 'approved',
                      label: `Đã duyệt (${drafts.filter((d) => d.status === 'approved').length})`,
                    },
                    {
                      val: 'rejected',
                      label: `Từ chối (${drafts.filter((d) => d.status === 'rejected').length})`,
                    },
                  ].map((pill) => {
                    const active = draftStatusFilter === pill.val;
                    return (
                      <button
                        key={pill.val || 'all'}
                        type="button"
                        data-solid-btn={active ? 'true' : undefined}
                        onClick={() => setDraftStatusFilter(pill.val)}
                        className={`px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap ${
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
                    const st = formatDraftStatusBadge(d.status);
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
                              #{d.draft_id} · {DIFF_LABELS[d.difficulty]?.text || `Mức ${d.difficulty}`}
                            </span>
                            <span className={`px-2 py-0.5 rounded-md text-xs font-semibold ${st.cls}`}>
                              {st.text}
                            </span>
                          </div>
                          <div className="text-sm font-semibold text-ink line-clamp-2">
                            {d.title}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Right Draft Detail & Action Buttons */}
            <div className="lg:col-span-7 bg-surface border border-line rounded-xl overflow-hidden">
              {selectedDraft ? (
                <div className="divide-y divide-line">
                  <div className="px-5 py-3.5 bg-soft flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-xs text-muted tabular-nums">
                        Bản nháp #{selectedDraft.draft_id}
                      </div>
                      <div className="text-base font-bold text-ink">
                        Kiểm duyệt nội dung &amp; SQL đáp án
                      </div>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-md text-xs font-semibold ${
                        formatDraftStatusBadge(selectedDraft.status).cls
                      }`}
                    >
                      {formatDraftStatusBadge(selectedDraft.status).text}
                    </span>
                  </div>

                  <div className="p-5 space-y-4">
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <label className="block text-sm font-semibold text-ink">
                          Tiêu đề bài tập
                        </label>
                        {hasDraftTextEdited &&
                          ['needs_human', 'rejected'].includes(selectedDraft.status) && (
                            <button
                              type="button"
                              disabled={draftActionBusy}
                              onClick={handleSaveDraftContent}
                              className="btn-secondary px-3 min-h-8 rounded-md text-xs font-semibold whitespace-nowrap"
                            >
                              Lưu nội dung
                            </button>
                          )}
                      </div>
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-ink mb-1">
                        Nội dung đề bài
                      </label>
                      <textarea
                        rows={3}
                        value={editQuestion}
                        onChange={(e) => setEditQuestion(e.target.value)}
                        className="w-full p-3.5 rounded-lg bg-canvas border border-line text-sm text-ink leading-relaxed"
                      />
                    </div>

                    {/* Choose Self-Solve Run OR Custom SQL (Clean Model B Labels) */}
                    <div className="space-y-2.5">
                      <div className="text-sm font-semibold text-ink">
                        Câu lệnh SQL đáp án dùng để chấm điểm
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
                              <div className="font-semibold text-ink">
                                Model A · Sinh đề (SQL gốc)
                              </div>
                              <div className="text-muted">Đáp án chuẩn của bản nháp</div>
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
                                Model B · Kiểm duyệt (Lượt #{rIdx + 1})
                              </div>
                              <div className="text-muted tabular-nums">
                                Khớp {run.matched_datasets}/{run.total_datasets} bộ dữ liệu ·{' '}
                                {run.row_count ?? 0} dòng
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
                            <div className="font-semibold text-ink">Tự chỉnh sửa SQL đáp án</div>
                            <div className="text-muted">Biên tập câu lệnh ngay bên dưới</div>
                          </div>
                        </label>
                      </div>

                      <textarea
                        rows={5}
                        value={customSqlText}
                        onChange={(e) => {
                          setCustomSqlText(e.target.value);
                          setSqlSourceChoice('custom');
                        }}
                        placeholder="SELECT … FROM …"
                        className="w-full p-3 rounded-lg bg-canvas border border-line font-mono text-xs text-ink leading-relaxed"
                      />
                    </div>

                    <div>
                      <input
                        value={reviewNote}
                        onChange={(e) => setReviewNote(e.target.value)}
                        placeholder="Ghi chú kiểm duyệt hoặc lý do từ chối (tùy chọn)…"
                        className="w-full px-3.5 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                      />
                    </div>

                    {/* Status-Specific Action Buttons (Strictly NO Requeue) */}
                    <div className="flex flex-wrap items-center gap-2.5 pt-1">
                      {(selectedDraft.status === 'needs_human' ||
                        selectedDraft.status === 'rejected') && (
                        <>
                          <button
                            type="button"
                            data-solid-btn="true"
                            disabled={draftActionBusy}
                            onClick={handleApproveSingleDraft}
                            className="btn-primary px-5 min-h-10 rounded-lg text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
                          >
                            {draftActionBusy ? 'Đang xử lý…' : 'Phê duyệt'}
                          </button>

                          {selectedDraft.status === 'needs_human' && (
                            <button
                              type="button"
                              data-solid-btn="true"
                              disabled={draftActionBusy}
                              onClick={handleRejectDraft}
                              className="btn-danger px-4 min-h-10 rounded-lg text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
                            >
                              Từ chối bản nháp
                            </button>
                          )}
                        </>
                      )}

                      {selectedDraft.status === 'approved' && (
                        <>
                          <button
                            type="button"
                            data-solid-btn="true"
                            disabled={draftActionBusy}
                            onClick={handleReturnNeedsHuman}
                            className="btn-copper px-4 min-h-10 rounded-lg text-sm font-semibold flex items-center gap-1.5 disabled:opacity-50 whitespace-nowrap"
                          >
                            <RotateCcw className="w-4 h-4" />
                            <span>Chuyển về Cần duyệt (needs_human)</span>
                          </button>

                          <button
                            type="button"
                            data-solid-btn="true"
                            disabled={draftActionBusy}
                            onClick={handleRejectDraft}
                            className="btn-danger px-4 min-h-10 rounded-lg text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
                          >
                            Từ chối bản nháp
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-10 text-center text-sm text-muted">
                  Chọn một bản nháp ở cột bên trái để kiểm duyệt chi tiết.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          TAB 4: BỘ ĐỀ TUẦN (APPROVED POOL + BATCH COMPOSER + WEEKLY SETS)
      ===================================================================== */}
      {activeTab === 'weekly' && (
        <div className="space-y-6">
          <div className="p-3.5 rounded-xl bg-surface border border-line text-xs text-text2 leading-relaxed">
            <strong className="text-ink">Cách hoạt động:</strong> Đề đạt <span className="font-semibold text-brand">Approved</span> (do AI tự duyệt hoặc Admin phê duyệt) sẽ nằm trong mục <strong>Câu hỏi Approved chưa có trên kệ</strong> bên dưới. Bạn tick chọn hoặc bấm <strong>+ Thêm</strong> các câu sang khung bên phải để soạn bộ đề rồi bấm <strong>Đăng</strong> lên kệ Học viên.
          </div>

          {/* SECTION A: APPROVED QUESTIONS POOL & 1-CLICK BATCH PUBLISH */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left: All Approved Questions (from both drafts 'approved' & live.questions 'ready') */}
            <div className="lg:col-span-6 bg-surface border border-line rounded-2xl overflow-hidden">
              <div className="p-4 bg-soft border-b border-line space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-base font-bold text-ink">
                      {approvedShelfTab === 'on_shelf'
                        ? `Thống kê câu hỏi đã có trên kệ (${onShelfApprovedPool.length})`
                        : `Câu hỏi Approved chưa có trên kệ (${unassignedApprovedPool.length})`}
                    </h2>
                    <p className="text-xs text-muted mt-0.5">
                      {approvedShelfTab === 'on_shelf'
                        ? 'Tổng hợp các câu hỏi đang mở trực tiếp cho học viên làm bài trên kệ hiện hành.'
                        : 'Tick chọn hoặc nắm kéo câu hỏi chưa lên kệ sang khung bên phải để soạn bộ đề tuần.'}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    data-solid-btn={approvedShelfTab === 'unassigned' ? 'true' : undefined}
                    onClick={() => {
                      setApprovedShelfTab('unassigned');
                      setPickedApprovedKeys([]);
                    }}
                    className={`px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap ${
                      approvedShelfTab === 'unassigned' ? 'btn-primary' : 'btn-secondary'
                    }`}
                  >
                    Chưa có trên kệ ({rawUnassignedPool.length})
                  </button>
                  <button
                    type="button"
                    data-solid-btn={approvedShelfTab === 'on_shelf' ? 'true' : undefined}
                    onClick={() => {
                      setApprovedShelfTab('on_shelf');
                      setPickedApprovedKeys([]);
                    }}
                    className={`px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap ${
                      approvedShelfTab === 'on_shelf' ? 'btn-primary' : 'btn-secondary'
                    }`}
                  >
                    Đã có trên kệ ({rawOnShelfPool.length})
                  </button>

                  {[
                    { label: 'Mọi mức', val: undefined },
                    { label: 'Dễ', val: 1 },
                    { label: 'Trung bình', val: 2 },
                    { label: 'Khó', val: 3 },
                  ].map((d) => {
                    const active = approvedDiffFilter === d.val;
                    return (
                      <button
                        key={d.label}
                        type="button"
                        data-solid-btn={active ? 'true' : undefined}
                        onClick={() => setApprovedDiffFilter(d.val)}
                        className={`px-2.5 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap ${
                          active ? 'btn-blue' : 'btn-secondary'
                        }`}
                      >
                        {d.label}
                      </button>
                    );
                  })}
                </div>

                {approvedShelfTab === 'on_shelf' && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 tabular-nums">
                    <div className="p-2.5 rounded-xl bg-surface border border-line">
                      <div className="text-xs text-muted">Tổng trên kệ</div>
                      <div className="text-base font-bold text-ink">
                        {rawOnShelfPool.length} câu
                      </div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-surface border border-line">
                      <div className="text-xs text-muted">Mức Dễ</div>
                      <div className="text-base font-bold text-brand">
                        {rawOnShelfPool.filter((x) => x.difficulty === 1).length} câu
                      </div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-surface border border-line">
                      <div className="text-xs text-muted">Trung bình</div>
                      <div className="text-base font-bold text-ink">
                        {rawOnShelfPool.filter((x) => x.difficulty === 2).length} câu
                      </div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-surface border border-line">
                      <div className="text-xs text-muted">Mức Khó</div>
                      <div className="text-base font-bold text-danger">
                        {rawOnShelfPool.filter((x) => x.difficulty === 3).length} câu
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative flex-1 min-w-[180px]">
                    <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
                    <input
                      value={approvedSearch}
                      onChange={(e) => setApprovedSearch(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && loadReadyQuestions()}
                      placeholder="Lọc mã câu, số thứ tự, tiêu đề, bảng dữ liệu…"
                      className="w-full pl-9 pr-3 min-h-9 rounded-lg bg-surface border border-line text-sm text-ink"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={loadReadyQuestions}
                    className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                  >
                    Lọc
                  </button>
                </div>

                {approvedShelfTab === 'unassigned' && (
                  <div className="pt-2 border-t border-line flex flex-wrap items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        const allKeys = unifiedApprovedPool.map((item) => item.key);
                        const allSelected =
                          allKeys.length > 0 &&
                          allKeys.every((k) => pickedApprovedKeys.includes(k));
                        setPickedApprovedKeys(allSelected ? [] : allKeys);
                      }}
                      className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                    >
                      Chọn tất cả ({unifiedApprovedPool.length})
                    </button>

                    {pickedApprovedKeys.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <button
                          type="button"
                          data-solid-btn="true"
                          disabled={groupBusy}
                          onClick={() => handleAddApprovedKeysToGroup(pickedApprovedKeys)}
                          className="btn-primary px-3.5 min-h-8 rounded-lg text-xs font-semibold flex items-center gap-1 disabled:opacity-50 whitespace-nowrap"
                        >
                          <span>Gom {pickedApprovedKeys.length} câu vào Nhóm</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                        {weeklySetDetail?.status === 'draft' && (
                          <button
                            type="button"
                            disabled={groupBusy}
                            onClick={handleAddPickedToDraftWeeklySet}
                            className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                          >
                            + Thêm vào Bộ đề #{weeklySetDetail.set_id}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="divide-y divide-line max-h-[520px] overflow-y-auto">
                {unifiedApprovedPool.length === 0 ? (
                  <div className="p-8 text-center text-sm text-muted">
                    {approvedShelfTab === 'on_shelf'
                      ? 'Hiện chưa có câu hỏi nào trên kệ Bộ đề đang mở.'
                      : 'Tất cả câu hỏi Approved hiện đã nằm trên kệ hoặc chưa có câu mới chờ gom nhóm.'}
                  </div>
                ) : (
                  unifiedApprovedPool.map((item) => {
                    const checked = pickedApprovedKeys.includes(item.key);
                    const alreadyInGroup =
                      item.question_id !== null && groupItemIdSet.has(item.question_id);
                    const diff = DIFF_LABELS[item.difficulty] || DIFF_LABELS[1];
                    const preview = item.question_id ? previewCache[item.question_id] : null;
                    return (
                      <div
                        key={item.key}
                        draggable={approvedShelfTab === 'unassigned'}
                        onDragStart={(e) => {
                          if (approvedShelfTab !== 'unassigned') return;
                          e.dataTransfer.setData('text/plain', item.key);
                          e.dataTransfer.effectAllowed = 'copy';
                          setDraggingApprovedKey(item.key);
                        }}
                        onDragEnd={() => {
                          setDraggingApprovedKey(null);
                          setIsOverDropZone(false);
                        }}
                        className={`p-3.5 space-y-2 transition-colors ${
                          draggingApprovedKey === item.key ? 'opacity-60 bg-soft' : 'hover:bg-canvas'
                        }`}
                      >
                        <div className="flex items-start gap-2.5">
                          {approvedShelfTab === 'unassigned' && (
                            <>
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() =>
                                  setPickedApprovedKeys((prev) =>
                                    prev.includes(item.key)
                                      ? prev.filter((k) => k !== item.key)
                                      : [...prev, item.key]
                                  )
                                }
                                aria-label={`Chọn câu hỏi ${item.key}`}
                                className="mt-1 w-4 h-4 accent-[var(--green)] cursor-pointer shrink-0"
                              />
                              <div
                                className="mt-0.5 text-muted cursor-grab active:cursor-grabbing shrink-0"
                                title="Kéo thả sang khung Nhóm đề bên phải"
                              >
                                <GripVertical className="w-4 h-4" />
                              </div>
                            </>
                          )}

                          <div className="flex-1 min-w-0 space-y-1">
                            <div className="text-sm font-semibold text-ink leading-snug">
                              <code className="text-xs text-brand font-bold mr-1.5">
                                {item.question_id ? `#${item.question_id}` : `Nháp #${item.draft_id}`}
                              </code>
                              {item.title}
                            </div>

                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="px-2 py-0.5 rounded badge-easy text-xs font-semibold">
                                Approved
                              </span>
                              <span className={`px-2 py-0.5 rounded text-xs font-semibold ${diff.badge}`}>
                                {diff.text}
                              </span>
                              {item.tables_used.slice(0, 2).map((tb) => (
                                <code
                                  key={tb}
                                  className="px-1.5 py-0.5 rounded bg-soft text-xs text-text2"
                                >
                                  {tb}
                                </code>
                              ))}
                              {item.in_published_set && (
                                <span className="px-2 py-0.5 rounded badge-info text-xs font-medium">
                                  Đang trên kệ
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {item.question_id && (
                              <button
                                type="button"
                                onClick={() => toggleQuestionPreview(item.question_id!)}
                                className="btn-secondary px-2.5 min-h-8 rounded-lg text-xs font-medium flex items-center gap-1 whitespace-nowrap"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                <span>Xem</span>
                              </button>
                            )}

                            {approvedShelfTab === 'unassigned' &&
                              (alreadyInGroup ? (
                                <span className="px-2.5 py-1 rounded-lg badge-easy text-xs font-semibold whitespace-nowrap">
                                  Đã gom
                                </span>
                              ) : (
                                <button
                                  type="button"
                                  data-solid-btn="true"
                                  disabled={groupBusy}
                                  onClick={() => handleAddApprovedKeysToGroup([item.key])}
                                  className="btn-primary px-3 min-h-8 rounded-lg text-xs font-semibold flex items-center gap-1 disabled:opacity-50 whitespace-nowrap"
                                >
                                  <Plus className="w-3.5 h-3.5" />
                                  <span>Thêm</span>
                                </button>
                              ))}
                          </div>
                        </div>

                        {item.question_id && previewQuestionId === item.question_id && (
                          <div className="ml-8 p-3 rounded-xl bg-canvas border border-line space-y-2 text-xs">
                            <div className="text-sm text-ink leading-relaxed">
                              {preview?.question || 'Đang tải nội dung đề bài…'}
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

            {/* Right: Group Composer & 1-Click Publish */}
            <div className="lg:col-span-6 bg-surface border border-line rounded-2xl overflow-hidden flex flex-col">
              <div className="p-4 bg-soft border-b border-line space-y-3">
                <div>
                  <h2 className="text-base font-bold text-ink">
                    Soạn Bộ đề thủ công theo đợt &amp; Đăng 1 lần
                  </h2>
                  <p className="text-xs text-muted mt-0.5">
                    Nhập tên bộ đề, thêm câu hỏi từ danh sách bên trái, sắp xếp thứ tự rồi phát hành cùng lúc.
                  </p>
                </div>

                <form onSubmit={handleCreateGroup} className="flex flex-wrap gap-2">
                  <input
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    placeholder="Nhập tên bộ đề tuần hoặc nhóm câu hỏi…"
                    className="flex-1 min-w-[200px] px-3.5 min-h-9 rounded-lg bg-surface border border-line text-sm text-ink"
                  />
                  <button
                    type="submit"
                    data-solid-btn="true"
                    disabled={creatingGroup}
                    className="btn-primary px-3.5 min-h-9 rounded-lg text-xs font-semibold flex items-center gap-1.5 shrink-0 whitespace-nowrap"
                  >
                    <FolderPlus className="w-3.5 h-3.5" />
                    <span>{creatingGroup ? 'Đang tạo…' : '+ Tạo bộ nháp'}</span>
                  </button>
                </form>

                {draftGroups.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {draftGroups.map((g) => {
                      const active = selectedGroupId === g.group_id;
                      return (
                        <button
                          key={g.group_id}
                          type="button"
                          data-solid-btn={active ? 'true' : undefined}
                          onClick={() => {
                            setPublishSetTitle(g.name || '');
                            loadGroupDetail(g.group_id);
                          }}
                          className={`px-3 min-h-8 rounded-lg text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap ${
                            active ? 'btn-blue' : 'btn-secondary'
                          }`}
                        >
                          <span>{g.name}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-xs tabular-nums ${
                              active ? 'bg-surface text-ink' : 'badge-medium'
                            }`}
                          >
                            {g.question_count} câu
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!isOverDropZone) setIsOverDropZone(true);
                }}
                onDragLeave={() => setIsOverDropZone(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsOverDropZone(false);
                  const droppedKey = e.dataTransfer.getData('text/plain');
                  if (droppedKey) {
                    handleAddApprovedKeysToGroup([droppedKey]);
                  }
                }}
                className={`p-4 space-y-4 transition-colors ${
                  isOverDropZone ? 'bg-soft' : 'bg-surface'
                }`}
              >
                <div
                  className={`p-3.5 rounded-xl border-2 border-dashed text-center text-xs ${
                    isOverDropZone
                      ? 'border-brand bg-canvas text-brand font-bold'
                      : 'border-line bg-canvas text-muted'
                  }`}
                >
                  {groupDetail ? (
                    isSelectedGroupEditable ? (
                      <span>
                        Thả câu hỏi Approved vào đây để gom vào nhóm{' '}
                        <strong className="text-ink">&quot;{groupDetail.name}&quot;</strong>
                      </span>
                    ) : (
                      <span>
                        Nhóm <strong className="text-ink">&quot;{groupDetail.name}&quot;</strong> đã phát hành. Hãy tạo nhóm mới ở trên nếu cần gom đợt tiếp theo.
                      </span>
                    )
                  ) : (
                    <span>Kéo thả câu hỏi Approved vào đây để tự động khởi tạo nhóm nháp</span>
                  )}
                </div>

                {groupDetail && (
                  <>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-ink">
                          {groupDetail.name} ({groupItems.length} câu)
                        </h3>
                        <span
                          className={`px-2 py-0.5 rounded-md text-xs font-semibold ${
                            groupDetail.status === 'published' ? 'badge-easy' : 'badge-medium'
                          }`}
                        >
                          {groupDetail.status === 'published' ? 'Đã đăng' : 'Nháp'}
                        </span>
                      </div>

                      {isSelectedGroupEditable && (
                        <button
                          type="button"
                          disabled={groupBusy}
                          onClick={handleDeleteGroup}
                          className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold text-danger flex items-center gap-1 whitespace-nowrap"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Xoá nhóm</span>
                        </button>
                      )}
                    </div>

                    {groupItems.length === 0 ? (
                      <div className="p-6 rounded-xl bg-canvas border border-line text-center text-sm text-muted">
                        Nhóm chưa có câu hỏi. Hãy tick chọn hoặc kéo thả từ danh sách Approved bên trái.
                      </div>
                    ) : (
                      <div className="divide-y divide-line border border-line rounded-xl overflow-hidden max-h-[300px] overflow-y-auto">
                        {groupItems.map((it: any, idx: number) => {
                          const diff = DIFF_LABELS[it.difficulty] || DIFF_LABELS[1];
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
                              className="p-2.5 bg-surface hover:bg-canvas flex items-center justify-between gap-2"
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <span className="w-6 h-6 rounded bg-soft border border-line text-xs font-bold text-ink flex items-center justify-center shrink-0 tabular-nums">
                                  {idx + 1}
                                </span>
                                <div className="min-w-0">
                                  <div className="text-sm font-semibold text-ink truncate">
                                    {it.title}
                                  </div>
                                  <div className="flex items-center gap-1.5 text-xs text-muted">
                                    <span className={`px-1.5 py-0.5 rounded font-semibold ${diff.badge}`}>
                                      {diff.text}
                                    </span>
                                    <code>#{it.question_id}</code>
                                  </div>
                                </div>
                              </div>

                              {isSelectedGroupEditable && (
                                <div className="flex items-center gap-1 shrink-0">
                                  <button
                                    type="button"
                                    disabled={groupBusy}
                                    onClick={() => removeGroupItem(it.question_id)}
                                    className="btn-secondary px-2.5 min-h-8 rounded-md text-xs font-semibold text-danger whitespace-nowrap"
                                  >
                                    Gỡ
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {isSelectedGroupEditable && (
                      <div className="p-4 rounded-xl bg-soft border border-line space-y-3">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          <label
                            className={`p-2.5 rounded-xl border cursor-pointer flex items-start gap-2 text-xs ${
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
                              className="mt-0.5 accent-[var(--green)]"
                            />
                            <div>
                              <div className="font-semibold text-ink">
                                Gộp vào Bộ đề tuần đang mở
                              </div>
                              <div className="text-muted">Hiển thị ngay bên Web Học Viên</div>
                            </div>
                          </label>

                          <label
                            className={`p-2.5 rounded-xl border cursor-pointer flex items-start gap-2 text-xs ${
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
                              className="mt-0.5 accent-[var(--green)]"
                            />
                            <div>
                              <div className="font-semibold text-ink">
                                Mở thành Bộ đề tuần mới
                              </div>
                              <div className="text-muted">Đóng bộ cũ &amp; phát hành bộ mới</div>
                            </div>
                          </label>
                        </div>

                        {publishMode === 'new_weekly_set' && (
                          <input
                            value={publishSetTitle}
                            onChange={(e) => setPublishSetTitle(e.target.value)}
                            placeholder="Tên Bộ đề tuần mới…"
                            className="w-full px-3.5 min-h-9 rounded-lg bg-surface border border-line text-sm text-ink"
                          />
                        )}

                        <button
                          type="button"
                          data-solid-btn="true"
                          disabled={groupBusy || groupItems.length === 0}
                          onClick={handlePublishGroup}
                          className="btn-primary w-full min-h-11 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-40 whitespace-nowrap"
                        >
                          <Send className="w-4 h-4" />
                          <span>
                            {groupBusy
                              ? 'Đang đăng…'
                              : `Đăng toàn bộ ${groupItems.length} câu lên cùng 1 lúc`}
                          </span>
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* SECTION B: WEEKLY SETS MANAGEMENT & INSPECTOR */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              <div className="lg:col-span-5 bg-surface border border-line rounded-xl overflow-hidden">
                <div className="px-4 py-3.5 bg-soft border-b border-line text-sm font-bold text-ink">
                  Danh sách Bộ đề tuần ({weeklySets.length})
                </div>
                <div className="divide-y divide-line max-h-[480px] overflow-y-auto">
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
                                      setMsg(`Đã phát hành bộ đề tuần #${w.set_id}.`);
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
                                className="btn-primary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                              >
                                Phát hành
                              </button>
                            )}
                            {w.status === 'published' && (
                              <button
                                type="button"
                                data-solid-btn="true"
                                onClick={() =>
                                  closeAdminWeeklySet(w.set_id)
                                    .then(() => {
                                      setMsg(`Đã đóng bộ đề tuần #${w.set_id}.`);
                                      loadWeekly();
                                    })
                                    .catch((e) =>
                                      setErr(extractApiError(e, 'Không thể đóng bộ đề tuần'))
                                    )
                                }
                                className="btn-danger px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                              >
                                Đóng chu kỳ
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div className="lg:col-span-7 bg-surface border border-line rounded-xl overflow-hidden">
                <div className="px-5 py-3.5 bg-soft border-b border-line flex items-center justify-between">
                  <h3 className="text-sm font-bold text-ink">
                    {weeklySetDetail
                      ? `Câu hỏi trong Bộ #${weeklySetDetail.set_id}: ${weeklySetDetail.title} (${
                          weeklySetDetail.items?.length || 0
                        } câu)`
                      : 'Chi tiết câu hỏi trong Bộ đề tuần'}
                  </h3>
                </div>

                {loadingWeeklyDetail ? (
                  <div className="p-10 text-center text-sm text-muted">
                    Đang tải danh sách câu hỏi…
                  </div>
                ) : !weeklySetDetail ? (
                  <div className="p-10 text-center text-sm text-muted">
                    Chọn một bộ đề tuần ở bên trái để xem danh sách câu hỏi.
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
                          <th className="py-3 px-4 w-24">Mã bài</th>
                          <th className="py-3 px-4">Câu hỏi</th>
                          <th className="py-3 px-4 w-32">Độ khó</th>
                          {weeklySetDetail.status !== 'closed' && (
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
                              {weeklySetDetail.status !== 'closed' && (
                                <td className="py-3 px-4">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      handleRemoveFromWeeklySet(
                                        weeklySetDetail.set_id,
                                        item.question_id
                                      )
                                    }
                                    className="btn-secondary px-2.5 min-h-8 rounded-md text-xs font-semibold text-danger whitespace-nowrap"
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
        </div>
      )}

      {/* =====================================================================
          TAB 5: NGÂN HÀNG ĐỀ
      ===================================================================== */}
      {activeTab === 'bank' && (
        <div className="bg-surface border border-line rounded-xl overflow-hidden">
          <div className="px-5 py-4 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-base font-bold text-ink">
              Ngân hàng đề ({visibleBankQuestions.length}/{allBankQuestions.length} câu)
            </h3>
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-4 h-4 text-muted absolute left-3 top-3" />
                <input
                  value={bankSearch}
                  onChange={(e) => setBankSearch(e.target.value)}
                  placeholder="Lọc ID, tiêu đề, bảng dữ liệu, độ khó…"
                  className="pl-9 pr-3 min-h-10 rounded-lg bg-surface border border-line text-sm text-ink"
                />
              </div>
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
                {visibleBankQuestions.map((q: any) => {
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
                          {q.in_published_set ? ' · Đang mở trên kệ' : ''}
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
                                  setMsg(`Đã cập nhật trạng thái Đề mẫu cho câu #${q.question_id}.`);
                                  loadAllBankQuestions();
                                })
                                .catch((e) => setErr(extractApiError(e, 'Lỗi cập nhật Đề mẫu')))
                            }
                            className={`px-2.5 min-h-8 rounded-md text-xs font-semibold whitespace-nowrap ${
                              q.is_source ? 'badge-easy' : 'btn-secondary'
                            }`}
                          >
                            Đề mẫu AI: {q.is_source ? 'Bật' : 'Tắt'}
                          </button>

                          {q.status !== 'retired' ? (
                            <button
                              type="button"
                              onClick={() =>
                                retireAdminQuestion(q.question_id, 'Quản trị viên thu hồi')
                                  .then(() => {
                                    setMsg(`Đã thu hồi câu hỏi #${q.question_id}.`);
                                    loadAllBankQuestions();
                                    loadReadyQuestions();
                                  })
                                  .catch((e) => setErr(extractApiError(e, 'Không thể thu hồi câu hỏi')))
                              }
                              className="btn-secondary px-2.5 min-h-8 rounded-md text-xs font-semibold text-danger whitespace-nowrap"
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
                                    loadReadyQuestions();
                                  })
                                  .catch((e) => setErr(extractApiError(e, 'Không thể khôi phục câu hỏi')))
                              }
                              className="btn-primary px-2.5 min-h-8 rounded-md text-xs font-semibold whitespace-nowrap"
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

      {/* =====================================================================
          TAB 6: CẤU HÌNH
      ===================================================================== */}
      {activeTab === 'settings' && (
        <div className="bg-surface border border-line rounded-xl overflow-hidden">
          <div className="px-5 py-4 bg-soft border-b border-line">
            <h3 className="text-base font-bold text-ink">
              Tham số Cấu hình Hệ thống
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
                    <span className="px-3 min-h-10 rounded-lg badge-neutral text-xs font-medium inline-flex items-center whitespace-nowrap">
                      Cố định
                    </span>
                  ) : (
                    <button
                      type="button"
                      data-solid-btn="true"
                      onClick={() => handleUpdateSetting(st.key)}
                      className="btn-primary px-4 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap"
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
