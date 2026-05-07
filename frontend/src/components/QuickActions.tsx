'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Search, RefreshCw, Download } from 'lucide-react';

interface QuickActionsProps {
  onAction: (action: 'generate' | 'verify' | 'pipeline' | 'export') => void;
}

const actions = [
  { id: 'generate' as const, label: 'Generate', icon: Zap, color: 'from-[#00d4ff] to-[#00e5a0]' },
  { id: 'verify' as const, label: 'Verify SQL', icon: Search, color: 'from-[#a78bfa] to-[#00d4ff]' },
  { id: 'pipeline' as const, label: 'Pipeline', icon: RefreshCw, color: 'from-[#ffb830] to-[#ff4d6d]' },
  { id: 'export' as const, label: 'Export', icon: Download, color: 'from-[#00e5a0] to-[#a78bfa]' },
];

export default function QuickActions({ onAction }: QuickActionsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {actions.map((action, i) => {
        const Icon = action.icon;
        return (
          <motion.button
            key={action.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 + i * 0.1 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onAction(action.id)}
            className={`relative overflow-hidden rounded-xl border border-[#1e2d45] bg-gradient-to-br ${action.color} p-px`}
          >
            <div className="bg-[#0d1320] rounded-xl p-5 text-center hover:bg-[#111827] transition-colors h-full flex flex-col items-center justify-center gap-2">
              <Icon className="w-5 h-5 text-[#e2eaf6]" />
              <div className="text-sm font-semibold text-[#e2eaf6]">{action.label}</div>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}
