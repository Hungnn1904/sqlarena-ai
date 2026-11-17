'use client';

import React from 'react';

type BadgeType = 'ok' | 'warn' | 'bad';

function StatusBadge({ type, children }: { type: BadgeType; children: React.ReactNode }) {
  const map: Record<BadgeType, string> = {
    ok: 'text-brand',
    warn: 'text-copper',
    bad: 'text-danger',
  };
  return <span className={`${map[type]} font-semibold`}>{children}</span>;
}

interface ComparisonRow {
  criteria: string;
  original: React.ReactNode;
  optimized: React.ReactNode;
}

const rows: ComparisonRow[] = [
  { criteria: 'Số lượt gọi LLM mỗi câu', original: <StatusBadge type="warn">3 lượt nặng</StatusBadge>, optimized: <StatusBadge type="ok">3 lượt (2 chính + 1 kiểm toán gọn)</StatusBadge> },
  { criteria: 'Chi phí vận hành', original: <StatusBadge type="warn">Tốn phí API ngoài</StatusBadge>, optimized: <StatusBadge type="ok">Tối ưu qua cổng API Thật (apithat.dev)</StatusBadge> },
  { criteria: 'Khởi tạo ban đầu', original: <StatusBadge type="bad">Chưa hỗ trợ</StatusBadge>, optimized: <StatusBadge type="ok">Bộ đề gốc chuẩn + soạn thủ công</StatusBadge> },
  { criteria: 'Phát hiện đề mơ hồ', original: <StatusBadge type="warn">Kiểm tra muộn</StatusBadge>, optimized: <StatusBadge type="ok">Kiểm tra ngay từ Blueprint & Audit</StatusBadge> },
  { criteria: 'Đối chứng kết quả', original: <StatusBadge type="warn">So chuỗi câu lệnh</StatusBadge>, optimized: <StatusBadge type="ok">Chạy thực nghiệm trên PostgreSQL 17</StatusBadge> },
];

export default function ComparisonTable() {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface mt-6">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-soft border-b border-line text-text2 font-semibold">
            <th className="px-4 py-3 text-left">Tiêu chí</th>
            <th className="px-4 py-3 text-left">Quy trình cũ</th>
            <th className="px-4 py-3 text-left">Quy trình tối ưu</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-soft transition-colors">
              <td className="px-4 py-3 text-ink font-semibold">{row.criteria}</td>
              <td className="px-4 py-3 text-text2 align-top">{row.original}</td>
              <td className="px-4 py-3 text-text2 align-top">{row.optimized}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
