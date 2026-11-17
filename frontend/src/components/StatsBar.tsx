'use client';

import React from 'react';
import type { StatItem } from './types';

interface StatsBarProps {
  stats: StatItem[];
}

const colorMap: Record<string, string> = {
  cyan: 'text-brand',
  green: 'text-brand',
  amber: 'text-copper',
  rose: 'text-danger',
  purple: 'text-info',
};

export default function StatsBar({ stats }: StatsBarProps) {
  return (
    <div className="flex flex-col sm:flex-row justify-center border border-line rounded-xl overflow-hidden max-w-[700px] mx-auto bg-surface tabular-nums">
      {stats.map((stat, index) => (
        <div
          key={index}
          className="flex-1 min-w-[110px] px-5 py-4 text-center border-b sm:border-b-0 sm:border-r border-line last:border-b-0 last:sm:border-r-0 bg-surface hover:bg-soft transition-colors"
        >
          <span
            className={`text-2xl font-bold block ${
              stat.color ? colorMap[stat.color] || 'text-brand' : 'text-brand'
            }`}
          >
            {stat.value}
          </span>
          <span className="text-xs text-muted mt-1 block">
            {stat.label}
          </span>
        </div>
      ))}
    </div>
  );
}
