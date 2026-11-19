'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Activity,
  Award,
} from 'lucide-react';
import {
  getMyProgress,
  getWeeklyLeaderboard,
  getMonthlyLeaderboard,
  getWeeklyHistory,
} from '../lib/api';

function resolveSubmissionOutcome(s: any): {
  label: 'Làm được' | 'RTE' | 'Chưa làm được';
  badgeClass: string;
  Icon: typeof CheckCircle2;
} {
  if (s.submission_status === 'passed') {
    return {
      label: 'Làm được',
      badgeClass: 'badge-easy',
      Icon: CheckCircle2,
    };
  }
  const isWrongAnswerMismatch =
    typeof s.error_message === 'string' &&
    s.error_message.includes('Kết quả truy vấn chưa khớp');
  const isRte =
    s.submission_status === 'error' ||
    s.execution_status === 'timeout' ||
    (s.execution_status === 'error' && !isWrongAnswerMismatch);

  if (isRte) {
    return {
      label: 'RTE',
      badgeClass: 'badge-medium',
      Icon: AlertTriangle,
    };
  }
  return {
    label: 'Chưa làm được',
    badgeClass: 'badge-hard',
    Icon: XCircle,
  };
}

export function LearnerProgressView() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyProgress()
      .then(setData)
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-10 bg-surface border border-line rounded-xl text-center text-sm text-muted">
        Đang tải dữ liệu tiến độ học tập…
      </div>
    );
  }

  const summary = data?.summary || {};
  const skills = data?.skills || [];
  const recent = data?.recent_submissions || [];

  return (
    <div className="space-y-5">
      {/* Telemetry Summary Strip */}
      <div className="bg-surface border border-line rounded-xl divide-y md:divide-y-0 md:divide-x divide-line grid grid-cols-1 md:grid-cols-4 tabular-nums">
        <div className="p-5">
          <div className="text-xs font-medium text-muted">
            Số bài đã giải đúng
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink">
              {summary.solved_questions ?? 0}
            </span>
            <span className="text-sm font-medium text-brand">
              trên {summary.attempted_questions ?? 0} bài đã thử
            </span>
          </div>
        </div>

        <div className="p-5">
          <div className="text-xs font-medium text-muted">
            Tổng số lượt nộp bài
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink">
              {summary.total_submissions ?? 0}
            </span>
            <span className="text-sm font-medium text-text2">
              ({summary.passed_submissions ?? 0} lượt làm được)
            </span>
          </div>
        </div>

        <div className="p-5">
          <div className="text-xs font-medium text-muted">
            Tỷ lệ chính xác
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink">
              {summary.accuracy_percent ?? 0}%
            </span>
          </div>
        </div>

        <div className="p-5">
          <div className="text-xs font-medium text-muted">
            Bộ đề đang tham gia
          </div>
          <div className="mt-1.5">
            <div className="text-base font-semibold text-ink truncate">
              {data?.weekly_set?.title || 'Bộ đề thực hành hiện tại'}
            </div>
          </div>
        </div>
      </div>

      {/* 6 Core SQL Competency Matrix */}
      <div className="bg-surface border border-line rounded-xl overflow-hidden">
        <div className="px-5 py-4 bg-soft border-b border-line flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand" />
            <h3 className="text-base font-bold text-ink">
              Mức độ thành thạo 6 nhóm kỹ năng SQL (S1 đến S6)
            </h3>
          </div>
        </div>

        <div className="p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 tabular-nums">
          {skills.length === 0 ? (
            <div className="col-span-full py-6 text-center text-sm text-muted">
              Hãy hoàn thành bài tập đầu tiên để mở khóa biểu đồ kỹ năng SQL.
            </div>
          ) : (
            skills.map((sk: any, idx: number) => {
              const pct = Math.min(100, Math.max(0, Number(sk.percent || 0)));
              return (
                <div
                  key={sk.skill_id || idx}
                  className="p-4 rounded-xl bg-canvas border border-line flex flex-col justify-between gap-3"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <code className="text-xs font-semibold px-2 py-0.5 rounded badge-info">
                        {sk.code}
                      </code>
                      <span className="text-xs text-muted">
                        {sk.passed_questions}/{sk.total_questions} câu ({pct}%)
                      </span>
                    </div>
                    <div className="text-sm font-semibold text-ink">
                      {sk.name}
                    </div>
                  </div>

                  <div className="w-full h-2 rounded-full bg-soft overflow-hidden">
                    <motion.div
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: pct / 100 }}
                      transition={{ duration: 0.35, ease: 'easeOut' }}
                      style={{ transformOrigin: 'left center' }}
                      className="h-full w-full bg-brand"
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Submission Audit Log (No Score Column, Strictly 3 Clear Verdicts) */}
      <div className="bg-surface border border-line rounded-xl overflow-hidden">
        <div className="px-5 py-4 bg-soft border-b border-line flex items-center justify-between">
          <h3 className="text-base font-bold text-ink">
            Lịch sử nộp bài gần đây
          </h3>
          <span className="text-xs text-muted">
            20 lượt nộp mới nhất
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm tabular-nums">
            <thead>
              <tr className="bg-canvas border-b border-line text-text2 font-semibold">
                <th className="py-3 px-4">Mã lượt nộp</th>
                <th className="py-3 px-4">Bài tập</th>
                <th className="py-3 px-4">Trạng thái</th>
                <th className="py-3 px-4">Thời gian chạy</th>
                <th className="py-3 px-4">Thời điểm nộp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-sm text-muted">
                    Chưa có lịch sử nộp bài.
                  </td>
                </tr>
              ) : (
                recent.map((s: any) => {
                  const outcome = resolveSubmissionOutcome(s);
                  const OutcomeIcon = outcome.Icon;
                  return (
                    <tr key={s.submission_id} className="hover:bg-soft transition-colors">
                      <td className="py-3 px-4 text-muted">
                        <code>#{s.submission_id}</code>
                      </td>
                      <td className="py-3 px-4 text-ink font-medium">
                        <code className="text-brand font-semibold mr-2">
                          SQL{s.question_id}
                        </code>
                        <span>{s.question_title}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-semibold ${outcome.badgeClass}`}
                        >
                          <OutcomeIcon className="w-3.5 h-3.5" />
                          <span>{outcome.label}</span>
                        </span>
                      </td>
                      <td className="py-3 px-4 text-text2">
                        {s.runtime_ms ?? 0} ms
                      </td>
                      <td className="py-3 px-4 text-muted">
                        {s.submitted_at
                          ? new Date(s.submitted_at).toLocaleString('vi-VN')
                          : '-'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function LeaderboardView() {
  const [mode, setMode] = useState<'weekly' | 'monthly'>('weekly');
  const [weeklyData, setWeeklyData] = useState<any>(null);
  const [monthlyData, setMonthlyData] = useState<any>(null);
  const [historySets, setHistorySets] = useState<any[]>([]);
  const [selectedSetId, setSelectedSetId] = useState<number | undefined>(undefined);
  const currentMonthStr = new Date().toISOString().slice(0, 7);
  const [selectedPeriod, setSelectedPeriod] = useState<string>(currentMonthStr);

  useEffect(() => {
    getWeeklyHistory(1)
      .then((res) => setHistorySets(res?.items || []))
      .catch(() => null);
  }, []);

  useEffect(() => {
    getWeeklyLeaderboard(selectedSetId).then(setWeeklyData).catch(() => null);
  }, [selectedSetId]);

  useEffect(() => {
    const [yr, mo] = selectedPeriod.split('-').map(Number);
    getMonthlyLeaderboard(yr, mo).then(setMonthlyData).catch(() => null);
  }, [selectedPeriod]);

  const currentItems =
    mode === 'weekly' ? weeklyData?.items || [] : monthlyData?.items || [];

  const rankOne = currentItems[0] || null;
  const rankTwo = currentItems[1] || null;
  const rankThree = currentItems[2] || null;

  // Olympic Podium slots: Left = #2, Center = #1 (Tallest), Right = #3
  const podiumSlots = [
    {
      slotKey: 'rank-2',
      entry: rankTwo,
      fallbackRank: 2,
      heightClass: 'min-h-[172px]',
      orderClass: 'order-2 md:order-1',
    },
    {
      slotKey: 'rank-1',
      entry: rankOne,
      fallbackRank: 1,
      heightClass: 'min-h-[212px]',
      orderClass: 'order-1 md:order-2',
    },
    {
      slotKey: 'rank-3',
      entry: rankThree,
      fallbackRank: 3,
      heightClass: 'min-h-[148px]',
      orderClass: 'order-3 md:order-3',
    },
  ];

  return (
    <div className="space-y-5">
      {/* Period Switcher */}
      <div className="p-4 rounded-xl bg-surface border border-line flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          {mode === 'weekly' && (
            <select
              value={selectedSetId ?? ''}
              onChange={(e) =>
                setSelectedSetId(e.target.value ? Number(e.target.value) : undefined)
              }
              className="px-3.5 min-h-10 rounded-lg text-sm bg-canvas text-ink border border-line"
            >
              <option value="">Bộ đề tuần đang mở</option>
              {historySets.map((s: any) => (
                <option key={s.set_id} value={s.set_id}>
                  #{s.set_id}: {s.title} ({s.status})
                </option>
              ))}
            </select>
          )}
          {mode === 'monthly' && (
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="px-3.5 min-h-10 rounded-lg text-sm bg-canvas text-ink border border-line"
            >
              {!['2026-10', '2026-09', '2026-08', '2026-04', '2025-03'].includes(currentMonthStr) && (
                <option value={currentMonthStr}>Tháng hiện tại ({currentMonthStr})</option>
              )}
              <option value="2026-10">Tháng 10/2026</option>
              <option value="2026-09">Tháng 09/2026</option>
              <option value="2026-08">Tháng 08/2026</option>
              <option value="2026-04">Tháng 04/2026</option>
              <option value="2025-03">Tháng 03/2025</option>
            </select>
          )}
        </div>

        <div className="flex items-center bg-soft p-1 rounded-lg border border-line gap-1">
          <button
            type="button"
            data-solid-btn={mode === 'weekly' ? 'true' : undefined}
            onClick={() => setMode('weekly')}
            className={`px-4 min-h-9 rounded-md text-sm font-semibold whitespace-nowrap ${
              mode === 'weekly' ? 'btn-primary' : 'text-text2 hover:text-ink'
            }`}
          >
            Xếp hạng Tuần
          </button>
          <button
            type="button"
            data-solid-btn={mode === 'monthly' ? 'true' : undefined}
            onClick={() => setMode('monthly')}
            className={`px-4 min-h-9 rounded-md text-sm font-semibold whitespace-nowrap ${
              mode === 'monthly' ? 'btn-primary' : 'text-text2 hover:text-ink'
            }`}
          >
            Xếp hạng Tháng
          </button>
        </div>
      </div>

      {/* Olympic Top 3 Podium (#2 Left, #1 Center Tallest, #3 Right — Unified Single Brand Tone) */}
      {currentItems.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end tabular-nums pt-2">
          {podiumSlots.map((slot) => {
            const r = slot.entry;
            if (!r) {
              return (
                <div
                  key={slot.slotKey}
                  className={`hidden md:flex ${slot.orderClass} ${slot.heightClass} bg-surface border border-dashed border-line rounded-2xl p-5 flex-col justify-between opacity-60`}
                >
                  <span className="inline-flex items-center gap-1.5 self-start text-xs font-semibold px-2.5 py-1 rounded-md badge-easy">
                    <Award className="w-3.5 h-3.5" />
                    <span>Hạng #{slot.fallbackRank}</span>
                  </span>
                  <div className="text-xs text-muted">Chưa có học viên ở vị trí này</div>
                </div>
              );
            }

            const solvedNum = r.correct_count ?? r.solved_count ?? 0;
            const isFirst = slot.fallbackRank === 1;

            return (
              <div
                key={r.user_id ?? slot.slotKey}
                className={`${slot.orderClass} ${slot.heightClass} bg-surface border ${
                  isFirst ? 'border-2 border-brand' : 'border-[var(--green-border)]'
                } rounded-2xl p-5 flex flex-col justify-between gap-3`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md badge-easy">
                    <Award className="w-3.5 h-3.5" />
                    <span>Hạng #{r.rank ?? slot.fallbackRank}</span>
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div
                    data-solid-btn="true"
                    className={`${
                      isFirst ? 'w-12 h-12 text-base' : 'w-10 h-10 text-sm'
                    } rounded-xl btn-primary flex items-center justify-center font-bold shrink-0`}
                  >
                    {(r.display_name || r.username).slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div
                      className={`${
                        isFirst ? 'text-lg' : 'text-base'
                      } font-bold text-ink truncate`}
                    >
                      {r.display_name || r.username}
                    </div>
                    <div className="text-xs text-muted truncate">
                      @{r.username}
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-line flex items-center justify-between text-sm">
                  <span className="text-text2 font-medium">Câu đúng</span>
                  <span className="text-brand font-bold">
                    {solvedNum} câu
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Full Standings Table (Strictly Rank, Learner, Correct Count — No Score, No Speed) */}
      <div className="bg-surface border border-line rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm tabular-nums">
            <thead>
              <tr className="bg-soft border-b border-line text-text2 font-semibold">
                <th className="py-3.5 px-4 w-28">Hạng</th>
                <th className="py-3.5 px-4">Học viên</th>
                <th className="py-3.5 px-4 w-44">Câu đúng</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {currentItems.length === 0 ? (
                <tr>
                  <td colSpan={3} className="py-10 text-center text-sm text-muted">
                    Chưa có dữ liệu bảng xếp hạng cho kỳ này.
                  </td>
                </tr>
              ) : (
                currentItems.map((r: any) => (
                  <tr key={r.user_id} className="hover:bg-soft transition-colors">
                    <td className="py-3.5 px-4 font-bold text-ink">
                      #{r.rank}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-ink">{r.display_name || r.username}</div>
                      <div className="text-xs text-muted">@{r.username}</div>
                    </td>
                    <td className="py-3.5 px-4 text-brand font-semibold">
                      {r.correct_count ?? r.solved_count ?? 0} câu
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
