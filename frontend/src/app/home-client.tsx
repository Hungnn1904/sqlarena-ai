'use client';

import React, { useEffect, useState } from 'react';
import AuthBar from '../components/AuthBar';
import LearnerWorkbench from '../components/LearnerWorkbench';
import { LearnerProgressView, LeaderboardView } from '../components/ProgressAndLeaderboard';
import AdminPortal from '../components/AdminPortal';
import PipelineTimeline from '../components/PipelineTimeline';
import FlowDiagram from '../components/FlowDiagram';
import ComparisonTable from '../components/ComparisonTable';
import ScheduleGrid from '../components/ScheduleGrid';
import { UserProfile, getMe, loginUser } from '../lib/api';
import type { PipelineStep } from '../components/types';

const PIPELINE_STEPS: PipelineStep[] = [
  {
    id: 1,
    title: 'Core World & Skill Taxonomy (core.worlds, core.skills, core.source_questions)',
    badges: [
      { label: 'PostgreSQL 17', variant: 'db' },
      { label: '6 Skills S1–S6 · 50 Source Questions', variant: 'rule' },
    ],
    status: 'completed',
    content: (
      <div className="text-xs text-[#94a3b8] leading-relaxed">
        Tầng tri thức nền tảng lưu trữ cấu trúc 13 bảng dữ liệu thật của EnterpriseDB, 6 kỹ năng SQL cốt lõi (SELECT, JOIN, GROUP BY, Subquery/CTE, Window Functions, Edge Cases) và 50 đề nguồn chuẩn.
      </div>
    ),
  },
  {
    id: 2,
    title: 'Model A — Blueprint & Question Generator (draft.question_drafts)',
    badges: [
      { label: 'Model A (Generator)', variant: 'llm' },
      { label: 'Blueprint + Candidate SQL', variant: 'new' },
    ],
    status: 'completed',
    content: (
      <div className="text-xs text-[#94a3b8] leading-relaxed">
        Sinh câu hỏi tiếng Việt bám sát nghiệp vụ doanh nghiệp kèm Blueprint logic_signature, danh sách cột đầu ra và điều kiện biên.
      </div>
    ),
  },
  {
    id: 3,
    title: 'Model B — Independent Self-Solve & 7-Gate Verification (draft.self_solve_runs)',
    badges: [
      { label: 'Model B (Reviewer)', variant: 'llm' },
      { label: 'Deterministic Hash Consensus', variant: 'db' },
    ],
    status: 'running',
    content: (
      <div className="text-xs text-[#94a3b8] leading-relaxed">
        Model B độc lập giải lại đề trên Base + Mutant Datasets. Chỉ những đề khớp kết quả thực thi và vượt qua 7 cổng kiểm định mới được tự động duyệt hoặc chuyển sang trạng thái <code className="text-amber-300">needs_human</code> cho Admin.
      </div>
    ),
  },
  {
    id: 4,
    title: 'Promotion, Weekly Sets & Read-Only Grading Sandbox (live.*)',
    badges: [
      { label: 'sqlarena_ai_ro Sandbox', variant: 'db' },
      { label: 'Real-Time Leaderboard', variant: 'free' },
    ],
    status: 'completed',
    content: (
      <div className="text-xs text-[#94a3b8] leading-relaxed">
        Câu hỏi đã duyệt được promote vào <code className="text-emerald-300">live.questions</code> kèm <code className="text-emerald-300">live.test_cases</code>. Học viên làm bài trên Monaco SQL Workbench, chấm điểm tức thì và xếp hạng Tuần/Tháng.
      </div>
    ),
  },
];

export default function HomeClient() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<string>('workbench');
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = window.localStorage.getItem('sqlarena_token');
        if (token) {
          const me = await getMe();
          setUser(me);
          setBooting(false);
          return;
        }
      } catch {
        window.localStorage.removeItem('sqlarena_token');
      }
      try {
        const res = await loginUser('nguyen_ptit', 'demo123');
        window.localStorage.setItem('sqlarena_token', res.access_token);
        setUser(res.user);
      } catch {}
      setBooting(false);
    };
    initAuth();
  }, []);

  const handleAuthSuccess = (token: string, u: UserProfile) => {
    window.localStorage.setItem('sqlarena_token', token);
    setUser(u);
  };

  const handleLogout = () => {
    window.localStorage.removeItem('sqlarena_token');
    setUser(null);
  };

  return (
    <div className="min-h-screen bg-[#060911] text-[#e2e8f0] flex flex-col">
      <AuthBar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onAuthSuccess={handleAuthSuccess}
        onLogout={handleLogout}
        onUserUpdated={setUser}
      />

      <main className="flex-1 max-w-[1520px] w-full mx-auto px-5 py-5">
        {booting ? (
          <div className="p-12 text-center text-xs font-mono text-[#64748b]">
            Initializing PostgreSQL 17 Enterprise Sandbox & Unified API...
          </div>
        ) : (
          <>
            {activeTab === 'workbench' && <LearnerWorkbench />}
            {activeTab === 'progress' && <LearnerProgressView />}
            {activeTab === 'leaderboard' && <LeaderboardView />}
            {activeTab === 'admin' && <AdminPortal isAdmin={user?.role === 'admin'} />}
            {activeTab === 'pipeline' && (
              <div className="space-y-8">
                <PipelineTimeline steps={PIPELINE_STEPS} />
                <FlowDiagram />
                <ComparisonTable />
                <ScheduleGrid />
              </div>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-[#151d2c] bg-[#060911] py-3.5 px-5 text-xs text-[#64748b] font-mono">
        <div className="max-w-[1520px] mx-auto flex flex-wrap items-center justify-between gap-2">
          <span>SQLArena Platform · Design v7 Clean Architecture</span>
          <span>PostgreSQL 17 Read-Only Sandbox · FastAPI · Next.js 16</span>
        </div>
      </footer>
    </div>
  );
}
