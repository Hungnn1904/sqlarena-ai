'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Header from '@/components/Header';
import Navigation from '@/components/Navigation';
import StatsBar from '@/components/StatsBar';
import SummaryBox from '@/components/SummaryBox';
import QuickActions from '@/components/QuickActions';
import PipelineTimeline from '@/components/PipelineTimeline';
import QuestionTable from '@/components/QuestionTable';
import QuestionCards from '@/components/QuestionCards';
import GenerateForm from '@/components/GenerateForm';
import VerifySQLEditor from '@/components/VerifySQLEditor';
import FlowDiagram from '@/components/FlowDiagram';
import ComparisonTable from '@/components/ComparisonTable';
import ScheduleGrid from '@/components/ScheduleGrid';
import {
  useHealth,
  useStats,
  useQuestions,
} from '@/lib/hooks';
import type { PipelineStep } from '@/components/types';

const navItems = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'generate', label: 'Generate' },
  { id: 'questions', label: 'Questions' },
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'verify', label: 'Verify' },
];

const pipelineSteps: PipelineStep[] = [
  {
    id: 1,
    title: 'Skill Taxonomy DB',
    badges: [
      { label: 'Nguồn tri thức', variant: 'db' },
      { label: 'Không LLM · $0', variant: 'rule' },
    ],
    status: 'completed',
    content: (
      <div className="space-y-4">
        <div className="bg-[rgba(0,212,255,0.04)] border border-dashed border-[rgba(0,212,255,0.25)] rounded-md p-4 text-[0.88rem] text-[#8ba3c7] leading-relaxed">
          <strong className="text-[#00d4ff]">Vai trò:</strong> "Từ điển kiến thức SQL" — định nghĩa tất cả topic, độ khó, lỗi phổ biến, pattern câu hỏi tốt.
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-[#111827] border border-[#1e2d45] rounded-md p-3.5">
            <div className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-[#5a7298] mb-1.5">Input</div>
            <div className="text-[0.85rem] text-[#8ba3c7] leading-relaxed">Syllabus PTIT, đề thi LearnSQL cũ, community tips</div>
          </div>
          <div className="bg-[#111827] border border-[#1e2d45] rounded-md p-3.5">
            <div className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-[#5a7298] mb-1.5">Output</div>
            <div className="text-[0.85rem] text-[#8ba3c7] leading-relaxed">
              <code className="text-[#ffb830] bg-[rgba(255,184,48,0.08)] px-1 py-0.5 rounded">taxonomy.json</code>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 2,
    title: 'Skill Target Selector',
    badges: [
      { label: 'Rule-based', variant: 'rule' },
      { label: 'Nâng cấp', variant: 'new' },
    ],
    status: 'completed',
    content: (
      <div className="space-y-4">
        <div className="bg-[rgba(0,212,255,0.04)] border border-dashed border-[rgba(0,212,255,0.25)] rounded-md p-4 text-[0.88rem] text-[#8ba3c7] leading-relaxed">
          <strong className="text-[#00d4ff]">Vai trò:</strong> "Lập kế hoạch tuần" — quyết định tuần này sinh bao nhiêu câu, topic nào, độ khó ra sao.
        </div>
      </div>
    ),
  },
  {
    id: 3,
    title: 'Question Planner',
    badges: [
      { label: 'LLM #1', variant: 'llm' },
      { label: 'Gemini Free', variant: 'free' },
      { label: '+ambiguity_risk', variant: 'new' },
    ],
    status: 'running',
    content: (
      <div className="space-y-4">
        <div className="bg-[rgba(0,212,255,0.04)] border border-dashed border-[rgba(0,212,255,0.25)] rounded-md p-4 text-[0.88rem] text-[#8ba3c7] leading-relaxed">
          <strong className="text-[#00d4ff]">Vai trò:</strong> Tạo "kịch bản bẫy sư phạm" trước khi viết đề. Blueprint là checkpoint: nếu sai thì reject trước khi tốn call Generator.
        </div>
      </div>
    ),
  },
  {
    id: 4,
    title: 'Question Generator',
    badges: [
      { label: 'LLM #2', variant: 'llm' },
      { label: 'Gemini Free', variant: 'free' },
      { label: '+Domain Rotation', variant: 'new' },
    ],
    status: 'pending',
    content: (
      <div className="space-y-4">
        <div className="bg-[rgba(0,212,255,0.04)] border border-dashed border-[rgba(0,212,255,0.25)] rounded-md p-4 text-[0.88rem] text-[#8ba3c7] leading-relaxed">
          <strong className="text-[#00d4ff]">Vai trò:</strong> AI chính thức "chắp bút" — bám sát blueprint để viết đề hoàn chỉnh bằng tiếng Việt.
        </div>
      </div>
    ),
  },
  {
    id: 5,
    title: 'Clarity Check + Ground Truth',
    badges: [
      { label: 'LLM #3 nhỏ', variant: 'llm' },
      { label: 'Rule-based', variant: 'rule' },
      { label: 'Thay Auto Solver', variant: 'new' },
    ],
    status: 'pending',
    content: (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-[#111827] border border-[#1e2d45] rounded-md p-3.5">
            <div className="font-mono text-[0.68rem] uppercase tracking-[0.1em] text-[#00d4ff] mb-2">Lớp A — Linguistic Clarity</div>
            <p className="text-[0.82rem] text-[#8ba3c7]">LLM đọc câu hỏi, liệt kê các cách hiểu khác nhau mà sinh viên có thể có.</p>
          </div>
          <div className="bg-[#111827] border border-[#1e2d45] rounded-md p-3.5">
            <div className="font-mono text-[0.68rem] uppercase tracking-[0.1em] text-[#00e5a0] mb-2">Lớp B — Ground Truth Assertion</div>
            <p className="text-[0.82rem] text-[#8ba3c7]">Rule-based: Negation test + NULL test. Không dùng LLM.</p>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 6,
    title: 'Execution Engine Verify',
    badges: [
      { label: 'Deterministic DB', variant: 'db' },
      { label: 'Không LLM · $0', variant: 'rule' },
    ],
    status: 'pending',
    content: (
      <div className="space-y-4">
        <div className="bg-[rgba(0,212,255,0.04)] border border-dashed border-[rgba(0,212,255,0.25)] rounded-md p-4 text-[0.88rem] text-[#8ba3c7] leading-relaxed">
          <strong className="text-[#00d4ff]">Vai trò:</strong> "Chốt chặn cơ học" — chạy answer_query thật trên MySQL sandbox. Kết quả binary: pass hoặc fail.
        </div>
      </div>
    ),
  },
  {
    id: 7,
    title: 'Output & Metadata + Retry Policy',
    badges: [
      { label: 'Storage', variant: 'db' },
      { label: '+Retry Escalation', variant: 'new' },
    ],
    status: 'pending',
    content: (
      <div className="space-y-4">
        <div className="bg-[rgba(255,77,109,0.04)] border border-[rgba(255,77,109,0.2)] rounded-md p-4 text-[0.83rem] text-[#fda4af]">
          <strong className="text-[#ff4d6d]">Retry Escalation 3 cấp:</strong> Attempt 1: cùng blueprint → Attempt 2: đơn giản hóa → Attempt 3: archive fallback.
        </div>
      </div>
    ),
  },
];

export default function Home() {
  const [activeTab, setActiveTab] = React.useState('dashboard');
  const { data: health } = useHealth();
  const { data: statsData } = useStats();
  const { data: questionsData } = useQuestions({ limit: 100 });

  React.useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [activeTab]);

  const stats = React.useMemo(() => {
    const base = [
      { label: 'total questions', value: 0, color: 'cyan' as const },
      { label: 'valid rate', value: '—', color: 'green' as const },
      { label: 'pipeline status', value: 'Offline', color: 'rose' as const },
      { label: 'approved', value: 0, color: 'green' as const },
      { label: 'pending', value: 0, color: 'amber' as const },
    ];
    if (!statsData) {
      base[2].value = health?.status === 'ok' ? 'Online' : 'Offline';
      base[2].color = health?.status === 'ok' ? 'green' : 'rose';
      return base;
    }
    base[0].value = statsData.total || 0;
    base[1].value = `${Math.round((statsData.valid_rate || 0) * 100)}%`;
    base[2].value = health?.status === 'ok' ? 'Online' : 'Offline';
    base[2].color = health?.status === 'ok' ? 'green' : 'rose';
    base[3].value = statsData.by_status?.approved || 0;
    base[4].value = statsData.by_status?.pending_review || 0;
    return base;
  }, [statsData, health]);

  const summaryStats = React.useMemo(
    () => [
      {
        label: 'Pipeline Status',
        value: health?.status === 'ok' ? 'Online' : 'Offline',
        description: health?.status === 'ok' ? 'All services healthy' : 'Backend unreachable',
        color: health?.status === 'ok' ? ('green' as const) : ('rose' as const),
      },
      {
        label: 'Total Questions',
        value: statsData?.total ?? 0,
        description: 'In database',
        color: 'cyan' as const,
      },
      {
        label: 'Valid Rate',
        value: `${Math.round((statsData?.valid_rate || 0) * 100)}%`,
        description: 'Validated questions',
        color: 'purple' as const,
      },
      {
        label: 'Weekly Target',
        value: 50,
        description: 'Questions planned',
        color: 'amber' as const,
      },
    ],
    [health, statsData]
  );

  const questions = React.useMemo(() => {
    if (!questionsData?.questions) return [];
    return questionsData.questions.map((q) => ({
      id: q.id,
      topic: (q.topic || 'SQL') as any,
      difficulty: (q.difficulty || 'easy') as any,
      domain: q.domain || 'sql',
      status: (q.status || 'pending_review') as any,
      createdAt: q.created_at || new Date().toISOString(),
      questionText: q.question_text || q.id,
      validationStatus: q.validation_status,
    }));
  }, [questionsData]);

  const handleQuickAction = (action: 'generate' | 'verify' | 'pipeline' | 'export') => {
    if (action === 'export') {
      if (!questions.length) return;
      const headers = ['ID', 'Topic', 'Difficulty', 'Domain', 'Status', 'Created', 'Text'];
      const rows = questions.map((q) => [
        q.id,
        q.topic,
        q.difficulty,
        q.domain,
        q.status,
        q.createdAt,
        `"${q.questionText.replace(/"/g, '""')}"`,
      ]);
      const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'sqlarena_questions.csv';
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    setActiveTab(action);
  };

  return (
    <div className="min-h-screen bg-[#080c14] text-[#e2eaf6]">
      <div className="relative z-10">
        <Navigation items={navItems} activeId={activeTab} onChange={setActiveTab} />

        <div className="max-w-[1060px] mx-auto px-6 pb-20">
          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' && (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.4 }}
                className="space-y-12"
              >
                <Header
                  title={
                    <>
                      SQL Question Generator
                      <br />
                      Pipeline
                    </>
                  }
                />
                <StatsBar stats={stats} />
                <SummaryBox stats={summaryStats} />
                <QuickActions onAction={handleQuickAction} />

                <section>
                  <SectionLabel>Pipeline · 7 bước</SectionLabel>
                  <PipelineTimeline steps={pipelineSteps} defaultOpen={3} />
                </section>

                <section>
                  <SectionLabel>Recent Questions</SectionLabel>
                  <QuestionTable questions={questions.slice(0, 10)} />
                </section>
              </motion.div>
            )}

            {activeTab === 'generate' && (
              <motion.div
                key="generate"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.4 }}
                className="space-y-8 pt-8"
              >
                <SectionLabel>Generate Questions</SectionLabel>
                <GenerateForm />
              </motion.div>
            )}

            {activeTab === 'questions' && (
              <motion.div
                key="questions"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.4 }}
                className="space-y-8 pt-8"
              >
                <SectionLabel>All Questions</SectionLabel>
                <QuestionCards />
              </motion.div>
            )}

            {activeTab === 'pipeline' && (
              <motion.div
                key="pipeline"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.4 }}
                className="space-y-12 pt-8"
              >
                <section>
                  <SectionLabel>Flow một câu hỏi</SectionLabel>
                  <FlowDiagram />
                </section>

                <section>
                  <SectionLabel>Pipeline · 7 bước</SectionLabel>
                  <PipelineTimeline steps={pipelineSteps} defaultOpen={1} />
                </section>

                <section>
                  <SectionLabel>So sánh Pipeline gốc vs Pipeline tối ưu</SectionLabel>
                  <ComparisonTable />
                </section>

                <section>
                  <SectionLabel>Lịch chạy batch thực tế</SectionLabel>
                  <ScheduleGrid />
                </section>
              </motion.div>
            )}

            {activeTab === 'verify' && (
              <motion.div
                key="verify"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.4 }}
                className="space-y-8 pt-8"
              >
                <SectionLabel>Verify SQL</SectionLabel>
                <VerifySQLEditor />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <footer className="border-t border-[#1e2d45] py-8 text-center font-mono text-[0.72rem] text-[#5a7298] tracking-[0.08em]">
          <div className="max-w-[1060px] mx-auto px-6">
            SQLArena · AI Question Generator Pipeline v2.0 · Tối ưu cho đồ án · Gemini 2.0 Flash Free Tier
          </div>
        </footer>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="font-mono text-[0.7rem] tracking-[0.2em] uppercase text-[#00d4ff] mb-8 flex items-center gap-3"
    >
      {children}
      <span className="flex-1 h-px bg-[#243550]" />
    </motion.div>
  );
}
