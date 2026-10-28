'use client';

import React from 'react';

type BadgeType = 'ok' | 'warn' | 'bad';

function StatusBadge({ type, children }: { type: BadgeType; children: React.ReactNode }) {
  const map: Record<BadgeType, string> = {
    ok: 'text-[#00e5a0]',
    warn: 'text-[#ffb830]',
    bad: 'text-[#ff4d6d]',
  };
  return <span className={`${map[type]} font-semibold`}>{children}</span>;
}

interface ComparisonRow {
  criteria: string;
  original: React.ReactNode;
  optimized: React.ReactNode;
}

const rows: ComparisonRow[] = [
  { criteria: 'LLM calls / câu', original: <StatusBadge type="warn">3 calls nặng</StatusBadge>, optimized: <StatusBadge type="ok">3 calls (2 nặng + 1 nhỏ)</StatusBadge> },
  { criteria: 'Chi phí', original: <StatusBadge type="warn">~$1-3/tuần (OpenAI)</StatusBadge>, optimized: <StatusBadge type="ok">$0 — Gemini free tier</StatusBadge> },
  { criteria: 'Cold start', original: <StatusBadge type="bad">Không đề cập</StatusBadge>, optimized: <StatusBadge type="ok">Giai đoạn 0 + human seed</StatusBadge> },
  { criteria: 'Detect ambiguity', original: <StatusBadge type="warn">Bước 5, sau sinh xong</StatusBadge>, optimized: <StatusBadge type="ok">Bước 3 (blueprint) + Bước 5</StatusBadge> },
  { criteria: 'Bắt lỗi logic', original: <StatusBadge type="warn">So sánh 2 LLM output</StatusBadge>, optimized: <StatusBadge type="ok">Rule-based assertion độc lập</StatusBadge> },
  { criteria: 'Taxonomy update', original: <StatusBadge type="warn">Pass rate đơn thuần</StatusBadge>, optimized: <StatusBadge type="ok">4-signal diagnose + ngưỡng min data</StatusBadge> },
  { criteria: 'Domain rotation', original: <StatusBadge type="warn">Xoay vòng cố định</StatusBadge>, optimized: <StatusBadge type="ok">Weighted random, không lặp</StatusBadge> },
  { criteria: 'Retry policy', original: <StatusBadge type="bad">Loop 3 lần, không fallback</StatusBadge>, optimized: <StatusBadge type="ok">3-level escalation + archive fallback</StatusBadge> },
  { criteria: 'SLA 100 câu/tuần', original: <StatusBadge type="bad">Không đảm bảo</StatusBadge>, optimized: <StatusBadge type="ok">Đảm bảo qua archive fallback</StatusBadge> },
  { criteria: 'Token / tuần', original: <StatusBadge type="warn">Không tối ưu prompt</StatusBadge>, optimized: <StatusBadge type="ok">~55k tokens (giới hạn 7M)</StatusBadge> },
];

export default function ComparisonTable() {
  return (
    <table className="w-full border-collapse text-[0.85rem] mt-6">
      <thead>
        <tr>
          <th className="bg-[#111827] border border-[#1e2d45] px-4 py-3 text-left font-mono text-[0.7rem] uppercase tracking-[0.1em] text-[#5a7298]">
            Tiêu chí
          </th>
          <th className="bg-[#111827] border border-[#1e2d45] px-4 py-3 text-left font-mono text-[0.7rem] uppercase tracking-[0.1em] text-[#5a7298]">
            Pipeline gốc
          </th>
          <th className="bg-[#111827] border border-[#1e2d45] px-4 py-3 text-left font-mono text-[0.7rem] uppercase tracking-[0.1em] text-[#5a7298]">
            Pipeline tối ưu
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="hover:bg-[#111827] transition-colors">
            <td className="border border-[#1e2d45] px-4 py-2.5 text-[#e2eaf6] font-semibold text-[0.83rem]">
              {row.criteria}
            </td>
            <td className="border border-[#1e2d45] px-4 py-2.5 text-[#8ba3c7] align-top">
              {row.original}
            </td>
            <td className="border border-[#1e2d45] px-4 py-2.5 text-[#8ba3c7] align-top">
              {row.optimized}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
