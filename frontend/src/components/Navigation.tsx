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
    <nav className="sticky top-0 z-50 backdrop-blur-md bg-[#080c14]/80 border-b border-[#1e2d45]">
      <div className="max-w-[1060px] mx-auto px-6">
        <ul className="flex gap-1 overflow-x-auto scrollbar-hide">
          {items.map((item) => {
            const isActive = item.id === activeId;
            return (
              <li key={item.id}>
                <button
                  onClick={() => onChange(item.id)}
                  className="relative px-4 py-3.5 text-sm font-medium transition-colors duration-200 whitespace-nowrap"
                >
                  <span className={isActive ? 'text-[#00d4ff]' : 'text-[#5a7298] hover:text-[#8ba3c7]'}>
                    {item.label}
                  </span>
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#00d4ff]"
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
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
