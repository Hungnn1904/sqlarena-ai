'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AuthBar from '../components/AuthBar';
import PitchTourBanner from '../components/PitchTourBanner';
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
    title: 'Tầng Dữ Liệu Thật & Khung Năng Lực (core.worlds · core.skills · enterprise_db)',
    badges: [
      { label: 'PostgreSQL 17', variant: 'db' },
      { label: '13 Bảng · 6 Kỹ năng S1–S6', variant: 'rule' },
    ],
    status: 'completed',
    content: (
      <div className="text-xs text-[var(--text2)] leading-relaxed pt-2 space-y-1.5">
        <div>
          • <strong>Database Thực Tế (`enterprise_db`)</strong>: Gồm 13 bảng thương mại điện tử & nhân sự với hơn 13.400 dòng dữ liệu thật (khách hàng, đơn hàng, thanh toán, tồn kho, phòng ban).
        </div>
        <div>
          • <strong>Khung 6 Kỹ Năng (`S1–S6`)</strong>: Phân loại bài tập từ <code>S1 SELECT/WHERE</code>, <code>S2 JOIN</code>, <code>S3 GROUP BY</code>, <code>S4 Subquery/CTE</code>, <code>S5 Window Functions</code> đến <code>S6 NULL & Edge Cases</code>.
        </div>
      </div>
    ),
  },
  {
    id: 2,
    title: 'Model A — AI Sinh Đề & Khung Truy Vấn Chuẩn (draft.question_drafts)',
    badges: [
      { label: 'Model A (Generator)', variant: 'llm' },
      { label: 'Blueprint + Candidate SQL', variant: 'new' },
    ],
    status: 'completed',
    content: (
      <div className="text-xs text-[var(--text2)] leading-relaxed pt-2 space-y-1.5">
        <div>
          • Khi Admin bấm <strong>&quot;Chạy Job Sinh đề&quot;</strong> trong tab Quản trị, <strong>Model A</strong> tự động thiết kế <em>Blueprint</em> (chọn bảng, cột kết quả, độ khó) và viết câu hỏi nghiệp vụ tiếng Việt kèm câu lệnh SQL đáp án mẫu.
        </div>
      </div>
    ),
  },
  {
    id: 3,
    title: 'Model B — AI Giải Độc Lập & Kiểm Định 7 Cổng (draft.self_solve_runs)',
    badges: [
      { label: 'Model B (Reviewer)', variant: 'llm' },
      { label: 'Đối chiếu Kết quả 3/3', variant: 'db' },
    ],
    status: 'running',
    content: (
      <div className="text-xs text-[var(--text2)] leading-relaxed pt-2 space-y-1.5">
        <div>
          • Để chống ảo giác AI (Hallucination), <strong>Model B</strong> chỉ đọc đề bài (không được nhìn SQL của Model A) và tự viết SQL giải lại 3 lần trên PostgreSQL 17.
        </div>
        <div>
          • Nếu kết quả chạy của Model B khớp 100% với Model A qua 7 cổng kiểm tra (cú pháp, hiệu năng, không rỗng, không mơ hồ), đề được gán nhãn <code>verified</code>. Nếu lệch, đề chuyển vào hàng đợi <code>needs_human</code> để Admin duyệt tay.
        </div>
      </div>
    ),
  },
  {
    id: 4,
    title: 'Phát Hành Bộ Đề Tuần, Sandbox Chấm Điểm & AI SQL Coach (live.*)',
    badges: [
      { label: 'Read-Only Sandbox', variant: 'db' },
      { label: 'AI Coach + Xếp hạng Tuần/Tháng', variant: 'free' },
    ],
    status: 'completed',
    content: (
      <div className="text-xs text-[var(--text2)] leading-relaxed pt-2 space-y-1.5">
        <div>
          • Đề đã duyệt được đưa vào <code>live.questions</code> kèm bộ <code>live.test_cases</code> chuẩn và phát hành thành <strong>Bộ đề tuần</strong>.
        </div>
        <div>
          • Học viên luyện tập trên <strong>SQL Studio</strong> với quyền chỉ đọc (<code>sqlarena_ai_ro</code>), phân tích hiệu năng bằng <code>EXPLAIN ANALYZE</code>, hỏi <strong>🤖 AI Coach</strong> và đua Top Bảng Xếp Hạng.
        </div>
      </div>
    ),
  },
];

