'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGenerate, useTask } from '@/lib/hooks';
import { Loader2, Zap } from 'lucide-react';

type Difficulty = 'easy' | 'medium' | 'hard';
type Topic = 'SELECT' | 'JOIN' | 'WHERE' | 'GROUP BY' | 'HAVING' | 'SUBQUERY' | 'CTE' | 'WINDOW FUNCTION';

const difficultyConfig: Record<Difficulty, { label: string; color: string; hover: string; ring: string }> = {
  easy: {
    label: 'Easy',
    color: 'border-[#00e5a0] text-[#00e5a0] bg-[rgba(0,229,160,0.08)]',
    hover: 'hover:bg-[rgba(0,229,160,0.15)] hover:shadow-[0_0_16px_rgba(0,229,160,0.15)]',
    ring: 'ring-[#00e5a0]',
  },
  medium: {
    label: 'Medium',
    color: 'border-[#ffb830] text-[#ffb830] bg-[rgba(255,184,48,0.08)]',
    hover: 'hover:bg-[rgba(255,184,48,0.15)] hover:shadow-[0_0_16px_rgba(255,184,48,0.15)]',
    ring: 'ring-[#ffb830]',
  },
  hard: {
    label: 'Hard',
    color: 'border-[#ff4d6d] text-[#ff4d6d] bg-[rgba(255,77,109,0.08)]',
    hover: 'hover:bg-[rgba(255,77,109,0.15)] hover:shadow-[0_0_16px_rgba(255,77,109,0.15)]',
    ring: 'ring-[#ff4d6d]',
  },
};

const allTopics: Topic[] = [
  'SELECT',
  'JOIN',
  'WHERE',
  'GROUP BY',
  'HAVING',
  'SUBQUERY',
  'CTE',
  'WINDOW FUNCTION',
];

export default function GenerateForm() {
  const [difficulties, setDifficulties] = React.useState<Difficulty[]>(['easy']);
  const [count, setCount] = React.useState(3);
  const [selectedTopic, setSelectedTopic] = React.useState<Topic | ''>('');
  const [taskId, setTaskId] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<unknown | null>(null);

  const generateMutation = useGenerate();
  const { data: taskData } = useTask(taskId || '');

  const toggleDifficulty = (d: Difficulty) => {
    setDifficulties((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (difficulties.length === 0) return;

    setResult(null);
    setTaskId(null);

    const specs =
      selectedTopic.length > 0
        ? difficulties.map((d) => `${selectedTopic}_${d}`.toUpperCase())
        : difficulties.map((d) => d.toUpperCase());

    try {
      const res = await generateMutation.mutateAsync({
        specs,
        questions_per_spec: count,
      });

      if (res.task_id) {
        setTaskId(res.task_id);
      } else if (res.status === 'done') {
        setResult(res.result);
      }
    } catch (err: any) {
      console.error('Generate error:', err);
    }
  };

  React.useEffect(() => {
    if (taskData?.status === 'done' && taskData?.result) {
      setResult(taskData.result);
    }
  }, [taskData]);

  const isLoading = generateMutation.isPending || (!!taskId && taskData?.status !== 'done' && taskData?.status !== 'failed');

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
          <span className="ml-2 text-[#8ba3c7] normal-case">({difficulties.length} selected)</span>
        </label>
        <div className="flex flex-wrap gap-3">
          {(Object.keys(difficultyConfig) as Difficulty[]).map((d) => {
            const selected = difficulties.includes(d);
            const cfg = difficultyConfig[d];
            return (
              <button
                key={d}
                type="button"
                onClick={() => toggleDifficulty(d)}
                className={`relative px-5 py-2.5 rounded-lg border font-semibold text-sm uppercase tracking-wider transition-all duration-300 ${cfg.color} ${cfg.hover} ${
                  selected ? `ring-2 ring-offset-2 ring-offset-[#0d1320] ${cfg.ring} shadow-lg` : 'opacity-50'
                }`}
              >
                {cfg.label}
              </button>
            );
          })}
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
            max={10}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer bg-[#1e2d45] accent-[#00d4ff]"
            style={{
              background: `linear-gradient(to right, #00d4ff ${(count - 1) * 11.11}%, #1e2d45 ${(count - 1) * 11.11}%)`,
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
          <span>5</span>
          <span>10</span>
        </div>
      </div>

      <div>
        <label className="block font-mono text-[0.7rem] uppercase tracking-[0.12em] text-[#5a7298] mb-4">
          Topic
        </label>
        <select
          value={selectedTopic}
          onChange={(e) => setSelectedTopic(e.target.value as Topic | '')}
          className="w-full bg-[#0d1320] border border-[#1e2d45] rounded-lg px-3 py-2.5 text-sm text-[#e2eaf6] focus:outline-none focus:border-[#00d4ff]"
        >
          <option value="">All Topics</option>
          {allTopics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <motion.button
        type="submit"
        disabled={isLoading || difficulties.length === 0}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`w-full py-4 rounded-lg font-semibold text-sm uppercase tracking-wider transition-all duration-300 relative overflow-hidden flex items-center justify-center gap-2 ${
          isLoading || difficulties.length === 0
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
              <Loader2 className="w-4 h-4 animate-spin" />
              {taskData?.status === 'running' ? (
                <span>Generating… ({taskData?.progress ?? 'in progress'})</span>
              ) : (
                <span>Generating…</span>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2"
            >
              <Zap className="w-4 h-4" />
              Generate Questions
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {generateMutation.isError && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg border bg-[rgba(255,77,109,0.08)] border-[#ff4d6d]/40 p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-[#ff4d6d] animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-wider font-semibold text-[#ff4d6d]">
              Backend Error
            </span>
          </div>
          <p className="text-[0.82rem] text-[#fda4af] leading-relaxed">
            {(generateMutation.error as any)?.response?.data?.detail || 'LLM service unavailable. Please ensure Ollama is running or configure Gemini API key in .env'}
          </p>
        </motion.div>
      )}

      {taskData && taskData.status !== 'done' && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="overflow-hidden"
        >
          <div
            className={`rounded-lg border p-4 ${
              taskData.status === 'failed'
                ? 'bg-[rgba(255,77,109,0.06)] border-[#ff4d6d]/30'
                : 'bg-[rgba(0,212,255,0.06)] border-[#00d4ff]/30'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`w-2 h-2 rounded-full ${
                  taskData.status === 'failed' ? 'bg-[#ff4d6d]' : 'bg-[#00d4ff] animate-pulse'
                }`}
              />
              <span
                className={`font-mono text-xs uppercase tracking-wider font-semibold ${
                  taskData.status === 'failed' ? 'text-[#ff4d6d]' : 'text-[#00d4ff]'
                }`}
              >
                Task: {taskData.status}
              </span>
            </div>
            {taskData.error && <p className="text-[0.8rem] text-[#ff4d6d] ml-4">{taskData.error}</p>}
          </div>
        </motion.div>
      )}

      <AnimatePresence>
        {!!result && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35 }}
            className="overflow-hidden"
          >
            <div className="rounded-lg border bg-[rgba(0,229,160,0.06)] border-[#00e5a0]/30 p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 rounded-full bg-[#00e5a0]" />
                <span className="font-mono text-xs uppercase tracking-wider font-semibold text-[#00e5a0]">
                  Result
                </span>
              </div>
              <pre className="bg-[#080c14] border border-[#1e2d45] rounded-lg p-4 overflow-auto text-[0.78rem] leading-[1.6] font-mono text-[#a8c4e8] max-h-[480px]">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.form>
  );
}
