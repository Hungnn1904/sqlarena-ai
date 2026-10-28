'use client';

import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  Award,
  TrendingUp,
  Calendar,
} from 'lucide-react';
import {
  getMyProgress,
  getWeeklyLeaderboard,
  getMonthlyLeaderboard,
} from '../lib/api';

const SKILL_DESCRIPTIONS: Record<string, string> = {
  S1: 'Truy vấn cơ bản, lọc điều kiện WHERE, ORDER BY, LIMIT và xử lý biểu thức đơn bảng.',
  S2: 'Kết nối đa bảng INNER/LEFT JOIN, kiểm soát bội số dòng (row grain) và quan hệ khóa ngoại.',
  S3: 'Tổng hợp dữ liệu GROUP BY, hàm агрегат COUNT/SUM/AVG và lọc nhóm với HAVING.',
  S4: 'Truy vấn con (Subquery), mệnh đề EXISTS/NOT EXISTS và bảng tạm CTE (WITH).',
  S5: 'Hàm cửa sổ nâng cao ROW_NUMBER, RANK, DENSE_RANK, LAG/LEAD và phân vùng PARTITION BY.',
  S6: 'Xử lý bẫy NULL (COALESCE, NULLIF), ép kiểu tiền tệ/thập phân, ngày giờ và điều kiện biên.',
};

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
      <div className="p-10 bg-[#0d1321] border border-[#1d283a] rounded-lg text-center text-xs font-mono text-[#64748b]">
        Đang tổng hợp dữ liệu phân tích học tập...
      </div>
    );
  }

  const summary = data?.summary || {};
  const skills = data?.skills || [];
  const recent = data?.recent_submissions || [];

  return (
    <div className="space-y-5">
      {/* Clean Telemetry Summary Strip */}
      <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg divide-y md:divide-y-0 md:divide-x divide-[#1d283a] grid grid-cols-1 md:grid-cols-4">
        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Bài tập đã hoàn thành
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-semibold font-mono text-white">
              {summary.solved_questions ?? 0}
            </span>
            <span className="text-xs font-mono text-emerald-400">
              / {summary.attempted_questions ?? 0} bài đã thử
            </span>
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Tổng số lượt nộp (Submissions)
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-semibold font-mono text-white">
              {summary.total_submissions ?? 0}
            </span>
            <span className="text-xs font-mono text-[#38bdf8]">
              ({summary.passed_submissions ?? 0} lượt Accepted)
            </span>
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Tỷ lệ chính xác (Pass Rate)
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-semibold font-mono text-white">
              {summary.accuracy_percent ?? 0}%
            </span>
            <span className="text-xs font-mono text-[#64748b]">
              trên tập kiểm thử chuẩn
            </span>
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Chu kỳ đánh giá hiện tại
          </div>
          <div className="mt-1.5">
            <div className="text-sm font-medium text-white truncate">
              {data?.weekly_set?.title || 'Tuần #42 — Enterprise SQL'}
            </div>
            <div className="text-[11px] font-mono text-[#64748b] mt-0.5">
              Bắt đầu: {data?.weekly_set?.week_start || '2026-10-26'}
            </div>
          </div>
        </div>
      </div>

      {/* 6 Core SQL Competency Matrix */}
      <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
        <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#38bdf8]" />
            <h3 className="text-sm font-semibold text-white">
              Ma trận Năng lực 6 Nhóm Kỹ năng SQL (Taxonomy S1–S6)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-[#64748b]">
            Đo lường tự động từ kết quả thực thi trên EnterpriseDB
          </span>
        </div>

        <div className="p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {skills.map((sk: any) => {
            const pct = sk.percent || 0;
            return (
              <div
                key={sk.skill_id}
                className="p-4 rounded-md bg-[#090d16] border border-[#192336] flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#131d31] text-[#38bdf8] border border-[#223456]">
                      {sk.code}
                    </span>
                    <span className="text-xs font-mono text-[#94a3b8]">
                      {sk.passed_questions}/{sk.total_questions} câu ({pct}%)
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-white mb-1">
                    {sk.name}
                  </div>
                  <p className="text-xs text-[#64748b] leading-relaxed mb-4">
                    {SKILL_DESCRIPTIONS[sk.code] || sk.category}
                  </p>
                </div>

                <div className="w-full h-1.5 rounded-full bg-[#162032] overflow-hidden">
                  <div
                    className="h-full bg-[#38bdf8] transition-all duration-300"
                    style={{ width: `${Math.min(100, pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Submission Audit Log */}
      <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
        <div className="px-5 py-3.5 bg-[#090d16] border-b border-[#1d283a] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            Nhật ký Nộp bài & Chấm điểm Gần đây
          </h3>
          <span className="text-[11px] font-mono text-[#64748b]">
            20 bản ghi mới nhất từ live.submissions
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#0a0f1a] border-b border-[#1d283a] text-[#64748b] font-mono">
                <th className="py-2.5 px-4">SUBMISSION ID</th>
                <th className="py-2.5 px-4">BÀI TẬP</th>
                <th className="py-2.5 px-4">TRẠNG THÁI</th>
                <th className="py-2.5 px-4">ĐIỂM</th>
                <th className="py-2.5 px-4">THỜI GIAN CHẠY</th>
                <th className="py-2.5 px-4">THỜI ĐIỂM NỘP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#151f30]">
              {recent.map((s: any) => {
                const isPass = s.submission_status === 'passed';
                return (
                  <tr key={s.submission_id} className="hover:bg-[#101829]">
                    <td className="py-2.5 px-4 font-mono text-[#64748b]">
                      #{s.submission_id}
                    </td>
                    <td className="py-2.5 px-4 text-white font-medium">
                      <span className="font-mono text-[#64748b] mr-2">
                        Q-{s.question_id}
                      </span>
                      {s.question_title}
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 font-mono px-2 py-0.5 rounded text-[11px] border ${
                          isPass
                            ? 'bg-emerald-950/50 text-emerald-300 border-emerald-800/60'
                            : 'bg-rose-950/50 text-rose-300 border-rose-800/60'
                        }`}
                      >
                        {isPass ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        {s.submission_status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-white">
                      {s.score}/100
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[#94a3b8]">
                      {s.runtime_ms} ms
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[#64748b]">
                      {s.submitted_at
                        ? new Date(s.submitted_at).toLocaleString('vi-VN')
                        : '-'}
                    </td>
                  </tr>
                );
              })}
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

  useEffect(() => {
    getWeeklyLeaderboard().then(setWeeklyData).catch(() => null);
    getMonthlyLeaderboard().then(setMonthlyData).catch(() => null);
  }, []);

  const currentItems =
    mode === 'weekly' ? weeklyData?.items || [] : monthlyData?.items || [];
  const topThree = currentItems.slice(0, 3);

  return (
    <div className="space-y-5">
      {/* Header & Period Switcher */}
      <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg p-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#38bdf8] mb-1">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>COMPETITIVE SQL STANDINGS</span>
          </div>
          <h2 className="text-base font-semibold text-white">
            {mode === 'weekly'
              ? weeklyData?.set?.title || 'Bảng Xếp Hạng Bộ Đề Tuần Hiện Tại'
              : `Bảng Xếp Hạng Tổng Hợp Tháng ${monthlyData?.month || 10}/${monthlyData?.year || 2026}`}
          </h2>
          <p className="text-xs text-[#64748b] mt-0.5">
            Xếp hạng tính theo tổng số bài giải đúng (First-Pass Score) và thời gian hoàn thành sớm nhất.
          </p>
        </div>

        <div className="flex items-center bg-[#090d16] p-1 rounded-md border border-[#1d283a]">
          <button
            onClick={() => setMode('weekly')}
            className={`px-3.5 py-1.5 rounded text-xs font-medium flex items-center gap-1.5 transition ${
              mode === 'weekly'
                ? 'bg-[#162238] text-white border border-[#293f66]'
                : 'text-[#64748b] hover:text-white'
            }`}
          >
            <Award className="w-3.5 h-3.5 text-[#38bdf8]" />
            <span>Bảng tuần hiện tại</span>
          </button>
          <button
            onClick={() => setMode('monthly')}
            className={`px-3.5 py-1.5 rounded text-xs font-medium flex items-center gap-1.5 transition ${
              mode === 'monthly'
                ? 'bg-[#162238] text-white border border-[#293f66]'
                : 'text-[#64748b] hover:text-white'
            }`}
          >
            <Calendar className="w-3.5 h-3.5 text-amber-400" />
            <span>
              Bảng tháng {monthlyData?.month || 10}/{monthlyData?.year || 2026}
            </span>
          </button>
        </div>
      </div>

      {/* Top 3 Podium Cards */}
      {topThree.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {topThree.map((r: any, idx: number) => {
            const borderColors = [
              'border-amber-500/40 bg-gradient-to-b from-amber-950/15 to-[#0d1321]',
              'border-slate-500/40 bg-[#0d1321]',
              'border-orange-800/40 bg-[#0d1321]',
            ];
            const rankBadges = [
              'bg-amber-500/15 text-amber-300 border-amber-500/40',
              'bg-slate-500/15 text-slate-300 border-slate-500/40',
              'bg-orange-500/15 text-orange-300 border-orange-500/40',
            ];
            return (
              <div
                key={r.user_id}
                className={`border rounded-lg p-4 ${borderColors[idx] || borderColors[1]}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`text-xs font-mono px-2 py-0.5 rounded border ${rankBadges[idx]}`}
                  >
                    RANK #{r.rank}
                  </span>
                  <span className="text-xs font-mono text-[#94a3b8] flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {r.avg_runtime_ms} ms
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded bg-[#162032] border border-[#263552] flex items-center justify-center font-mono text-sm font-semibold text-white">
                    {(r.display_name || r.username).slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">
                      {r.display_name}
                    </div>
                    <div className="text-xs font-mono text-[#64748b]">
                      @{r.username}
                    </div>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-[#192336] flex items-center justify-between text-xs font-mono">
                  <span className="text-emerald-400">
                    Solved: {r.correct_count ?? r.solved_count} bài
                  </span>
                  <span className="text-white font-semibold text-sm">
                    {r.total_score} pts
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Full Standings Table */}
      <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#090d16] border-b border-[#1d283a] text-[#64748b] font-mono">
                <th className="py-3 px-4 w-20">HẠNG</th>
                <th className="py-3 px-4">THÀNH VIÊN</th>
                <th className="py-3 px-4">SỐ CÂU ĐÚNG</th>
                <th className="py-3 px-4">TỔNG ĐIỂM</th>
                <th className="py-3 px-4">LATENCY TB</th>
                <th className="py-3 px-4">THỜI ĐIỂM XÁC LẬP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#151f30]">
              {currentItems.map((r: any) => (
                <tr key={r.user_id} className="hover:bg-[#101829]">
                  <td className="py-3 px-4 font-mono font-semibold text-white">
                    #{String(r.rank).padStart(2, '0')}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-medium text-white">{r.display_name}</div>
                    <div className="font-mono text-[11px] text-[#64748b]">
                      @{r.username}
                    </div>
                  </td>
                  <td className="py-3 px-4 font-mono text-emerald-400 font-medium">
                    {r.correct_count ?? r.solved_count} bài
                  </td>
                  <td className="py-3 px-4 font-mono text-white font-semibold">
                    {r.total_score} pts
                  </td>
                  <td className="py-3 px-4 font-mono text-[#94a3b8]">
                    {r.avg_runtime_ms} ms
                  </td>
                  <td className="py-3 px-4 font-mono text-[#64748b]">
                    {r.completed_at
                      ? new Date(r.completed_at).toLocaleString('vi-VN')
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
