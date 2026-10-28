'use client';

import React, { useEffect, useState } from 'react';
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
      <div className="p-8 bg-[#111827] border border-[#1e2d45] rounded-xl text-center text-sm text-[#8ba3c7]">
        Đang tải thống kê tiến độ học tập...
      </div>
    );
  }

  const summary = data?.summary || {};
  const skills = data?.skills || [];
  const recent = data?.recent_submissions || [];

  return (
    <div className="space-y-5">
      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          {
            label: 'Câu hỏi đã giải (PASSED)',
            val: summary.solved_questions ?? 0,
            color: 'text-[#00e5a0]',
            sub: 'Trích từ live.submissions',
          },
          {
            label: 'Tổng số lần nộp bài',
            val: summary.total_submissions ?? 0,
            color: 'text-[#00d4ff]',
            sub: `${summary.passed_submissions ?? 0} lần đạt 100 điểm`,
          },
          {
            label: 'Tỷ lệ chính xác (Accuracy)',
            val: `${summary.accuracy_percent ?? 0}%`,
            color: 'text-[#ffb830]',
            sub: 'Trên toàn bộ lượt chấm',
          },
          {
            label: 'Bộ đề tuần hiện tại',
            val: data?.weekly_set?.title?.split('—')[0] || 'Tuần #42',
            color: 'text-white',
            sub: `Bắt đầu: ${data?.weekly_set?.week_start || '2026-10-26'}`,
          },
        ].map((c) => (
          <div
            key={c.label}
            className="bg-[#111827] border border-[#1e2d45] rounded-xl p-4"
          >
            <div className="text-xs text-[#8ba3c7]">{c.label}</div>
            <div className={`text-2xl font-black mt-1 font-mono ${c.color}`}>
              {c.val}
            </div>
            <div className="text-[0.68rem] font-mono text-[#5a7298] mt-1">
              {c.sub}
            </div>
          </div>
        ))}
      </div>

      {/* 6 SQL Skill Mastery Progress Bars */}
      <div className="bg-[#111827] border border-[#1e2d45] rounded-xl p-5">
        <h3 className="text-sm font-bold text-white mb-4 flex items-center justify-between">
          <span>🎯 Độ thông thạo theo 6 Nhóm Kỹ năng SQL (S1–S6)</span>
          <span className="text-xs font-mono text-[#8ba3c7]">
            Tính theo bộ đề tuần đang mở
          </span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {skills.map((sk: any) => (
            <div
              key={sk.skill_id}
              className="p-3.5 rounded-lg bg-[#0a0e17] border border-[#1e2d45]"
            >
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="font-semibold text-white">
                  <span className="font-mono text-[#00d4ff] mr-1.5">
                    [{sk.code}]
                  </span>
                  {sk.name}
                </span>
                <span className="font-mono text-[#00e5a0]">
                  {sk.passed_questions}/{sk.total_questions} câu ({sk.percent}%)
                </span>
              </div>
              <div className="w-full h-2 rounded-full bg-[#1e2d45] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#00d4ff] to-[#00e5a0] transition-all"
                  style={{ width: `${Math.min(100, sk.percent || 0)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Submissions Table */}
      <div className="bg-[#111827] border border-[#1e2d45] rounded-xl p-5">
        <h3 className="text-sm font-bold text-white mb-3">
          🕒 Lịch sử nộp bài gần đây (20 lượt gần nhất)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#1e2d45] text-[#8ba3c7] font-mono">
                <th className="py-2 px-3">ID</th>
                <th className="py-2 px-3">Câu hỏi</th>
                <th className="py-2 px-3">Trạng thái</th>
                <th className="py-2 px-3">Điểm</th>
                <th className="py-2 px-3">Runtime</th>
                <th className="py-2 px-3">Thời gian</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((s: any) => (
                <tr
                  key={s.submission_id}
                  className="border-b border-[#1e2d45]/50 hover:bg-[#0a0e17]/60"
                >
                  <td className="py-2 px-3 font-mono text-[#5a7298]">
                    #{s.submission_id}
                  </td>
                  <td className="py-2 px-3 text-white font-medium">
                    {s.question_title}
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={`font-mono px-2 py-0.5 rounded text-[0.68rem] ${
                        s.submission_status === 'passed'
                          ? 'bg-[#00e5a0]/15 text-[#00e5a0]'
                          : 'bg-red-500/15 text-red-400'
                      }`}
                    >
                      {s.submission_status.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2 px-3 font-mono text-white">{s.score}</td>
                  <td className="py-2 px-3 font-mono text-[#8ba3c7]">
                    {s.runtime_ms}ms
                  </td>
                  <td className="py-2 px-3 font-mono text-[#5a7298]">
                    {s.submitted_at
                      ? new Date(s.submitted_at).toLocaleString('vi-VN')
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

  return (
    <div className="bg-[#111827] border border-[#1e2d45] rounded-xl p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1e2d45] pb-4">
        <div>
          <span className="text-[0.68rem] font-mono uppercase tracking-wider text-[#ffb830]">
            REAL-TIME SQL LEADERBOARD
          </span>
          <h2 className="text-lg font-bold text-white">
            {mode === 'weekly'
              ? weeklyData?.set?.title || 'Bảng Xếp Hạng Tuần Hiện Tại'
              : `Bảng Xếp Hạng Tháng ${monthlyData?.month || 10}/${monthlyData?.year || 2026}`}
          </h2>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setMode('weekly')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition ${
              mode === 'weekly'
                ? 'bg-[#00d4ff] text-[#0a0e17]'
                : 'bg-[#0a0e17] text-[#8ba3c7] border border-[#1e2d45]'
            }`}
          >
            🏆 BXH Tuần Hiện Tại
          </button>
          <button
            onClick={() => setMode('monthly')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition ${
              mode === 'monthly'
                ? 'bg-[#ffb830] text-[#0a0e17]'
                : 'bg-[#0a0e17] text-[#8ba3c7] border border-[#1e2d45]'
            }`}
          >
            🌟 BXH Tháng {monthlyData?.month || 10}/{monthlyData?.year || 2026}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-[#1e2d45] text-[#8ba3c7] font-mono">
              <th className="py-2.5 px-3">Hạng</th>
              <th className="py-2.5 px-3">Học viên</th>
              <th className="py-2.5 px-3">Số câu PASSED</th>
              <th className="py-2.5 px-3">Tổng điểm</th>
              <th className="py-2.5 px-3">Runtime TB</th>
              <th className="py-2.5 px-3">Lần hoàn thành cuối</th>
            </tr>
          </thead>
          <tbody>
            {currentItems.map((r: any) => (
              <tr
                key={r.user_id}
                className="border-b border-[#1e2d45]/50 hover:bg-[#0a0e17]/70"
              >
                <td className="py-3 px-3 font-mono font-bold text-sm">
                  {r.rank === 1 ? (
                    <span className="text-[#ffb830]">🥇 #1</span>
                  ) : r.rank === 2 ? (
                    <span className="text-slate-300">🥈 #2</span>
                  ) : r.rank === 3 ? (
                    <span className="text-amber-600">🥉 #3</span>
                  ) : (
                    <span className="text-[#5a7298]">#{r.rank}</span>
                  )}
                </td>
                <td className="py-3 px-3">
                  <div className="font-bold text-white">{r.display_name}</div>
                  <div className="font-mono text-[0.68rem] text-[#5a7298]">
                    @{r.username}
                  </div>
                </td>
                <td className="py-3 px-3 font-mono text-[#00e5a0] font-bold">
                  {r.correct_count ?? r.solved_count} câu
                </td>
                <td className="py-3 px-3 font-mono text-[#00d4ff] font-bold text-sm">
                  {r.total_score} đ
                </td>
                <td className="py-3 px-3 font-mono text-[#8ba3c7]">
                  {r.avg_runtime_ms}ms
                </td>
                <td className="py-3 px-3 font-mono text-[#5a7298]">
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
  );
}
