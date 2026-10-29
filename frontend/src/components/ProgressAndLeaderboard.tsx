'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
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
        Đang tải dữ liệu...
      </div>
    );
  }

  const summary = data?.summary || {};
  const skills = data?.skills || [];
  const recent = data?.recent_submissions || [];

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] font-bold tracking-[0.15em] uppercase text-[var(--copper)]">
          THEO DÕI NĂNG LỰC
        </div>
        <h2 className="text-2xl font-bold text-[var(--ink)] mt-0.5">
          Tiến độ <span className="editorial-serif text-[var(--green)]">kỹ năng SQL.</span>
        </h2>
      </div>

      {/* Clean Telemetry Summary Strip */}
      <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg divide-y md:divide-y-0 md:divide-x divide-[#1d283a] grid grid-cols-1 md:grid-cols-4">
        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Đã giải
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-semibold font-mono text-white">
              {summary.solved_questions ?? 0}
            </span>
            <span className="text-xs font-mono text-emerald-400">
              / {summary.attempted_questions ?? 0} bài
            </span>
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Lượt nộp
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-semibold font-mono text-white">
              {summary.total_submissions ?? 0}
            </span>
            <span className="text-xs font-mono text-[#38bdf8]">
              ({summary.passed_submissions ?? 0} đúng)
            </span>
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Tỷ lệ đúng
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-2xl font-semibold font-mono text-white">
              {summary.accuracy_percent ?? 0}%
            </span>
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">
            Bộ đề tuần
          </div>
          <div className="mt-1.5">
            <div className="text-sm font-medium text-white truncate">
              {data?.weekly_set?.title || 'Tuần #42'}
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
              6 Nhóm kỹ năng SQL (S1–S6)
            </h3>
          </div>
        </div>

        <div className="p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {skills.map((sk: any, idx: number) => {
            const pct = sk.percent || 0;
            return (
              <motion.div
                key={sk.skill_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -3 }}
                transition={{
                  duration: 0.22,
                  delay: idx * 0.04,
                  ease: [0.23, 1, 0.32, 1],
                }}
                className="p-4 rounded-md bg-[#090d16] border border-[#192336] flex flex-col justify-between gap-3 card-interactive"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#131d31] text-[#38bdf8] border border-[#223456]">
                      {sk.code}
                    </span>
                    <span className="text-xs font-mono text-[#94a3b8]">
                      {sk.passed_questions}/{sk.total_questions} câu ({pct}%)
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-white">
                    {sk.name}
                  </div>
                </div>

                <div className="w-full h-2 rounded-full bg-[#162032] overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, pct)}%` }}
                    transition={{ type: 'spring', stiffness: 110, damping: 18, delay: 0.1 + idx * 0.05 }}
                    className="h-full bg-[#5C7F71]"
                  />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Submission Audit Log */}
      <div className="bg-[#0d1321] border border-[#1d283a] rounded-lg overflow-hidden">
        <div className="px-5 py-3 bg-[#090d16] border-b border-[#1d283a] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            Lịch sử nộp bài
          </h3>
          <span className="text-[11px] font-mono text-[#64748b]">
            20 lượt gần nhất
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
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-[11px] font-bold tracking-[0.15em] uppercase text-[var(--copper)]">
            BẢNG VÀNG HỌC VIÊN
          </div>
          <h2 className="text-2xl font-bold text-[var(--ink)] mt-0.5">
            Xếp hạng <span className="editorial-serif text-[var(--green)]">cộng đồng.</span>
          </h2>
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
            <span>BXH Tuần</span>
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
            <span>BXH Tháng</span>
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
              <motion.div
                key={r.user_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -4 }}
                transition={{ duration: 0.22, delay: idx * 0.05, ease: [0.23, 1, 0.32, 1] }}
                className={`border rounded-lg p-4 card-interactive ${borderColors[idx] || borderColors[1]}`}
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
              </motion.div>
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
                <th className="py-3 px-4 w-20">Hạng</th>
                <th className="py-3 px-4">Học viên</th>
                <th className="py-3 px-4">Câu đúng</th>
                <th className="py-3 px-4">Điểm</th>
                <th className="py-3 px-4">Tốc độ</th>
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
                    {r.correct_count ?? r.solved_count} câu
                  </td>
                  <td className="py-3 px-4 font-mono text-white font-semibold">
                    {r.total_score} pts
                  </td>
                  <td className="py-3 px-4 font-mono text-[#94a3b8]">
                    {r.avg_runtime_ms} ms
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
