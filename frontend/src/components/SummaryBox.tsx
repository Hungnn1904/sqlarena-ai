'use client';

import React from 'react';

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
  cyan: 'badge-info',
  green: 'badge-easy',
  amber: 'badge-medium',
  rose: 'badge-hard',
  purple: 'badge-neutral',
};

export default function SummaryBox({ stats }: SummaryBoxProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 tabular-nums">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className={`rounded-xl p-5 ${colorMap[stat.color || 'cyan']}`}
        >
          <div className="text-xs font-medium mb-2">
            {stat.label}
          </div>
          <div className="text-2xl font-bold mb-1">{stat.value}</div>
          {stat.description && (
            <div className="text-xs opacity-85">{stat.description}</div>
          )}
        </div>
      ))}
    </div>
  );
}
