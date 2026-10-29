'use client';

import React from 'react';

interface FlowNodeProps {
  label: string;
  color?: 'cyan' | 'green' | 'amber' | 'rose' | 'default';
}

function FlowNode({ label, color = 'default' }: FlowNodeProps) {
  const colorMap: Record<string, string> = {
    cyan: 'border-[#5C7F71] text-[#46685A] bg-[#5C7F71]/10 font-semibold',
    green: 'border-[#5C7F71] text-[#46685A] bg-[#5C7F71]/10 font-semibold',
    amber: 'border-[#BA8530] text-[#8A621B] bg-[#BA8530]/10 font-semibold',
    rose: 'border-[#802520] text-[#802520] bg-[#802520]/10 font-semibold',
    default: 'border-[var(--line)] text-[var(--ink)] bg-[var(--soft)] font-semibold',
  };

  return (
    <span className={`inline-block border rounded px-2.5 py-0.5 ${colorMap[color]}`}>
      {label}
    </span>
  );
}

export default function FlowDiagram() {
  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-lg p-6 font-mono text-[0.78rem] leading-[2.1] text-[var(--text2)] overflow-x-auto whitespace-pre">
      <FlowNode label="Target Spec" color="cyan" />
      {'\n↓\n'}
      <FlowNode label="Bước 3: Planner" />{' '}&rarr;{' '}Blueprint <span className="text-[var(--copper)] font-semibold">+ ambiguity_risk</span>
      {'\n↓\n'}
      <FlowNode label="Bước 4: Generator" />{' '}&rarr;{' '}draft_question (theo blueprint + domain random)
      {'\n↓\n'}
      <FlowNode label="Bước 5: Clarity Check (LLM)" />
      {'\n  '}<span className="text-[var(--red)] font-semibold">├─ fail →</span> rewrite question_text &rarr; re-check
      {'\n  '}<span className="text-[var(--green)] font-semibold">└─ pass →</span> tiếp tục
      {'\n↓\n'}
      <FlowNode label="Bước 5: Ground Truth Assertion (rule)" />
      {'\n  '}<span className="text-[var(--red)] font-semibold">├─ fail →</span> retry từ Generator (escalation policy)
      {'\n  '}<span className="text-[var(--green)] font-semibold">└─ pass →</span> tiếp tục
      {'\n↓\n'}
      <FlowNode label="Bước 6: Execution Engine" />
      {'\n  '}<span className="text-[var(--red)] font-semibold">├─ fail →</span> retry (escalation) hoặc archive fallback
      {'\n  '}<span className="text-[var(--green)] font-semibold">└─ pass →</span> tiếp tục
      {'\n↓\n'}
      <FlowNode label="Bước 7: Package → pending_review ✓" color="cyan" />
    </div>
  );
}
