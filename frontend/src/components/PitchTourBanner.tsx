'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Presentation,
  ChevronRight,
  ChevronLeft,
  PlayCircle,
  CheckCircle2,
  X,
  Layers,
  ShieldCheck,
  BarChart3,
  Terminal,
  GitBranch,
} from 'lucide-react';

interface PitchTourProps {
  open: boolean;
  onClose: () => void;
  onSelectStepAction: (tab: string, role?: 'learner' | 'admin') => void;
}

const PITCH_STEPS = [
  {
    step: 1,
    code: '01 · TỔNG QUAN',
    title: 'Sinh đề & Chấm thi SQL tự động trên PostgreSQL 17',
    summary: 'Kết hợp 2-Model AI kiểm chứng chéo với Sandbox PostgreSQL 17 thật (13 bảng, 13.400+ dòng).',
    metrics: [
      { label: 'Dữ liệu thực tế', val: '13 Bảng · 13,400+ Dòng' },
      { label: 'Kiểm định tự động', val: '7 Cổng (3/3 Consensus)' },
      { label: 'Độ trễ chấm bài', val: '< 45ms (Read-Only PG17)' },
      { label: 'Kiểm thử hệ thống', val: '48/48 E2E Tests Passed' },
    ],
    actionLabel: 'Mở Không gian Làm bài',
    targetTab: 'workbench',
    targetRole: 'learner' as const,
    icon: Layers,
  },
  {
    step: 2,
    code: '02 · LÀM BÀI',
    title: 'Làm bài & Chấm điểm Thời gian thực',
    summary: 'Tra cứu Schema 13 bảng, viết truy vấn trên Monaco Editor và chấm điểm tức thì trong Sandbox cô lập.',
    metrics: [
      { label: 'Cơ chế bảo mật', val: 'SET TRANSACTION READ ONLY' },
      { label: 'Chế độ so khớp', val: 'ORDERED & UNORDERED' },
      { label: 'Công cụ hỗ trợ', val: 'Catalog Explorer + Snippets' },
      { label: 'Tài khoản đang dùng', val: 'nguyen_ptit (Learner)' },
    ],
    actionLabel: 'Thử chạy SQL ngay',
    targetTab: 'workbench',
    targetRole: 'learner' as const,
    icon: Terminal,
  },
  {
    step: 3,
    code: '03 · NĂNG LỰC',
    title: 'Đánh giá Năng lực theo 6 Kỹ năng SQL (S1–S6)',
    summary: 'Phân tích tiến độ chuyên sâu từ SELECT, JOIN, GROUP BY đến Subquery/CTE, Window Functions và NULL.',
    metrics: [
      { label: 'Trục đánh giá', val: 'S1 -> S6 Competency Matrix' },
      { label: 'Lịch sử truy vết', val: 'Full SQL Submission Audit' },
      { label: 'Bảng xếp hạng', val: 'Real-time Tuần & Tháng' },
      { label: 'Chỉ số phụ', val: 'Average Runtime Latency (ms)' },
    ],
    actionLabel: 'Xem Tiến độ & Xếp hạng',
    targetTab: 'progress',
    targetRole: 'learner' as const,
    icon: BarChart3,
  },
  {
    step: 4,
    code: '04 · QUẢN TRỊ AI',
    title: 'Cổng Kiểm duyệt Đề thi Human-in-the-Loop',
    summary: 'Model A sinh đề, Model B giải độc lập 3 lần; Admin kiểm duyệt trực tiếp các đề cần hiệu đính.',
    metrics: [
      { label: 'Model A (Generator)', val: 'Blueprint + Candidate SQL' },
      { label: 'Model B (Reviewer)', val: 'Blind Self-Solve 3 Samples' },
      { label: 'Kiểm soát chi phí', val: 'Daily LLM Budget Ledger' },
      { label: 'Tài khoản chuyển đổi', val: 'admin (Quản trị viên)' },
    ],
    actionLabel: 'Mở Cổng Quản trị',
    targetTab: 'admin',
    targetRole: 'admin' as const,
    icon: ShieldCheck,
  },
  {
    step: 5,
    code: '05 · KIẾN TRÚC',
    title: 'Kiến trúc Clean Architecture & 7 Cổng Kiểm định',
    summary: 'Thiết kế 4 tầng chuẩn công nghiệp với FastAPI, SQLAlchemy 2,PostgreSQL 17 và Next.js 16.',
    metrics: [
      { label: 'Backend Stack', val: 'FastAPI + SQLAlchemy 2 + Alembic' },
      { label: 'Database Engine', val: 'PostgreSQL 17 (core/draft/live)' },
      { label: 'Frontend Stack', val: 'Next.js 16 + React 19 + Monaco' },
      { label: 'Deployment', val: '1-Command Docker Compose' },
    ],
    actionLabel: 'Xem Sơ đồ Kiến trúc',
    targetTab: 'pipeline',
    targetRole: undefined,
    icon: GitBranch,
  },
];

