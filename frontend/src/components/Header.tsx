'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface HeaderProps {
  badgeText?: string;
  title: React.ReactNode;
  subtitle?: string;
}

export default function Header({
  badgeText = 'SQLARENA · AI QUESTION GENERATOR PIPELINE · v2.0',
  title,
  subtitle = 'Hệ thống tự động hóa sinh câu hỏi SQL có kiểm soát — tối ưu chi phí, đủ coverage, phù hợp production.',
}: HeaderProps) {
  return (
    <header className="relative pt-16 pb-12 md:pt-[72px] md:pb-14 text-center">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="inline-flex items-center gap-2 bg-[rgba(0,212,255,0.12)] border border-[#00d4ff] rounded px-3.5 py-1.5 font-mono text-[0.72rem] text-[#00d4ff] tracking-[0.12em] uppercase mb-6"
      >
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#00d4ff] animate-pulse-dot" />
        {badgeText}
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="text-[clamp(2.2rem,5vw,3.6rem)] font-extrabold tracking-[-0.03em] leading-[1.1] mb-4 bg-gradient-to-br from-white via-[#00d4ff] to-[#00e5a0] bg-clip-text text-transparent"
      >
        {title}
      </motion.h1>

      {subtitle && (
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-base text-[#8ba3c7] max-w-[560px] mx-auto mb-10"
        >
          {subtitle}
        </motion.p>
      )}
    </header>
  );
}
