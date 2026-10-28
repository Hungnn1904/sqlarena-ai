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
    code: 'VALUE PROPOSITION',
    title: 'Giải quyết bài toán Chấm thi & Sinh đề SQL quy mô doanh nghiệp',
    summary:
      'Các nền tảng học SQL truyền thống bị giới hạn bởi ngân hàng đề tĩnh dễ lộ đáp án, hoặc dùng 1 LLM sinh đề bị lỗi ảo giác (hallucination). SQLArena kết hợp 2-Model Cross-Verification với PostgreSQL 17 Sandbox thật.',
    metrics: [
      { label: 'Dữ liệu thực tế', val: '13 Bảng · 13,400+ Dòng' },
      { label: 'Kiểm định tự động', val: '7 Cổng (3/3 Consensus)' },
      { label: 'Độ trễ chấm bài', val: '< 45ms (Read-Only PG17)' },
      { label: 'Kiểm thử hệ thống', val: '48/48 E2E Tests Passed' },
    ],
    actionLabel: 'Bắt đầu Demo Môi trường Học viên',
    targetTab: 'workbench',
    targetRole: 'learner' as const,
    icon: Layers,
  },
  {
    step: 2,
    code: 'STEP 01 · LEARNER STUDIO',
    title: 'Trải nghiệm Làm bài & Chấm điểm Thời gian thực trên PostgreSQL 17',
    summary:
      'Ứng viên/sinh viên tra cứu trực tiếp Schema 13 bảng bên cột trái, viết truy vấn trên Monaco Editor và thực thi trong Sandbox cô lập quyền (sqlarena_ai_ro). Hệ thống đối chiếu bảng kết quả với Test Case chuẩn.',
    metrics: [
      { label: 'Cơ chế bảo mật', val: 'SET TRANSACTION READ ONLY' },
      { label: 'Chế độ so khớp', val: 'ORDERED & UNORDERED' },
      { label: 'Công cụ hỗ trợ', val: 'Catalog Explorer + Snippets' },
      { label: 'Tài khoản đang dùng', val: 'nguyen_ptit (Learner)' },
    ],
    actionLabel: 'Mở SQL Workspace & Chạy thử ngay',
    targetTab: 'workbench',
    targetRole: 'learner' as const,
    icon: Terminal,
  },
  {
    step: 3,
    code: 'STEP 02 · TALENT ANALYTICS',
    title: 'Đánh giá Năng lực Ứng viên theo 6 Trục Kỹ năng SQL (S1–S6)',
    summary:
      'Dành cho Nhà tuyển dụng & Giảng viên: Thay vì chỉ chấm điểm tổng, hệ thống bóc tách năng lực theo 6 nhóm kỹ năng chuẩn công nghiệp (từ SELECT/JOIN cơ bản đến CTE, Window Functions và xử lý bẫy NULL).',
    metrics: [
      { label: 'Trục đánh giá', val: 'S1 -> S6 Competency Matrix' },
      { label: 'Lịch sử truy vết', val: 'Full SQL Submission Audit' },
      { label: 'Bảng xếp hạng', val: 'Real-time Tuần & Tháng' },
      { label: 'Chỉ số phụ', val: 'Average Runtime Latency (ms)' },
    ],
    actionLabel: 'Xem Ma trận Kỹ năng & Bảng xếp hạng',
    targetTab: 'progress',
    targetRole: 'learner' as const,
    icon: BarChart3,
  },
  {
    step: 4,
    code: 'STEP 03 · AI GOVERNANCE',
    title: 'Cổng Kiểm duyệt Human-in-the-Loop dành cho Hội đồng Chuyên môn',
    summary:
      'Khi Model A sinh đề mới, Model B sẽ giải độc lập 3 lần trên dữ liệu gốc và dữ liệu đột biến. Những câu hỏi có độ phân kỳ kết quả được chuyển sang trạng thái needs_human để Admin trực tiếp hiệu đính và phê duyệt.',
    metrics: [
      { label: 'Model A (Generator)', val: 'Blueprint + Candidate SQL' },
      { label: 'Model B (Reviewer)', val: 'Blind Self-Solve 3 Samples' },
      { label: 'Kiểm soát chi phí', val: 'Daily LLM Budget Ledger' },
      { label: 'Tài khoản chuyển đổi', val: 'admin (Quản trị viên)' },
    ],
    actionLabel: 'Chuyển sang Admin & Mở Hàng đợi Kiểm duyệt',
    targetTab: 'admin',
    targetRole: 'admin' as const,
    icon: ShieldCheck,
  },
  {
    step: 5,
    code: 'STEP 04 · SYSTEM ARCHITECTURE',
    title: 'Kiến trúc Clean Architecture v7 & Sơ đồ 7 Cổng Kiểm định',
    summary:
      'Toàn bộ dự án được thiết kế theo Clean Architecture 4 tầng, đóng gói Docker Compose sẵn sàng triển khai thực tế cho trường đại học và doanh nghiệp tuyển dụng Data/Backend Engineer.',
    metrics: [
      { label: 'Backend Stack', val: 'FastAPI + SQLAlchemy 2 + Alembic' },
      { label: 'Database Engine', val: 'PostgreSQL 17 (core/draft/live)' },
      { label: 'Frontend Stack', val: 'Next.js 16 + React 19 + Monaco' },
      { label: 'Deployment', val: '1-Command Docker Compose' },
    ],
    actionLabel: 'Trình chiếu Sơ đồ Kiến trúc 7-Step AI',
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
          className="pitch-banner-surface border-b border-[#1d283a] bg-gradient-to-r from-[#13203d] via-[#1a2c54] to-[#13203d]"
        >
          <div className="max-w-[1520px] mx-auto px-5 py-4">
            {/* Top Stepper Row */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 mb-3 border-b border-[#263859]">
              <div className="flex items-center gap-2.5">
                <span className="p-1.5 rounded bg-sky-500/20 border border-sky-400/40 text-[#0284c7] dark:text-[#38bdf8]">
                  <Presentation className="w-4 h-4" />
                </span>
                <div>
                  <div className="text-xs font-semibold text-white">
                    Kịch bản Trình chiếu & Hướng dẫn (Investor / Reviewer Pitch Guide)
                  </div>
                  <div className="text-[11px] font-mono text-[#94a3b8]">
                    Bấm qua từng bước để tự động chuyển quyền & màn hình minh họa trực tiếp
                  </div>
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
                        ? 'bg-[#0284c7] text-white border-[#38bdf8]'
                        : i < idx
                        ? 'bg-emerald-950/50 text-emerald-300 border-emerald-800/50'
                        : 'bg-[#090d16] text-[#64748b] border-[#1d283a] hover:text-white'
                    }`}
                  >
                    Bước {s.step}
                  </button>
                ))}
                <button
                  onClick={onClose}
                  className="ml-2 p-1.5 rounded text-[#64748b] hover:text-white hover:bg-[#162032] transition"
                  title="Đóng thanh trình chiếu"
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
