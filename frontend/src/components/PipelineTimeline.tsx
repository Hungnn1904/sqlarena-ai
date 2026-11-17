'use client';

import React from 'react';
import { ChevronDown } from 'lucide-react';
import type { PipelineStep, BadgeVariant } from './types';

interface PipelineTimelineProps {
  steps: PipelineStep[];
  defaultOpen?: number;
}

const badgeStyles: Record<BadgeVariant, string> = {
  llm: 'badge-medium',
  rule: 'badge-easy',
  db: 'badge-info',
  new: 'badge-hard',
  free: 'badge-easy',
};

export default function PipelineTimeline({ steps, defaultOpen = 1 }: PipelineTimelineProps) {
  const [openId, setOpenId] = React.useState<number | null>(defaultOpen);

  const toggle = (id: number) => {
    setOpenId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="space-y-4">
      {steps.map((step) => {
        const isOpen = openId === step.id;
        return (
          <div
            key={step.id}
            className="bg-surface border border-line rounded-xl overflow-hidden"
          >
            <button
              type="button"
              onClick={() => toggle(step.id)}
              className="w-full px-5 py-4 flex items-center justify-between gap-3 flex-wrap hover:bg-soft transition-colors text-left"
            >
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs text-brand font-bold px-2.5 py-1 rounded-md bg-soft border border-line">
                  Bước {step.id}
                </span>
                <span className="text-base font-bold text-ink">{step.title}</span>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {step.badges.map((badge, i) => (
                  <span
                    key={i}
                    className={`text-xs px-2.5 py-0.5 rounded-md font-semibold ${
                      badgeStyles[badge.variant]
                    }`}
                  >
                    {badge.label}
                  </span>
                ))}
                <ChevronDown
                  className={`w-4 h-4 text-muted transition-transform ${
                    isOpen ? 'rotate-180' : ''
                  }`}
                />
              </div>
            </button>

            {isOpen && <div className="px-6 pb-6 pt-2 border-t border-line">{step.content}</div>}
          </div>
        );
      })}
    </div>
  );
}

export function ExplainBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-canvas border border-dashed border-line rounded-lg p-4 text-sm text-text2 leading-relaxed">
      {children}
    </div>
  );
}

export function NewTag({ children }: { children: React.ReactNode }) {
  return (
    <div className="badge-hard rounded-lg p-4 text-sm leading-relaxed">
      {children}
    </div>
  );
}

export function IOGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">{children}</div>;
}

export function IOBox({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-canvas border border-line rounded-lg p-3.5">
      <div className="text-xs font-semibold text-muted mb-1.5">{label}</div>
      <div className="text-sm text-text2 leading-relaxed">{children}</div>
    </div>
  );
}

export function SubTitle({ children }: { children: React.ReactNode }) {
  return <h4 className="text-sm font-bold text-brand mt-5 mb-2">{children}</h4>;
}

export function BodyText({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-text2 mb-2.5 leading-relaxed">{children}</p>;
}

export function BodyList({ children }: { children: React.ReactNode }) {
  return <ul className="list-disc pl-5 mb-3">{children}</ul>;
}

export function BodyListItem({ children }: { children: React.ReactNode }) {
  return <li className="text-sm text-text2 mb-1 leading-relaxed">{children}</li>;
}

export function CodeBlock({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <pre
      className={`bg-canvas border border-line rounded-lg p-4 overflow-x-auto text-xs leading-relaxed text-ink my-2.5 ${className}`}
    >
      <code>{children}</code>
    </pre>
  );
}

export function TwoLayer({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-3.5">{children}</div>;
}

export function LayerBox({
  title,
  titleColor = 'cyan',
  children,
}: {
  title: string;
  titleColor?: 'cyan' | 'green';
  children: React.ReactNode;
}) {
  const colorClass = titleColor === 'green' ? 'text-brand' : 'text-info';
  return (
    <div className="bg-canvas border border-line rounded-lg p-4">
      <div className={`text-xs font-bold mb-2 ${colorClass}`}>{title}</div>
      {children}
    </div>
  );
}

export function RetryTable({ children }: { children: React.ReactNode }) {
  return <div className="my-3.5">{children}</div>;
}

export function RetryRow({
  attempt,
  children,
}: {
  attempt: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[100px_1fr] gap-3 py-2.5 border-b border-line last:border-b-0 items-start">
      <div className="text-xs text-copper font-semibold">{attempt}</div>
      <div className="text-sm text-text2">{children}</div>
    </div>
  );
}
