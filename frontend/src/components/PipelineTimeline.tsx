'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PipelineStep, BadgeVariant } from './types';

interface PipelineTimelineProps {
  steps: PipelineStep[];
  defaultOpen?: number;
}

const badgeStyles: Record<BadgeVariant, string> = {
  llm: 'bg-[#B2653B]/15 text-[#B2653B] border border-[#B2653B]/40',
  rule: 'bg-[#5C7F71]/15 text-[#46685A] border border-[#5C7F71]/40',
  db: 'bg-[#BA8530]/15 text-[#8A621B] border border-[#BA8530]/40',
  new: 'bg-[#802520]/15 text-[#802520] border border-[#802520]/40',
  free: 'bg-[#5C7F71]/15 text-[#46685A] border border-[#5C7F71]/40',
};

const statusColor: Record<string, string> = {
  pending: '#6F6B60',
  running: '#B2653B',
  completed: '#5C7F71',
  failed: '#802520',
  skipped: '#6F6B60',
};

export default function PipelineTimeline({ steps, defaultOpen = 1 }: PipelineTimelineProps) {
  const [openId, setOpenId] = React.useState<number | null>(defaultOpen);

  const toggle = (id: number) => {
    setOpenId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="relative pl-[52px]">
      <div
        className="absolute left-[19px] top-7 bottom-7 w-0.5 rounded-full bg-[var(--green)] opacity-35"
      />

      <div className="space-y-4">
        {steps.map((step, index) => {
          const isOpen = openId === step.id;
          const status = step.status || 'pending';
          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, delay: 0.05 + index * 0.06 }}
              className="relative group"
            >
              <div
                className="absolute -left-[42px] top-5 w-[24px] h-[24px] rounded-full bg-[var(--surface)] border border-[var(--green)] text-[var(--green)] flex items-center justify-center font-mono text-[0.68rem] font-bold transition-all duration-300 z-10"
              >
                {String(step.id).padStart(2, '0')}
              </div>

              <div
                className="bg-[var(--surface)] border border-[var(--line)] rounded-xl overflow-hidden transition-all duration-300 card-interactive"
              >
                <button
                  onClick={() => toggle(step.id)}
                  className="w-full px-5 py-4 flex items-center justify-between gap-3 flex-wrap border-b border-[var(--line)] transition-colors duration-300"
                >
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono text-[0.7rem] text-[var(--copper)] font-bold min-w-[60px]">
                      BƯỚC {String(step.id).padStart(2, '0')}
                    </span>
                    <span className="text-[1rem] font-bold text-[var(--ink)]">
                      {step.title}
                    </span>
                    {step.status && (
                      <span
                        className="ml-2 inline-block w-2 h-2 rounded-full"
                        style={{ backgroundColor: statusColor[status] }}
                      />
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    {step.badges.map((badge, i) => (
                      <span
                        key={i}
                        className={`font-mono text-[0.65rem] px-2 py-0.5 rounded font-semibold tracking-[0.05em] uppercase ${
                          badgeStyles[badge.variant]
                        }`}
                      >
                        {badge.label}
                      </span>
                    ))}
                    <motion.svg
                      animate={{ rotate: isOpen ? 180 : 0 }}
                      transition={{ duration: 0.3 }}
                      className="w-4 h-4 text-[#5a7298] ml-2 flex-shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </motion.svg>
                  </div>
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.35, ease: 'easeInOut' }}
                      className="overflow-hidden"
                    >
                      <motion.div
                        initial={{ y: -10 }}
                        animate={{ y: 0 }}
                        transition={{ duration: 0.3, delay: 0.05 }}
                        className="px-6 pb-6"
                      >
                        {step.content}
                      </motion.div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Helper sub-components for step body ── */

export function ExplainBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-[rgba(0,212,255,0.04)] border border-dashed border-[rgba(0,212,255,0.25)] rounded-md p-4 text-[0.88rem] text-[#8ba3c7] leading-relaxed">
      {children}
    </div>
  );
}

export function NewTag({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-[rgba(255,77,109,0.04)] border border-[rgba(255,77,109,0.2)] rounded-md p-4 text-[0.83rem] text-[#fda4af] leading-relaxed">
      {children}
    </div>
  );
}

export function IOGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
      {children}
    </div>
  );
}

export function IOBox({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#111827] border border-[#1e2d45] rounded-md p-3.5">
      <div className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-[#5a7298] mb-1.5">{label}</div>
      <div className="text-[0.85rem] text-[#8ba3c7] leading-relaxed">{children}</div>
    </div>
  );
}

export function SubTitle({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="font-mono text-[0.72rem] uppercase tracking-[0.12em] text-[#00d4ff] mt-5 mb-2">
      {children}
    </h4>
  );
}

export function BodyText({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[0.88rem] text-[#8ba3c7] mb-2.5 leading-relaxed">
      {children}
    </p>
  );
}

export function BodyList({ children }: { children: React.ReactNode }) {
  return (
    <ul className="list-disc pl-[18px] mb-3">
      {children}
    </ul>
  );
}

export function BodyListItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="text-[0.87rem] text-[#8ba3c7] mb-1 leading-relaxed">
      {children}
    </li>
  );
}

export function CodeBlock({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <pre
      className={`bg-[#060a10] border border-[#1e2d45] rounded-md p-4 overflow-x-auto font-mono text-[0.78rem] leading-[1.6] text-[#a8c4e8] my-2.5 ${className}`}
    >
      <code className="bg-none p-0 text-inherit text-[inherit]">{children}</code>
    </pre>
  );
}

export function TwoLayer({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-3.5">
      {children}
    </div>
  );
}

export function LayerBox({ title, titleColor = 'cyan', children }: { title: string; titleColor?: 'cyan' | 'green'; children: React.ReactNode }) {
  const colorClass = titleColor === 'green' ? 'text-[#00e5a0]' : 'text-[#00d4ff]';
  return (
    <div className="bg-[#111827] border border-[#1e2d45] rounded-md p-4">
      <div className={`font-mono text-[0.68rem] uppercase tracking-[0.1em] mb-2 flex items-center gap-1.5 ${colorClass}`}>
        {title}
      </div>
      {children}
    </div>
  );
}

export function RetryTable({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-3.5">
      {children}
    </div>
  );
}

export function RetryRow({ attempt, children }: { attempt: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[90px_1fr] gap-3 py-2.5 border-b border-[#1e2d45] last:border-b-0 items-start">
      <div className="font-mono text-[0.72rem] text-[#ffb830] font-semibold">{attempt}</div>
      <div className="text-[0.85rem] text-[#8ba3c7]">{children}</div>
    </div>
  );
}
