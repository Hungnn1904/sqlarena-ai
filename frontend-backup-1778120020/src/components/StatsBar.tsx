'use client';

import React from 'react';
import { motion } from 'framer-motion';
import type { StatItem } from './types';

interface StatsBarProps {
  stats: StatItem[];
}

const colorMap = {
  cyan: 'text-[#00d4ff]',
  green: 'text-[#00e5a0]',
  amber: 'text-[#ffb830]',
  rose: 'text-[#ff4d6d]',
  purple: 'text-[#a78bfa]',
};

export default function StatsBar({ stats }: StatsBarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="flex flex-wrap justify-center border border-[#243550] rounded-lg overflow-hidden max-w-[700px] mx-auto"
    >
      {stats.map((stat, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.3 + index * 0.1 }}
          className="flex-1 min-w-[110px] px-5 py-4 text-center border-r border-[#243550] last:border-r-0 bg-[#0d1320]"
        >
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
            className={`font-mono text-[1.4rem] font-bold block ${
              stat.color ? colorMap[stat.color] : 'text-[#00d4ff]'
            }`}
          >
            {typeof stat.value === 'number' ? (
              <CountUp end={stat.value} duration={1.5} delay={0.5 + index * 0.1} />
            ) : (
              stat.value
            )}
          </motion.span>
          <span className="text-[0.72rem] text-[#5a7298] uppercase tracking-[0.08em] mt-0.5 block">
            {stat.label}
          </span>
        </motion.div>
      ))}
    </motion.div>
  );
}

function CountUp({ end, duration, delay }: { end: number; duration: number; delay: number }) {
  const [count, setCount] = React.useState(0);
  const ref = React.useRef<HTMLSpanElement>(null);
  const [hasStarted, setHasStarted] = React.useState(false);

  React.useEffect(() => {
    const timer = setTimeout(() => setHasStarted(true), delay * 1000);
    return () => clearTimeout(timer);
  }, [delay]);

  React.useEffect(() => {
    if (!hasStarted) return;
    let startTime: number;
    let animationFrame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [hasStarted, end, duration]);

  return <span ref={ref}>{count}</span>;
}
