'use client';

import React from 'react';

interface FlowNodeProps {
  label: string;
  color?: 'cyan' | 'green' | 'amber' | 'rose' | 'default';
}

function FlowNode({ label, color = 'default' }: FlowNodeProps) {
  const colorMap: Record<string, string> = {
    cyan: 'badge-info',
    green: 'badge-easy',
    amber: 'badge-medium',
    rose: 'badge-hard',
    default: 'badge-neutral',
  };

  return (
    <span className={`inline-block rounded-md px-3 py-1 text-xs font-semibold ${colorMap[color]}`}>
      {label}
    </span>
  );
}

export default function FlowDiagram() {
  return (
    <div className="bg-surface border border-line rounded-xl p-6 space-y-3 text-sm text-text2">
      <div><FlowNode label="1. Chọn đặc tả kỹ năng (Target Spec)" color="cyan" /></div>
      <div><FlowNode label="2. Planner lập khung Blueprint & đánh giá rủi ro nhập nhằng" /></div>
      <div><FlowNode label="3. Model A (Generator) sinh câu hỏi tiếng Việt & SQL mẫu" color="green" /></div>
      <div><FlowNode label="4. Model B (Reviewer) giải độc lập 3 lần trên PostgreSQL 17" color="amber" /></div>
      <div><FlowNode label="5. Đối chiếu kết quả & chuyển sang hàng đợi kiểm duyệt" color="cyan" /></div>
    </div>
  );
}