export default function PitchTourBanner({
  open,
  onClose,
  onSelectStepAction,
}: PitchTourProps) {
  const [idx, setIdx] = useState(0);
  const current = PITCH_STEPS[idx];
  const Icon = current.icon;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: -14 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -14 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="pitch-banner-surface border-b border-[var(--line)] bg-[var(--soft)]"
        >
          <div className="max-w-[1520px] mx-auto px-5 py-3.5">
            {/* Top Stepper Row */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-2.5 mb-2.5 border-b border-[var(--line)]">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded bg-[var(--green)]/15 border border-[var(--green)]/30 text-[var(--green)]">
                  <Presentation className="w-4 h-4" />
                </span>
                <div className="text-xs font-semibold text-[var(--ink)]">
                  Hướng dẫn nhanh 5 bước trải nghiệm sqlarena
                </div>
              </div>

              {/* Step Pills */}
              <div className="flex items-center gap-1.5">
                {PITCH_STEPS.map((s, i) => (
                  <button
                    key={s.step}
                    onClick={() => {
                      setIdx(i);
                      onSelectStepAction(s.targetTab, s.targetRole);
                    }}
                    className={`px-2.5 py-1 rounded text-xs font-mono transition border ${
                      i === idx
                        ? 'bg-[var(--green)] text-[var(--on-accent)] border-[var(--green)]'
                        : 'bg-[var(--surface)] text-[var(--muted)] border-[var(--line)] hover:text-[var(--ink)]'
                    }`}
                  >
                    Bước {s.step}
                  </button>
                ))}
                <button
                  onClick={onClose}
                  className="ml-2 p-1.5 rounded text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--surface)] transition"
                  title="Đóng hướng dẫn"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Animated Step Content */}
            <AnimatePresence mode="wait">
              <motion.div
                key={current.step}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ duration: 0.2 }}
                className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center"
              >
                <div className="lg:col-span-7 space-y-1.5">
                  <div className="flex items-center gap-2 text-[11px] font-mono text-[#38bdf8]">
                    <Icon className="w-3.5 h-3.5" />
                    <span>{current.code}</span>
                  </div>
                  <h3 className="text-base font-semibold text-white">
                    {current.title}
                  </h3>
                  <p className="text-xs text-[#cbd5e1] leading-relaxed">
                    {current.summary}
                  </p>
                </div>

                <div className="lg:col-span-5 space-y-2.5">
                  <div className="grid grid-cols-2 gap-2">
                    {current.metrics.map((m) => (
                      <div
                        key={m.label}
                        className="px-3 py-2 rounded bg-[#090d16]/90 border border-[#1e2d47]"
                      >
                        <div className="text-[10px] font-mono text-[#64748b] uppercase">
                          {m.label}
                        </div>
                        <div className="text-xs font-mono font-semibold text-white mt-0.5">
                          {m.val}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-1">
                    <div className="flex items-center gap-1.5">
                      <button
                        disabled={idx === 0}
                        onClick={() => {
                          const prev = Math.max(0, idx - 1);
                          setIdx(prev);
                          onSelectStepAction(
                            PITCH_STEPS[prev].targetTab,
                            PITCH_STEPS[prev].targetRole
                          );
                        }}
                        className="px-2.5 py-1.5 rounded bg-[#090d16] border border-[#1e2d47] text-xs text-[#94a3b8] hover:text-white disabled:opacity-40 flex items-center gap-1"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" />
                        <span>Trước</span>
                      </button>
                      <button
                        disabled={idx === PITCH_STEPS.length - 1}
                        onClick={() => {
                          const next = Math.min(PITCH_STEPS.length - 1, idx + 1);
                          setIdx(next);
                          onSelectStepAction(
                            PITCH_STEPS[next].targetTab,
                            PITCH_STEPS[next].targetRole
                          );
                        }}
                        className="px-2.5 py-1.5 rounded bg-[#090d16] border border-[#1e2d47] text-xs text-[#94a3b8] hover:text-white disabled:opacity-40 flex items-center gap-1"
                      >
                        <span>Tiếp theo</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <button
                      onClick={() =>
                        onSelectStepAction(current.targetTab, current.targetRole)
                      }
                      className="flex-1 py-1.5 px-3 rounded bg-[#0284c7] hover:bg-[#0369a1] text-white text-xs font-medium flex items-center justify-center gap-1.5 shadow transition"
                    >
                      <PlayCircle className="w-3.5 h-3.5" />
                      <span>{current.actionLabel}</span>
                    </button>
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