export default function HomeClient() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<string>('workbench');
  const [pitchOpen, setPitchOpen] = useState<boolean>(false);
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

  const handlePitchAction = async (targetTab: string, targetRole?: 'learner' | 'admin') => {
    if (targetRole === 'admin' && user?.role !== 'admin') {
      try {
        const res = await loginUser('admin', 'admin123');
        handleAuthSuccess(res.access_token, res.user);
      } catch {}
    } else if (targetRole === 'learner' && user?.role === 'admin') {
      try {
        const res = await loginUser('nguyen_ptit', 'demo123');
        handleAuthSuccess(res.access_token, res.user);
      } catch {}
    }
    setActiveTab(targetTab);
  };

  return (
    <div className="min-h-screen bg-[#060911] text-[#e2e8f0] flex flex-col transition-colors duration-300">
      <AuthBar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onAuthSuccess={handleAuthSuccess}
        onLogout={handleLogout}
        onUserUpdated={setUser}
        pitchOpen={pitchOpen}
        onTogglePitch={() => setPitchOpen((p) => !p)}
      />

      <PitchTourBanner
        open={pitchOpen}
        onClose={() => setPitchOpen(false)}
        onSelectStepAction={handlePitchAction}
      />

      <main className="flex-1 max-w-[1520px] w-full mx-auto px-5 py-5 relative z-10">
        {booting ? (
          <div className="p-12 text-center text-xs font-mono text-[#64748b]">
            Initializing PostgreSQL 17 Enterprise Sandbox & Unified API...
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            >
              {activeTab === 'workbench' && <LearnerWorkbench />}
              {activeTab === 'progress' && <LearnerProgressView />}
              {activeTab === 'leaderboard' && <LeaderboardView />}
              {activeTab === 'admin' && <AdminPortal isAdmin={user?.role === 'admin'} />}
              {activeTab === 'pipeline' && (
                <div className="space-y-6">
                  <div className="p-5 rounded-lg bg-[var(--surface)] border border-[var(--line)] flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <div className="text-[11px] font-bold tracking-[0.15em] uppercase text-[var(--copper)]">
                        05 · KIẾN TRÚC &amp; QUY TRÌNH SINH ĐỀ TỰ ĐỘNG
                      </div>
                      <h2 className="text-2xl font-bold text-[var(--ink)] mt-0.5">
                        Pipeline <span className="editorial-serif text-[var(--green)]">2-Model AI kiểm chứng chéo.</span>
                      </h2>
                      <p className="text-xs text-[var(--text2)] mt-1 max-w-3xl">
                        Giải quyết bài toán AI sinh đề SQL bị lỗi hoặc mơ hồ bằng cơ chế 2 mô hình độc lập (Model A sinh đề → Model B tự giải kiểm chứng trên PostgreSQL 17 → Admin duyệt → Mở bộ đề tuần cho Học viên).
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handlePitchAction('admin', 'admin')}
                        className="px-3.5 py-2 rounded bg-[#B2653B] text-[#F5EDDC] text-xs font-semibold"
                      >
                        ⚡ Chạy thử Pipeline ở trang Quản trị →
                      </button>
                      <button
                        onClick={() => setActiveTab('workbench')}
                        className="px-3.5 py-2 rounded bg-[#5C7F71] text-[#F5EDDC] text-xs font-semibold"
                      >
                        ▶ Mở Phòng Luyện SQL
                      </button>
                    </div>
                  </div>
                  <PipelineTimeline steps={PIPELINE_STEPS} />
                  <FlowDiagram />
                  <ComparisonTable />
                  <ScheduleGrid />
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </main>

      <footer className="border-t border-[var(--line)] bg-[var(--paper)] py-3 px-5 text-xs text-[var(--muted)] font-mono relative z-10">
        <div className="max-w-[1520px] mx-auto flex items-center justify-between">
          <span>sqlarena · Nền tảng học & chấm thi SQL tự động trên PostgreSQL 17</span>
        </div>
      </footer>
    </div>
  );
}
