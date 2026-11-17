'use client';

import React from 'react';
import { useGenerate, useTask } from '@/lib/hooks';
import { Loader2, Zap } from 'lucide-react';

type Difficulty = 'easy' | 'medium' | 'hard';
type Topic = 'SELECT' | 'JOIN' | 'WHERE' | 'GROUP BY' | 'HAVING' | 'SUBQUERY' | 'CTE' | 'WINDOW FUNCTION';

const difficultyConfig: Record<Difficulty, { label: string; cls: string }> = {
  easy: { label: 'Dễ (Easy)', cls: 'badge-easy' },
  medium: { label: 'Trung bình (Medium)', cls: 'badge-medium' },
  hard: { label: 'Khó (Hard)', cls: 'badge-hard' },
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
    } catch {}
  };

  React.useEffect(() => {
    if (taskData?.status === 'done' && taskData?.result) {
      setResult(taskData.result);
    }
  }, [taskData]);

  const isLoading =
    generateMutation.isPending ||
    (!!taskId && taskData?.status !== 'done' && taskData?.status !== 'failed');

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-surface border border-line rounded-xl p-6 space-y-6"
    >
      <div>
        <label className="block text-sm font-semibold text-ink mb-2">
          Độ khó ({difficulties.length} đã chọn)
        </label>
        <div className="flex flex-wrap gap-2.5">
          {(Object.keys(difficultyConfig) as Difficulty[]).map((d) => {
            const selected = difficulties.includes(d);
            const cfg = difficultyConfig[d];
            return (
              <button
                key={d}
                type="button"
                onClick={() => toggleDifficulty(d)}
                className={`px-4 min-h-10 rounded-lg font-semibold text-sm ${
                  selected ? cfg.cls : 'btn-secondary opacity-70'
                }`}
              >
                {cfg.label}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <label className="block text-sm font-semibold text-ink mb-2">
          Số lượng câu hỏi: {count}
        </label>
        <input
          type="range"
          min={1}
          max={10}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
          className="w-full accent-[var(--green)] cursor-pointer"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold text-ink mb-2">
          Chủ đề SQL
        </label>
        <select
          value={selectedTopic}
          onChange={(e) => setSelectedTopic(e.target.value as Topic | '')}
          className="w-full bg-canvas border border-line rounded-lg px-3.5 min-h-10 text-sm text-ink"
        >
          <option value="">Tất cả chủ đề</option>
          {allTopics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        data-solid-btn="true"
        disabled={isLoading || difficulties.length === 0}
        className="btn-primary w-full min-h-11 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Đang sinh câu hỏi...</span>
          </>
        ) : (
          <>
            <Zap className="w-4 h-4" />
            <span>Sinh câu hỏi</span>
          </>
        )}
      </button>

      {generateMutation.isError && (
        <div className="rounded-lg badge-hard p-4 text-sm">
          {(generateMutation.error as any)?.response?.data?.detail ||
            'Dịch vụ LLM hiện chưa sẵn sàng.'}
        </div>
      )}

      {!!result && (
        <div className="rounded-lg badge-easy p-4 space-y-2">
          <div className="text-sm font-semibold">Kết quả sinh đề</div>
          <pre className="bg-surface border border-line rounded-lg p-3 overflow-auto text-xs text-ink max-h-[360px]">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </form>
  );
}
