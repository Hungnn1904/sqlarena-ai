'use client';

import React from 'react';

interface FlowNodeProps {
  label: string;
  color?: 'cyan' | 'green' | 'amber' | 'rose' | 'default';
}

function FlowNode({ label, color = 'default' }: FlowNodeProps) {
  const colorMap: Record<string, string> = {
    cyan: 'border-[#00d4ff] text-[#00d4ff]',
    green: 'border-[#00e5a0] text-[#00e5a0]',
    amber: 'border-[#ffb830] text-[#ffb830]',
    rose: 'border-[#ff4d6d] text-[#ff4d6d]',
    default: 'border-[#243550] text-[#e2eaf6]',
  };

  return (
    <span className={`inline-block bg-[#111827] border rounded px-2.5 py-0.5 ${colorMap[color]}`}>
      {label}
    </span>
  );
}

export default function FlowDiagram() {
  return (
    <div className="bg-[#060a10] border border-[#1e2d45] rounded-lg p-6 font-mono text-[0.75rem] leading-[2] text-[#8ba3c7] overflow-x-auto whitespace-pre">
      <FlowNode label="Target Spec" color="cyan" />
      {'\n↓\n'}
      <FlowNode label="Bước 3: Planner" />{' '}&rarr;{' '}Blueprint <span className="text-[#ff4d6d]">+ ambiguity_risk</span>
      {'\n↓\n'}
      <FlowNode label="Bước 4: Generator" />{' '}&rarr;{' '}draft_question (theo blueprint + domain random)
      {'\n↓\n'}
      <FlowNode label="Bước 5: Clarity Check (LLM)" />
      {'\n  '}<span className="text-[#ff4d6d]">├─ fail →</span> rewrite question_text &rarr; re-check
      {'\n  '}<span className="text-[#00e5a0]">└─ pass →</span> tiếp tục
      {'\n↓\n'}
      <FlowNode label="Bước 5: Ground Truth Assertion (rule)" />
      {'\n  '}<span className="text-[#ff4d6d]">├─ fail →</span> retry từ Generator (escalation policy)
      {'\n  '}<span className="text-[#00e5a0]">└─ pass →</span> tiếp tục
      {'\n↓\n'}
      <FlowNode label="Bước 6: Execution Engine" />
      {'\n  '}<span className="text-[#ff4d6d]">├─ fail →</span> retry (escalation) hoặc archive fallback
      {'\n  '}<span className="text-[#00e5a0]">└─ pass →</span> tiếp tục
      {'\n↓\n'}
      <FlowNode label="Bước 7: Package → pending_review ✓" color="cyan" />
    </div>
  );
}
