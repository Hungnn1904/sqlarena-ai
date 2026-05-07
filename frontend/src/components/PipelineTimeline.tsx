'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PipelineStep, BadgeVariant } from './types';

interface PipelineTimelineProps {
  steps: PipelineStep[];
  defaultOpen?: number;
}

const badgeStyles: Record<BadgeVariant, string> = {
  llm: 'bg-[rgba(167,139,250,0.1)] text-[#a78bfa] border border-[#a78bfa]',
  rule: 'bg-[rgba(0,229,160,0.1)] text-[#00e5a0] border border-[#00e5a0]',
  db: 'bg-[rgba(255,184,48,0.1)] text-[#ffb830] border border-[#ffb830]',
  new: 'bg-[rgba(255,77,109,0.1)] text-[#ff4d6d] border border-[#ff4d6d]',
  free: 'bg-[rgba(0,229,160,0.15)] text-[#00e5a0] border border-[#00e5a0]',
};

const statusColor: Record<string, string> = {
  pending: '#5a7298',
  running: '#00d4ff',
  completed: '#00e5a0',
  failed: '#ff4d6d',
  skipped: '#8ba3c7',
};

export default function PipelineTimeline({ steps, defaultOpen = 1 }: PipelineTimelineProps) {
  const [openId, setOpenId] = React.useState<number | null>(defaultOpen);

  const toggle = (id: number) => {
    setOpenId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="relative pl-[52px]">
      <div
        className="absolute left-[19px] top-7 bottom-7 w-0.5 rounded-full"
        style={{
          background: 'linear-gradient(to bottom, #00d4ff, #00e5a0, #00d4ff)',
          opacity: 0.3,
        }}
      />

      <div className="space-y-8">
        {steps.map((step, index) => {
          const isOpen = openId === step.id;
          const status = step.status || 'pending';
          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.1 + index * 0.1 }}
              className="relative group"
            >
              <div
                className="absolute -left-[42px] top-5 w-[22px] h-[22px] rounded-full bg-[#080c14] border-2 border-[#243550] flex items-center justify-center font-mono text-[0.65rem] font-bold transition-all duration-300 z-10 group-hover:border-[#00d4ff] group-hover:text-[#00d4ff] group-hover:shadow-[0_0_12px_rgba(0,212,255,0.25)]"
                style={{
                  borderColor: isOpen ? '#00d4ff' : undefined,
                  color: isOpen ? '#00d4ff' : '#5a7298',
                  boxShadow: isOpen ? '0 0 12px rgba(0,212,255,0.25)' : undefined,
                }}
              >
                {String(step.id).padStart(2, '0')}
              </div>

              <div
                className={`bg-[#0d1320] border rounded-xl overflow-hidden transition-all duration-300 ${
                  isOpen ? 'border-[#243550] shadow-[0_8px_32px_rgba(0,0,0,0.4)]' : 'border-[#1e2d45]'
                } group-hover:border-[#243550]`}
              >
                <button
                  onClick={() => toggle(step.id)}
                  className="w-full px-6 py-5 flex items-center justify-between gap-3 flex-wrap border-b transition-colors duration-300"
                  style={{
                    borderBottomColor: isOpen ? '#243550' : 'transparent',
                    borderBottomWidth: '1px',
                  }}
                >
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono text-[0.7rem] text-[#5a7298] min-w-[60px]">
                      BƯỚC {String(step.id).padStart(2, '0')}
                    </span>
                    <span className="text-[1.1rem] font-bold text-[#e2eaf6]">
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
