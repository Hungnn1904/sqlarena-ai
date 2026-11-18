'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Presentation,
  ChevronRight,
  ChevronLeft,
  PlayCircle,
  X,
  Layers,
  ShieldCheck,
  BarChart3,
  Terminal,
} from 'lucide-react';

interface PitchTourProps {
  open: boolean;
  onClose: () => void;
  onSelectStepAction: (tab: string, role?: 'learner' | 'admin') => void;
}

const PITCH_STEPS = [
  {
    step: 1,
    code: 'Bước 1: Tổng quan',
    title: 'Sinh đề & Chấm thi SQL tự động trên PostgreSQL 17',
    summary: 'Kết hợp AI 2-Model kiểm chứng chéo với Sandbox PostgreSQL 17 thật gồm 13 bảng dữ liệu.',
    metrics: [
      { label: 'Dữ liệu thực tế', val: '13 Bảng doanh nghiệp' },
      { label: 'Kiểm định tự động', val: '7 Cổng kiểm tra' },
      { label: 'Độ trễ chấm bài', val: '< 45ms Read-Only' },
      { label: 'Chế độ gom đề', val: 'Đăng cả nhóm 1 chạm' },
    ],
    actionLabel: 'Mở Bàn Làm Bài',
    targetTab: 'workbench',
    targetRole: 'learner' as const,
    icon: Layers,
  },
  {
    step: 2,
    code: 'Bước 2: Làm bài',
    title: 'Thực hành & Chấm điểm Thời gian thực',
    summary: 'Tra cứu sơ đồ PK/FK 13 bảng, viết truy vấn trên Monaco Editor và nhận gợi ý từ AI Coach.',
    metrics: [
      { label: 'Bảo mật dữ liệu', val: 'READ ONLY Transaction' },
      { label: 'Lưu nháp tự động', val: 'Theo từng câu hỏi' },
      { label: 'Hỗ trợ người mới', val: 'AI Coach + EXPLAIN' },
      { label: 'Phân quyền xác thực', val: 'JWT + PBKDF2-SHA256' },
    ],
    actionLabel: 'Thử chạy SQL ngay',
    targetTab: 'workbench',
    targetRole: 'learner' as const,
    icon: Terminal,
  },
  {
    step: 3,
    code: 'Bước 3: Tiến độ',
    title: 'Đánh giá Năng lực theo 6 Kỹ năng SQL',
    summary: 'Theo dõi tiến độ từ SELECT, JOIN, GROUP BY đến Subquery/CTE, Window Functions và xử lý NULL.',
    metrics: [
      { label: 'Trục kỹ năng', val: 'S1 đến S6' },
      { label: 'Lịch sử nộp bài', val: 'Lưu trữ đầy đủ' },
      { label: 'Bảng xếp hạng', val: 'Theo Tuần & Tháng' },
      { label: 'Chỉ số phụ', val: 'Thời gian chạy (ms)' },
    ],
    actionLabel: 'Xem Tiến độ',
    targetTab: 'progress',
    targetRole: 'learner' as const,
    icon: BarChart3,
  },
  {
    step: 4,
    code: 'Bước 4: Ra đề',
    title: 'Gom nhóm Đề & Phát hành 1 Lần Lên Kệ',
    summary: 'Giảng viên duyệt hàng loạt, kéo thả nhiều đề vào một nhóm và đăng toàn bộ lên kệ ngay lập tức.',
    metrics: [
      { label: 'Nguồn câu hỏi', val: 'AI sinh + Thủ công' },
      { label: 'Duyệt nhanh', val: 'Bulk Approve & Group' },
      { label: ' Sắp xếp đề', val: 'Kéo thả trực quan' },
      { label: 'Tài khoản mẫu', val: 'admin' },
    ],
    actionLabel: 'Mở Cổng Quản trị',
    targetTab: 'admin',
    targetRole: 'admin' as const,
    icon: ShieldCheck,
  },
];

export default function PitchTourBanner({
  open,
  onClose,
  onSelectStepAction,
}: PitchTourProps) {
  const [idx, setIdx] = useState(0);
  const current = PITCH_STEPS[idx] || PITCH_STEPS[0];
  const Icon = current.icon;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="border-b border-line bg-soft"
        >
          <div className="max-w-[1520px] mx-auto px-5 py-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-2.5 border-b border-line">
              <div className="flex items-center gap-2">
                <Presentation className="w-4 h-4 text-brand" />
                <span className="text-sm font-semibold text-ink">
                  Hướng dẫn nhanh trải nghiệm SQL Arena PTIT
                </span>
              </div>

              <div className="flex items-center gap-1.5">
                {PITCH_STEPS.map((s, i) => (
                  <button
                    key={s.step}
                    type="button"
                    data-solid-btn={i === idx ? 'true' : undefined}
                    onClick={() => {
                      setIdx(i);
                      onSelectStepAction(s.targetTab, s.targetRole);
                    }}
                    className={`px-3 min-h-9 rounded-lg text-xs font-semibold ${
                      i === idx ? 'btn-primary' : 'btn-secondary'
                    }`}
                  >
                    Bước {s.step}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-secondary ml-2 min-w-9 min-h-9 rounded-lg flex items-center justify-center"
                  title="Đóng hướng dẫn"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
              <div className="lg:col-span-7 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-semibold text-brand">
                  <Icon className="w-4 h-4" />
                  <span>{current.code}</span>
                </div>
                <h3 className="text-base font-bold text-ink">{current.title}</h3>
                <p className="text-sm text-text2 leading-relaxed">{current.summary}</p>
              </div>

              <div className="lg:col-span-5 space-y-2.5">
                <div className="grid grid-cols-2 gap-2">
                  {current.metrics.map((m) => (
                    <div key={m.label} className="px-3 py-2 rounded-lg bg-surface border border-line">
                      <div className="text-xs text-muted">{m.label}</div>
                      <div className="text-xs font-semibold text-ink mt-0.5">{m.val}</div>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={idx === 0}
                      onClick={() => {
                        const prev = Math.max(0, idx - 1);
                        setIdx(prev);
                        onSelectStepAction(PITCH_STEPS[prev].targetTab, PITCH_STEPS[prev].targetRole);
                      }}
                      className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-40"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Trước</span>
                    </button>
                    <button
                      type="button"
                      disabled={idx === PITCH_STEPS.length - 1}
                      onClick={() => {
                        const next = Math.min(PITCH_STEPS.length - 1, idx + 1);
                        setIdx(next);
                        onSelectStepAction(PITCH_STEPS[next].targetTab, PITCH_STEPS[next].targetRole);
                      }}
                      className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-40"
                    >
                      <span>Tiếp</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <button
                    type="button"
                    data-solid-btn="true"
                    onClick={() => onSelectStepAction(current.targetTab, current.targetRole)}
                    className="btn-primary flex-1 min-h-9 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5"
                  >
                    <PlayCircle className="w-3.5 h-3.5" />
                    <span>{current.actionLabel}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
