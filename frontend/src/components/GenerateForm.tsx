'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Difficulty, Topic } from './types';

interface GenerateFormProps {
  topics?: Topic[];
  onSubmit?: (data: GenerateFormData) => void | Promise<void>;
  isLoading?: boolean;
  taskData?: { status?: string; result?: unknown; error?: string | null } | null;
}

export interface GenerateFormData {
  difficulty: Difficulty;
  count: number;
  topics: Topic[];
}

const difficultyConfig: Record<Difficulty, { label: string; color: string; hover: string }> = {
  easy: {
    label: 'Easy',
    color: 'border-[#00e5a0] text-[#00e5a0] bg-[rgba(0,229,160,0.08)]',
    hover: 'hover:bg-[rgba(0,229,160,0.15)] hover:shadow-[0_0_16px_rgba(0,229,160,0.15)]',
  },
  medium: {
    label: 'Medium',
    color: 'border-[#ffb830] text-[#ffb830] bg-[rgba(255,184,48,0.08)]',
    hover: 'hover:bg-[rgba(255,184,48,0.15)] hover:shadow-[0_0_16px_rgba(255,184,48,0.15)]',
  },
  hard: {
    label: 'Hard',
    color: 'border-[#ff4d6d] text-[#ff4d6d] bg-[rgba(255,77,109,0.08)]',
    hover: 'hover:bg-[rgba(255,77,109,0.15)] hover:shadow-[0_0_16px_rgba(255,77,109,0.15)]',
  },
};

export default function GenerateForm({ topics = [], onSubmit, isLoading = false, taskData }: GenerateFormProps) {
  const [difficulty, setDifficulty] = React.useState<Difficulty>('easy');
  const [count, setCount] = React.useState(10);
  const [selectedTopics, setSelectedTopics] = React.useState<Topic[]>([]);

  const toggleTopic = (topic: Topic) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit?.({ difficulty, count, topics: selectedTopics });
  };

  const allTopics: Topic[] = topics.length > 0
    ? topics
    : ['SELECT', 'JOIN', 'WHERE', 'GROUP BY', 'HAVING', 'SUBQUERY', 'CTE', 'WINDOW FUNCTION'];

  return (
    <motion.form
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      onSubmit={handleSubmit}
      className="bg-[#0d1320] border border-[#1e2d45] rounded-xl p-6 md:p-8 space-y-8"
    >
      <div>
        <label className="block font-mono text-[0.7rem] uppercase tracking-[0.12em] text-[#5a7298] mb-4">
          Difficulty
        </label>
        <div className="flex flex-wrap gap-3">
          {(Object.keys(difficultyConfig) as Difficulty[]).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDifficulty(d)}
              className={`relative px-6 py-3 rounded-lg border font-semibold text-sm uppercase tracking-wider transition-all duration-300 ${
                difficultyConfig[d].color
              } ${difficultyConfig[d].hover} ${
                difficulty === d ? 'ring-2 ring-offset-2 ring-offset-[#0d1320] ring-current shadow-lg' : 'opacity-60'
              }`}
            >
              {difficultyConfig[d].label}
              <AnimatePresence>
                {difficulty === d && (
                  <motion.div
                    layoutId="difficultyIndicator"
                    className="absolute inset-0 rounded-lg border-2 border-current opacity-20"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
              </AnimatePresence>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block font-mono text-[0.7rem] uppercase tracking-[0.12em] text-[#5a7298] mb-4">
          Number of Questions
        </label>
        <div className="flex items-center gap-6">
          <input
            type="range"
            min={1}
            max={100}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer bg-[#1e2d45] accent-[#00d4ff]"
            style={{
              background: `linear-gradient(to right, #00d4ff ${count}%, #1e2d45 ${count}%)`,
            }}
          />
          <motion.div
            key={count}
            initial={{ scale: 1.2 }}
            animate={{ scale: 1 }}
            className="w-16 text-center font-mono text-xl font-bold text-[#00d4ff]"
          >
            {count}
          </motion.div>
        </div>
        <div className="flex justify-between text-[0.65rem] text-[#5a7298] mt-2 font-mono">
          <span>1</span>
          <span>50</span>
          <span>100</span>
        </div>
      </div>

      <div>
        <label className="block font-mono text-[0.7rem] uppercase tracking-[0.12em] text-[#5a7298] mb-4">
          Topics
          <span className="ml-2 text-[#8ba3c7] normal-case">({selectedTopics.length} selected)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {allTopics.map((topic) => {
            const isSelected = selectedTopics.includes(topic);
            return (
              <button
                key={topic}
                type="button"
                onClick={() => toggleTopic(topic)}
                className={`px-3 py-1.5 rounded-md text-sm border transition-all duration-200 ${
                  isSelected
                    ? 'border-[#00d4ff] text-[#00d4ff] bg-[rgba(0,212,255,0.08)] shadow-[0_0_8px_rgba(0,212,255,0.1)]'
                    : 'border-[#1e2d45] text-[#5a7298] hover:border-[#243550] hover:text-[#8ba3c7]'
                }`}
              >
                {topic}
              </button>
            );
          })}
        </div>
      </div>

      <motion.button
        type="submit"
        disabled={isLoading}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`w-full py-4 rounded-lg font-semibold text-sm uppercase tracking-wider transition-all duration-300 relative overflow-hidden ${
          isLoading
            ? 'bg-[#1e2d45] text-[#5a7298] cursor-not-allowed'
            : 'bg-gradient-to-r from-[#00d4ff] to-[#00e5a0] text-[#080c14] hover:shadow-[0_0_32px_rgba(0,212,255,0.25)]'
        }`}
      >
        <AnimatePresence mode="wait">
          {isLoading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center gap-3"
            >
              <span className="relative flex h-4 w-4">
                <span className="animate-spin absolute inline-flex h-full w-full rounded-full border-2 border-current border-t-transparent opacity-75" />
              </span>
              Generating...
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              Generate Questions
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {taskData && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="overflow-hidden"
        >
          <div className={`rounded-lg border p-4 ${
            taskData.status === 'done'
              ? 'bg-[rgba(0,229,160,0.06)] border-[#00e5a0]/30'
              : taskData.status === 'failed'
              ? 'bg-[rgba(255,77,109,0.06)] border-[#ff4d6d]/30'
              : 'bg-[rgba(0,212,255,0.06)] border-[#00d4ff]/30'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2 h-2 rounded-full ${
                taskData.status === 'done' ? 'bg-[#00e5a0]' : taskData.status === 'failed' ? 'bg-[#ff4d6d]' : 'bg-[#00d4ff] animate-pulse'
              }`} />
              <span className={`font-mono text-xs uppercase tracking-wider font-semibold ${
                taskData.status === 'done' ? 'text-[#00e5a0]' : taskData.status === 'failed' ? 'text-[#ff4d6d]' : 'text-[#00d4ff]'
              }`}>
                Task: {taskData.status}
              </span>
            </div>
            {taskData.error && (
              <p className="text-[0.8rem] text-[#ff4d6d] ml-4">{taskData.error}</p>
            )}
          </div>
        </motion.div>
      )}
    </motion.form>
  );
}
