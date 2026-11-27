'use client';

import React, { useEffect, useState } from 'react';
import { CheckCircle2, Flag, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import { extractApiError, reportQuestion, voteQuestion } from '@/lib/api';

const REPORT_REASONS = [
  { value: 'ambiguous_prompt', label: 'Đề mơ hồ' },
  { value: 'wrong_difficulty', label: 'Sai độ khó' },
  { value: 'wrong_answer_or_testcase', label: 'Nghi sai đáp án/test case' },
  { value: 'typo_or_column_name', label: 'Lỗi chính tả/tên cột' },
  { value: 'other', label: 'Khác' },
];

export function QuestionFeedbackBar({
  questionId,
  feedback,
  onFeedbackUpdated,
}: {
  questionId?: number | null;
  feedback?: any;
  onFeedbackUpdated?: () => void;
}) {
  const [upvotes, setUpvotes] = useState<number>(0);
  const [downvotes, setDownvotes] = useState<number>(0);
  const [myVote, setMyVote] = useState<number | null>(null);
  const [canVote, setCanVote] = useState<boolean>(false);
  const [openReport, setOpenReport] = useState<any>(null);

  const [voting, setVoting] = useState(false);
  const [inlineMsg, setInlineMsg] = useState<string | null>(null);
  const [inlineErr, setInlineErr] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [reasonType, setReasonType] = useState<string>('ambiguous_prompt');
  const [comment, setComment] = useState<string>('');
  const [submittingReport, setSubmittingReport] = useState(false);

  useEffect(() => {
    setUpvotes(Number(feedback?.upvotes ?? 0));
    setDownvotes(Number(feedback?.downvotes ?? 0));
    setMyVote(
      feedback?.my_vote === 1 || feedback?.my_vote === -1 ? Number(feedback.my_vote) : null
    );
    setCanVote(Boolean(feedback?.can_vote));
    setOpenReport(feedback?.my_open_report || null);
    setInlineMsg(null);
    setInlineErr(null);
  }, [questionId, feedback]);

  if (!questionId) return null;

  const handleVote = async (target: 1 | -1) => {
    setInlineMsg(null);
    setInlineErr(null);
    if (!canVote) {
      setInlineErr('Bạn cần nộp bài ít nhất 1 lần trước khi bình chọn cho câu hỏi này.');
      return;
    }
    const nextVote: 1 | -1 | 0 = myVote === target ? 0 : target;
    setVoting(true);
    try {
      const res = await voteQuestion(questionId, nextVote);
      setUpvotes(Number(res.upvotes ?? 0));
      setDownvotes(Number(res.downvotes ?? 0));
      setMyVote(res.my_vote === 1 || res.my_vote === -1 ? Number(res.my_vote) : null);
      setCanVote(true);
      if (onFeedbackUpdated) onFeedbackUpdated();
    } catch (e: any) {
      setInlineErr(extractApiError(e, 'Không gửi được bình chọn.'));
    } finally {
      setVoting(false);
    }
  };

  const handleReportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setInlineErr(null);
    setInlineMsg(null);
    const trimmed = comment.trim();
    if (trimmed.length < 3) {
      setInlineErr('Vui lòng nhập mô tả ngắn tối thiểu 3 ký tự.');
      return;
    }
    setSubmittingReport(true);
    try {
      const created = await reportQuestion(questionId, {
        reason_type: reasonType,
        comment: trimmed,
      });
      setOpenReport(created);
      setComment('');
      setModalOpen(false);
      setInlineMsg('Đã gửi góp ý / báo lỗi tới Quản trị viên.');
      if (onFeedbackUpdated) onFeedbackUpdated();
    } catch (e: any) {
      setInlineErr(extractApiError(e, 'Không gửi được báo lỗi.'));
    } finally {
      setSubmittingReport(false);
    }
  };

  return (
    <div className="pt-2.5 border-t border-line space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5 tabular-nums">
          <button
            type="button"
            disabled={voting}
            onClick={() => handleVote(1)}
            title={
              canVote
                ? 'Đề bài rõ ràng, hữu ích'
                : 'Nộp bài ít nhất 1 lần để mở khóa bình chọn'
            }
            className={`px-2.5 min-h-8 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 whitespace-nowrap border ${
              myVote === 1
                ? 'badge-easy border-transparent'
                : 'bg-canvas border-line text-text2 hover:text-ink'
            }`}
          >
            <ThumbsUp className="w-3.5 h-3.5" />
            <span>{upvotes}</span>
          </button>

          <button
            type="button"
            disabled={voting}
            onClick={() => handleVote(-1)}
            title={
              canVote
                ? 'Đề bài cần cải thiện'
                : 'Nộp bài ít nhất 1 lần để mở khóa bình chọn'
            }
            className={`px-2.5 min-h-8 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 whitespace-nowrap border ${
              myVote === -1
                ? 'badge-hard border-transparent'
                : 'bg-canvas border-line text-text2 hover:text-ink'
            }`}
          >
            <ThumbsDown className="w-3.5 h-3.5" />
            <span>{downvotes}</span>
          </button>
        </div>

        <button
          type="button"
          onClick={() => {
            setInlineErr(null);
            setModalOpen(true);
          }}
          className={`px-3 min-h-8 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 whitespace-nowrap border ${
            openReport
              ? 'badge-medium border-transparent'
              : 'bg-canvas border-line text-text2 hover:text-ink'
          }`}
        >
          <Flag className="w-3.5 h-3.5" />
          <span>{openReport ? 'Đã báo lỗi (Đang mở)' : 'Báo lỗi / Góp ý'}</span>
        </button>
      </div>

      {inlineMsg && (
        <div className="px-2.5 py-1.5 rounded-lg badge-easy text-xs font-medium flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          <span>{inlineMsg}</span>
        </div>
      )}

      {inlineErr && !modalOpen && (
        <div className="px-2.5 py-1.5 rounded-lg badge-hard text-xs font-medium">
          {inlineErr}
        </div>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-xl bg-surface border border-line overflow-hidden">
            <div className="px-4 py-3 bg-soft border-b border-line flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Flag className="w-4 h-4 text-brand" />
                <span className="text-sm font-bold text-ink">
                  Báo lỗi / Góp ý câu hỏi #{questionId}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-md text-muted hover:text-ink"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {openReport ? (
              <div className="p-4 space-y-3 text-sm">
                <div className="p-3 rounded-lg bg-canvas border border-line space-y-1.5">
                  <div className="text-xs font-semibold text-brand">
                    Loại góp ý: {openReport.reason_label || openReport.reason_type}
                  </div>
                  <div className="text-xs text-ink whitespace-pre-wrap">
                    {openReport.comment}
                  </div>
                </div>
                <p className="text-xs text-muted leading-relaxed">
                  Bạn đang có 1 báo lỗi chờ Quản trị viên xem xét cho câu hỏi này. Sau khi báo lỗi được xử lý, bạn có thể gửi góp ý mới nếu cần.
                </p>
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="btn-secondary px-4 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                  >
                    Đóng
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleReportSubmit} className="p-4 space-y-3 text-sm">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink block">
                    Phân loại vấn đề
                  </label>
                  <select
                    value={reasonType}
                    onChange={(e) => setReasonType(e.target.value)}
                    className="w-full px-3 min-h-10 rounded-lg bg-canvas border border-line text-sm text-ink"
                  >
                    {REPORT_REASONS.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink block">
                    Mô tả chi tiết ngắn gọn
                  </label>
                  <textarea
                    rows={3}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Nêu điểm chưa rõ trong đề bài, tên cột hoặc kết quả mong đợi…"
                    className="w-full p-3 rounded-lg bg-canvas border border-line text-sm text-ink"
                  />
                </div>

                <p className="text-xs text-muted leading-relaxed">
                  Hệ thống ghi nhận góp ý để Quản trị viên rà soát thủ công; câu hỏi vẫn mở bình thường trong lúc chờ xử lý.
                </p>

                {inlineErr && (
                  <div className="px-2.5 py-1.5 rounded-lg badge-hard text-xs font-medium">
                    {inlineErr}
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="btn-secondary px-3.5 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    data-solid-btn="true"
                    disabled={submittingReport}
                    className="btn-primary px-4 min-h-9 rounded-lg text-xs font-semibold whitespace-nowrap disabled:opacity-50"
                  >
                    {submittingReport ? 'Đang gửi…' : 'Gửi góp ý'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
