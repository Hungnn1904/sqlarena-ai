'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  CheckCircle2,
  CornerDownRight,
  Lock,
  MessageSquare,
  Send,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import {
  deleteQuestionComment,
  extractApiError,
  getQuestionComments,
  postQuestionComment,
} from '@/lib/api';

function ReputationBadge({
  badge,
  label,
}: {
  badge?: string | null;
  label?: string | null;
}) {
  if (badge === 'admin') {
    return (
      <span className="badge-info px-2 py-0.5 rounded text-[11px] font-semibold inline-flex items-center gap-1 whitespace-nowrap">
        <ShieldCheck className="w-3 h-3" />
        <span>{label || 'Quản trị viên'}</span>
      </span>
    );
  }
  if (badge === 'solved') {
    return (
      <span className="badge-easy px-2 py-0.5 rounded text-[11px] font-semibold inline-flex items-center gap-1 whitespace-nowrap">
        <CheckCircle2 className="w-3 h-3" />
        <span>{label || 'Đã giải đúng'}</span>
      </span>
    );
  }
  return (
    <span className="badge-neutral px-2 py-0.5 rounded text-[11px] font-semibold whitespace-nowrap">
      {label || 'Đã thử làm'}
    </span>
  );
}

export function QuestionDiscussionCard({
  questionId,
  refreshToken,
}: {
  questionId?: number | null;
  refreshToken?: number;
}) {
  const [items, setItems] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [canComment, setCanComment] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const [newContent, setNewContent] = useState<string>('');
  const [postingRoot, setPostingRoot] = useState<boolean>(false);

  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyContent, setReplyContent] = useState<string>('');
  const [postingReply, setPostingReply] = useState<boolean>(false);

  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const prevQuestionIdRef = useRef<number | null>(null);
  const activeQuestionIdRef = useRef<number | null>(null);
  activeQuestionIdRef.current = questionId ?? null;

  const loadComments = async (qid: number, shouldIgnore?: () => boolean) => {
    setLoading(true);
    try {
      const res = await getQuestionComments(qid);
      if (shouldIgnore?.() || activeQuestionIdRef.current !== qid) return;
      setItems(Array.isArray(res?.items) ? res.items : []);
      setTotalCount(Number(res?.total_count ?? 0));
      setCanComment(Boolean(res?.can_comment));
    } catch (e: any) {
      if (shouldIgnore?.() || activeQuestionIdRef.current !== qid) return;
      setErr(extractApiError(e, 'Không tải được khu vực thảo luận.'));
    } finally {
      if (!shouldIgnore?.() && activeQuestionIdRef.current === qid) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    let cancelled = false;
    if (prevQuestionIdRef.current !== (questionId ?? null)) {
      prevQuestionIdRef.current = questionId ?? null;
      setItems([]);
      setTotalCount(0);
      setCanComment(false);
      setNewContent('');
      setReplyingToId(null);
      setReplyContent('');
      setErr(null);
    }
    if (questionId) {
      loadComments(questionId, () => cancelled);
    }
    return () => {
      cancelled = true;
    };
  }, [questionId, refreshToken]);

  if (!questionId) return null;

  const handlePostRoot = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    const trimmed = newContent.trim();
    if (trimmed.length < 2) {
      setErr('Nội dung bình luận cần tối thiểu 2 ký tự.');
      return;
    }
    setPostingRoot(true);
    try {
      await postQuestionComment(questionId, { content: trimmed });
      setNewContent('');
      await loadComments(questionId);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không đăng được bình luận.'));
    } finally {
      setPostingRoot(false);
    }
  };

  const handlePostReply = async (e: React.FormEvent, parentId: number) => {
    e.preventDefault();
    setErr(null);
    const trimmed = replyContent.trim();
    if (trimmed.length < 2) {
      setErr('Nội dung trả lời cần tối thiểu 2 ký tự.');
      return;
    }
    setPostingReply(true);
    try {
      await postQuestionComment(questionId, {
        content: trimmed,
        parent_comment_id: parentId,
      });
      setReplyContent('');
      setReplyingToId(null);
      await loadComments(questionId);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không gửi được câu trả lời.'));
    } finally {
      setPostingReply(false);
    }
  };

  const handleDelete = async (commentId: number) => {
    setErr(null);
    setDeletingId(commentId);
    try {
      await deleteQuestionComment(questionId, commentId);
      await loadComments(questionId);
    } catch (e: any) {
      setErr(extractApiError(e, 'Không xóa được bình luận.'));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="rounded-xl bg-surface border border-line overflow-hidden">
      <div className="px-5 py-3.5 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-brand shrink-0" />
          <h2 className="text-base font-bold text-ink tabular-nums">
            Thảo luận ({totalCount})
          </h2>
        </div>
        <span className="text-xs text-muted">
          Trao đổi hướng tiếp cận, giải thích logic SQL và hỗ trợ nhau cùng tiến bộ
        </span>
      </div>

      <div className="p-5 space-y-4">
        {/* Composer or Soft-Locked Banner */}
        {canComment ? (
          <form onSubmit={handlePostRoot} className="space-y-2.5">
            <textarea
              rows={3}
              maxLength={2000}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Chia sẻ cách tư duy truy vấn, lưu ý JOIN/NULL hoặc đặt câu hỏi cho bài này…"
              className="w-full p-3 rounded-xl bg-canvas border border-line text-sm text-ink"
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted tabular-nums">
                {newContent.trim().length}/2000 ký tự
              </span>
              <button
                type="submit"
                data-solid-btn="true"
                disabled={postingRoot || newContent.trim().length < 2}
                className="btn-primary px-4 min-h-9 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 whitespace-nowrap disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{postingRoot ? 'Đang đăng…' : 'Đăng bình luận'}</span>
              </button>
            </div>
          </form>
        ) : (
          <div className="p-3.5 rounded-xl bg-soft border border-line flex items-center gap-2.5 text-sm text-text2">
            <Lock className="w-4 h-4 text-muted shrink-0" />
            <span>Nộp bài ít nhất 1 lần để tham gia thảo luận</span>
          </div>
        )}

        {err && (
          <div className="px-3 py-2 rounded-lg badge-hard text-xs font-medium">{err}</div>
        )}

        {/* Discussion Thread List */}
        {loading && items.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted">
            Đang tải danh sách thảo luận…
          </div>
        ) : items.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted bg-canvas rounded-xl border border-line">
            Chưa có bình luận nào cho câu hỏi này. Hãy nộp bài thử sức và mở đầu cuộc thảo luận.
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((c: any) => {
              const replies: any[] = Array.isArray(c.replies) ? c.replies : [];
              const isReplying = replyingToId === c.comment_id;
              return (
                <div
                  key={c.comment_id}
                  className="p-4 rounded-xl bg-canvas border border-line space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-bold text-ink">
                        {c.display_name || c.username}
                      </span>
                      <ReputationBadge
                        badge={c.author_badge}
                        label={c.author_badge_label}
                      />
                      <span className="text-xs text-muted tabular-nums">
                        {c.created_at
                          ? new Date(c.created_at).toLocaleString('vi-VN')
                          : ''}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {canComment && (
                        <button
                          type="button"
                          onClick={() => {
                            setReplyingToId(isReplying ? null : c.comment_id);
                            setReplyContent('');
                          }}
                          className="btn-secondary px-2.5 min-h-7 rounded-md text-xs font-semibold inline-flex items-center gap-1 whitespace-nowrap"
                        >
                          <CornerDownRight className="w-3 h-3" />
                          <span>Trả lời</span>
                        </button>
                      )}
                      {c.can_delete && (
                        <button
                          type="button"
                          disabled={deletingId === c.comment_id}
                          onClick={() => handleDelete(c.comment_id)}
                          className="btn-secondary px-2.5 min-h-7 rounded-md text-xs font-semibold text-danger inline-flex items-center gap-1 whitespace-nowrap"
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>Xóa bình luận</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="text-sm text-ink whitespace-pre-wrap break-words leading-relaxed">
                    {c.content}
                  </div>

                  {/* 1-Level Replies */}
                  {replies.length > 0 && (
                    <div className="pl-4 border-l-2 border-line space-y-2.5 pt-1">
                      {replies.map((r: any) => (
                        <div
                          key={r.comment_id}
                          className="p-3 rounded-lg bg-surface border border-line space-y-1.5"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-bold text-ink">
                                {r.display_name || r.username}
                              </span>
                              <ReputationBadge
                                badge={r.author_badge}
                                label={r.author_badge_label}
                              />
                              <span className="text-[11px] text-muted tabular-nums">
                                {r.created_at
                                  ? new Date(r.created_at).toLocaleString('vi-VN')
                                  : ''}
                              </span>
                            </div>

                            {r.can_delete && (
                              <button
                                type="button"
                                disabled={deletingId === r.comment_id}
                                onClick={() => handleDelete(r.comment_id)}
                                className="btn-secondary px-2 min-h-7 rounded-md text-[11px] font-semibold text-danger inline-flex items-center gap-1 whitespace-nowrap"
                              >
                                <Trash2 className="w-3 h-3" />
                                <span>Xóa bình luận</span>
                              </button>
                            )}
                          </div>
                          <div className="text-sm text-ink whitespace-pre-wrap break-words leading-relaxed">
                            {r.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Inline 1-Level Reply Form */}
                  {isReplying && canComment && (
                    <form
                      onSubmit={(ev) => handlePostReply(ev, c.comment_id)}
                      className="pl-4 border-l-2 border-brand space-y-2 pt-1"
                    >
                      <textarea
                        rows={2}
                        maxLength={2000}
                        value={replyContent}
                        onChange={(e) => setReplyContent(e.target.value)}
                        placeholder={`Trả lời ${c.display_name || c.username}…`}
                        className="w-full p-2.5 rounded-lg bg-surface border border-line text-sm text-ink"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setReplyingToId(null)}
                          className="btn-secondary px-3 min-h-8 rounded-lg text-xs font-semibold whitespace-nowrap"
                        >
                          Hủy
                        </button>
                        <button
                          type="submit"
                          data-solid-btn="true"
                          disabled={postingReply || replyContent.trim().length < 2}
                          className="btn-primary px-3.5 min-h-8 rounded-lg text-xs font-semibold inline-flex items-center gap-1 whitespace-nowrap disabled:opacity-50"
                        >
                          <Send className="w-3 h-3" />
                          <span>{postingReply ? 'Đang gửi…' : 'Gửi trả lời'}</span>
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
