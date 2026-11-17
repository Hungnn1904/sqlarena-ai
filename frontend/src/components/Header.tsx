'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface HeaderProps {
  badgeText?: string;
  title: React.ReactNode;
  subtitle?: string;
}

export default function Header({
  badgeText = 'SQL Arena PTIT: AI Question Generator Pipeline',
  title,
  subtitle = 'Hệ thống tự động hóa sinh câu hỏi SQL có kiểm soát, tối ưu chi phí và phù hợp môi trường thực tế.',
}: HeaderProps) {
  return (
    <header className="relative pt-14 pb-10 text-center">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="inline-flex items-center gap-2 badge-info rounded-md px-3.5 py-1.5 text-xs font-semibold mb-5"
      >
        <span>{badgeText}</span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.05 }}
        className="text-3xl sm:text-4xl font-bold tracking-tight leading-tight mb-4 text-ink"
      >
        {title}
      </motion.h1>

      {subtitle && (
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.1 }}
          className="text-base text-text2 max-w-[560px] mx-auto mb-8"
        >
          {subtitle}
        </motion.p>
      )}
    </header>
  );
}
