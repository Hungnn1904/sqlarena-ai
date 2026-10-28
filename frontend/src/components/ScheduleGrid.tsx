'use client';

import React from 'react';

interface ScheduleItem {
  time: string;
  description: React.ReactNode;
}

const items: ScheduleItem[] = [
  {
    time: 'CN 22:00',
    description: (
      <>
        Chạy batch 100 câu — ước tính 2–3 giờ với retry. Chạy overnight, không ảnh hưởng user.
      </>
    ),
  },
  {
    time: 'T2 sáng',
    description: (
      <>
        Admin review queue ~100 câu <code className="text-[#ffb830] bg-[rgba(255,184,48,0.08)] px-1 py-0.5 rounded">pending_review</code>. Approve → pool tuần mới.
      </>
    ),
  },
  {
    time: 'T2 00:00',
    description: (
      <>
        Pool mới active cho người dùng. Câu từ archive fallback đã được đánh dấu để ưu tiên review lại sau.
      </>
    ),
  },
  {
    time: 'T2–T7',
    description: (
      <>
        Analytics thu thập pass rate, avg_attempts, hint_usage theo topic — làm input cho Target Selector tuần sau.
      </>
    ),
  },
];

export default function ScheduleGrid() {
  return (
    <div className="bg-[#0d1320] border border-[#243550] rounded-lg overflow-hidden my-6">
      {items.map((item, i) => (
        <div
          key={i}
          className="grid grid-cols-[140px_1fr] border-b border-[#1e2d45] last:border-b-0"
        >
          <div className="px-4 py-3.5 font-mono text-[0.78rem] text-[#ffb830] bg-[#111827] border-r border-[#1e2d45]">
            {item.time}
          </div>
          <div className="px-4 py-3.5 text-[0.85rem] text-[#8ba3c7]">
            {item.description}
          </div>
        </div>
      ))}
    </div>
  );
}
