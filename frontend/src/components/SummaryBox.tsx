'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface SummaryStat {
  label: string;
  value: string | number;
  description?: string;
  color?: 'cyan' | 'green' | 'amber' | 'rose' | 'purple';
}

interface SummaryBoxProps {
  stats: SummaryStat[];
}

const colorMap: Record<string, string> = {
  cyan: 'text-[#00d4ff] border-[#00d4ff]/20 bg-[rgba(0,212,255,0.06)]',
  green: 'text-[#00e5a0] border-[#00e5a0]/20 bg-[rgba(0,229,160,0.06)]',
  amber: 'text-[#ffb830] border-[#ffb830]/20 bg-[rgba(255,184,48,0.06)]',
  rose: 'text-[#ff4d6d] border-[#ff4d6d]/20 bg-[rgba(255,77,109,0.06)]',
  purple: 'text-[#a78bfa] border-[#a78bfa]/20 bg-[rgba(167,139,250,0.06)]',
};

export default function SummaryBox({ stats }: SummaryBoxProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: i * 0.1 }}
          className={`rounded-xl border p-5 ${colorMap[stat.color || 'cyan']}`}
        >
          <div className="font-mono text-[0.7rem] uppercase tracking-[0.12em] opacity-70 mb-2">
            {stat.label}
          </div>
          <div className="text-2xl font-bold mb-1">{stat.value}</div>
          {stat.description && (
            <div className="text-[0.8rem] opacity-60">{stat.description}</div>
          )}
        </motion.div>
      ))}
    </div>
  );
}
