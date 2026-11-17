'use client';

import React from 'react';
import { Zap, Search, RefreshCw, Download } from 'lucide-react';

interface QuickActionsProps {
  onAction: (action: 'generate' | 'verify' | 'pipeline' | 'export') => void;
}

const actions = [
  { id: 'generate' as const, label: 'Sinh đề mới', icon: Zap },
  { id: 'verify' as const, label: 'Kiểm tra SQL', icon: Search },
  { id: 'pipeline' as const, label: 'Tiến trình AI', icon: RefreshCw },
  { id: 'export' as const, label: 'Xuất dữ liệu', icon: Download },
];

export default function QuickActions({ onAction }: QuickActionsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <button
            key={action.id}
            type="button"
            onClick={() => onAction(action.id)}
            className="btn-secondary rounded-xl p-5 text-center flex flex-col items-center justify-center gap-2 min-h-24"
          >
            <Icon className="w-5 h-5 text-brand" />
            <div className="text-sm font-semibold text-ink">{action.label}</div>
          </button>
        );
      })}
    </div>
  );
}
