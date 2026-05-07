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
      {/* Vertical timeline line */}
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
              {/* Step dot */}
              <div
                className="absolute -left-[42px] top-5 w-[22px] h-[22px] rounded-full bg-[#080c14] border-2 border-[#243550] flex items-center justify-center font-mono text-[0.65rem] font-bold transition-all duration-300 z-10"
                style={{
                  borderColor: isOpen ? '#00d4ff' : undefined,
                  color: isOpen ? '#00d4ff' : '#5a7298',
                  boxShadow: isOpen ? '0 0 12px rgba(0,212,255,0.25)' : undefined,
                }}
              >
                {String(step.id).padStart(2, '0')}
              </div>

              {/* Card */}
              <div
                className={`bg-[#0d1320] border rounded-xl overflow-hidden transition-all duration-300 ${
                  isOpen ? 'border-[#243550] shadow-[0_8px_32px_rgba(0,0,0,0.4)]' : 'border-[#1e2d45]'
                } group-hover:border-[#243550]`}
              >
                {/* Header */}
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

                {/* Body */}
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
