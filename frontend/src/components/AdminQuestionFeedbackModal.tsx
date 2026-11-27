'use client';

import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Flag,
  RotateCcw,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  Wrench,
  X,
} from 'lucide-react';
import {
  extractApiError,
  getAdminQuestionDetail,
  resolveAdminQuestionReport,
} from '@/lib/api';

export function AdminQuestionFeedbackModal({
  questionId,
  onClose,
  onResolved,
}: {
  questionId: number | null;
  onClose: () => void;
  onResolved: (msg: string) => void;
}) {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editQuestion, setEditQuestion] = useState('');
  const [editSql, setEditSql] = useState('');
  const [adminNote, setAdminNote] = useState('');
  const [busy, setBusy] = useState(false);

  const loadDetail = async (qid: number) => {
    setLoading(true);
    setErr(null);
    try {
      const d = await getAdminQuestionDetail(qid);
      setDetail(d);
      setEditTitle(d?.title || '');
      setEditQuestion(d?.question || '');
      setEditSql(d?.reference_sql || '');
      const openList = (d?.feedback?.reports || []).filter((r: any) => r.status === 'open');
      setSelectedReportId(openList.length > 0 ? openList[0].report_id : null);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không tải được chi tiết câu hỏi và góp ý.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (questionId) {
      setEditMode(false);
      setAdminNote('');
      loadDetail(questionId);
    } else {
      setDetail(null);
    }
  }, [questionId]);

  if (!questionId) return null;

  const fb = detail?.feedback || { upvotes: 0, downvotes: 0, open_reports_count: 0, reports: [] };
  const reports: any[] = Array.isArray(fb.reports) ? fb.reports : [];
  const activeOpenReport =
    reports.find((r) => r.report_id === selectedReportId && r.status === 'open') ||
    reports.find((r) => r.status === 'open') ||
    null;

  const handleResolve = async (
    action: 'rework' | 'return_needs_human' | 'retire' | 'dismiss'
  ) => {
    if (!activeOpenReport) return;
    setBusy(true);
    setErr(null);
    try {
      const payload: any = {
        action,
        admin_note: adminNote.trim() || undefined,
      };
      if (action === 'rework') {
        payload.updated_title = editTitle.trim();
        payload.updated_question = editQuestion.trim();
        payload.updated_sql = editSql.trim();
      }
      await resolveAdminQuestionReport(activeOpenReport.report_id, payload);
      const actionMsg =
        action === 'dismiss'
          ? `Đã bỏ qua báo lỗi #${activeOpenReport.report_id}; câu hỏi #${questionId} giữ nguyên hoạt động.`
          : action === 'retire'
          ? `Đã loại bỏ câu hỏi #${questionId} khỏi ngân hàng đề và đóng các báo lỗi.`
          : action === 'return_needs_human'
          ? `Đã thu hồi câu hỏi #${questionId} về hàng đợi Duyệt đề và đóng báo lỗi.`
          : `Đã cập nhật SQL / đề bài, sinh lại Test Case cho câu #${questionId} và đóng báo lỗi.`;
      onResolved(actionMsg);
      await loadDetail(questionId);
      setEditMode(false);
      setAdminNote('');
    } catch (e: any) {
      setErr(extractApiError(e, 'Không xử lý được báo lỗi.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      data-ui="feedback-modal"
      className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
    >
      <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl bg-surface border border-line">
        <div className="px-5 py-3.5 bg-soft border-b border-line flex items-center justify-between gap-3 sticky top-0 z-10">
          <div className="flex flex-wrap items-center gap-2">
            <Flag className="w-4 h-4 text-brand" />
            <h3 className="text-base font-bold text-ink">
              Chi tiết câu hỏi #{questionId} &amp; Phản hồi người học
            </h3>
            <span className="badge-neutral px-2 py-0.5 rounded text-xs font-semibold inline-flex items-center gap-1 tabular-nums">
              <ThumbsUp className="w-3 h-3" /> {fb.upvotes ?? 0}
            </span>
            <span className="badge-neutral px-2 py-0.5 rounded text-xs font-semibold inline-flex items-center gap-1 tabular-nums">
              <ThumbsDown className="w-3 h-3" /> {fb.downvotes ?? 0}
            </span>
            {Number(fb.open_reports_count || 0) > 0 && (
              <span className="badge-medium px-2 py-0.5 rounded text-xs font-semibold inline-flex items-center gap-1 tabular-nums">
                <AlertTriangle className="w-3 h-3" /> {fb.open_reports_count} báo lỗi đang mở
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted hover:text-ink"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4 text-sm">
          {loading && <div className="text-muted">Đang tải dữ liệu câu hỏi…</div>}
          {err && (
            <div className="p-3 rounded-lg badge-hard text-xs font-medium">{err}</div>
          )}

          {detail && (
            <>
              {/* Current Question Snapshot */}
              <div className="p-4 rounded-xl bg-canvas border border-line space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-bold text-ink">{detail.title}</div>
                  <span className="badge-neutral px-2 py-0.5 rounded text-xs font-semibold">
                    Trạng thái: {detail.status} · So khớp: {detail.compare_mode || 'unordered'}
                  </span>
                </div>
                <div className="text-xs text-ink whitespace-pre-line leading-relaxed">
                  {detail.question}
                </div>
                {detail.reference_sql && (
                  <pre className="p-2.5 rounded-lg bg-surface border border-line font-mono text-xs text-ink whitespace-pre-wrap break-words">
                    {detail.reference_sql}
                  </pre>
                )}
              </div>

              {/* Reports List */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-ink">
                  Danh sách báo lỗi / góp ý ({reports.length})
                </div>

                {reports.length === 0 ? (
                  <div className="p-3.5 rounded-xl bg-canvas border border-line text-xs text-muted">
                    Chưa có báo lỗi hoặc góp ý nào cho câu hỏi này.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {reports.map((rep: any) => {
                      const isOpen = rep.status === 'open';
                      const isSelected = activeOpenReport?.report_id === rep.report_id;
                      return (
                        <div
                          key={rep.report_id}
                          onClick={() => isOpen && setSelectedReportId(rep.report_id)}
                          className={`p-3 rounded-xl border space-y-1.5 ${
                            isSelected
                              ? 'bg-soft border-brand cursor-pointer'
                              : isOpen
                              ? 'bg-canvas border-line cursor-pointer'
                              : 'bg-canvas border-line opacity-80'
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-bold text-ink">
                                #{rep.report_id} · {rep.reason_label || rep.reason_type}
                              </span>
                              <span className="text-muted">
                                bởi {rep.display_name || rep.username}
                              </span>
                            </div>
                            <span
                              className={`px-2 py-0.5 rounded font-semibold ${
                                rep.status === 'open'
                                  ? 'badge-medium'
                                  : rep.status === 'resolved'
                                  ? 'badge-easy'
                                  : 'badge-neutral'
                              }`}
                            >
                              {rep.status === 'open'
                                ? 'Đang mở'
                                : rep.status === 'resolved'
                                ? 'Đã xử lý'
                                : 'Đã bỏ qua'}
                            </span>
                          </div>
                          <div className="text-xs text-ink whitespace-pre-wrap">
                            {rep.comment}
                          </div>
                          {rep.admin_note && (
                            <div className="text-[11px] text-muted pt-1 border-t border-line">
                              Ghi chú Admin ({rep.resolved_by_username || 'Admin'}): {rep.admin_note}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* 3-Way Resolution Panel for Open Report */}
              {activeOpenReport && (
                <div className="p-4 rounded-xl bg-soft border border-line space-y-3">
                  <div className="text-xs font-bold text-ink">
                    Xử lý báo lỗi đang chọn #{activeOpenReport.report_id} (Human-in-the-loop)
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-ink block">
                      Ghi chú phản hồi của Quản trị viên (tùy chọn)
                    </label>
                    <input
                      value={adminNote}
                      onChange={(e) => setAdminNote(e.target.value)}
                      placeholder="Ghi rõ lý do sửa SQL, thu hồi hoặc bỏ qua báo lỗi…"
                      className="w-full px-3 min-h-9 rounded-lg bg-surface border border-line text-xs text-ink"
                    />
                  </div>

                  {editMode && (
                    <div className="p-3 rounded-lg bg-surface border border-line space-y-2.5">
                      <div className="text-xs font-bold text-ink">
                        Sửa đề / SQL đáp án &amp; Sinh lại Test Case trực tiếp trên PostgreSQL 17
                      </div>
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        placeholder="Tiêu đề câu hỏi"
                        className="w-full px-3 min-h-9 rounded-lg bg-canvas border border-line text-xs text-ink"
                      />
                      <textarea
                        rows={3}
                        value={editQuestion}
                        onChange={(e) => setEditQuestion(e.target.value)}
                        className="w-full p-2.5 rounded-lg bg-canvas border border-line text-xs text-ink"
                      />
                      <textarea
                        rows={4}
                        value={editSql}
                        onChange={(e) => setEditSql(e.target.value)}
                        className="w-full p-2.5 rounded-lg bg-canvas border border-line font-mono text-xs text-ink"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setEditMode(false)}
                          className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                        >
                          Ẩn khung sửa
                        </button>
                        <button
                          type="button"
                          data-solid-btn="true"
                          disabled={busy}
                          onClick={() => handleResolve('rework')}
                          className="btn-primary px-3.5 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap inline-flex items-center gap-1.5"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Lưu SQL &amp; Sinh lại Test</span>
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <button
                      type="button"
                      data-solid-btn="true"
                      disabled={busy}
                      onClick={() => setEditMode((v) => !v)}
                      className="btn-primary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap inline-flex items-center gap-1.5"
                    >
                      <Wrench className="w-3.5 h-3.5" />
                      <span>1A. Sửa SQL &amp; Test Case</span>
                    </button>

                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleResolve('return_needs_human')}
                      className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap inline-flex items-center gap-1.5"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>1B. Thu hồi về Duyệt đề</span>
                    </button>

                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleResolve('retire')}
                      className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold text-danger whitespace-nowrap inline-flex items-center gap-1.5"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>2. Loại bỏ (Retire)</span>
                    </button>

                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleResolve('dismiss')}
                      className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                    >
                      3. Bỏ qua (Dismiss)
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
