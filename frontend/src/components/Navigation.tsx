'use client';

import React from 'react';
import { motion } from 'framer-motion';
import type { NavItem } from './types';

interface NavigationProps {
  items: NavItem[];
  activeId: string;
  onChange: (id: string) => void;
}

export default function Navigation({ items, activeId, onChange }: NavigationProps) {
  return (
    <nav className="sticky top-0 z-40 bg-surface border-b border-line">
      <div className="max-w-[1060px] mx-auto px-6">
        <ul className="flex gap-1 overflow-x-auto scrollbar-hide">
          {items.map((item) => {
            const isActive = item.id === activeId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onChange(item.id)}
                  className="relative px-4 min-h-11 text-sm font-medium transition-colors duration-200 whitespace-nowrap"
                >
                  <span className={isActive ? 'text-brand font-semibold' : 'text-muted hover:text-ink'}>
                    {item.label}
                  </span>
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand"
                      transition={{ type: 'spring', stiffness: 450, damping: 30 }}
                    />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
