'use client';

import React from 'react';
import { useVerifySQL } from '@/lib/hooks';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

export default function VerifySQLEditor() {
  const [schema, setSchema] = React.useState('');
  const [seed, setSeed] = React.useState('');
  const [answer, setAnswer] = React.useState('');

  const verifyMutation = useVerifySQL();
  const result = verifyMutation.data || null;

  const handleVerify = async () => {
    await verifyMutation.mutateAsync({
      ddl_sql: schema,
      seed_sql: seed,
      answer_sql: answer,
    });
  };

  const editors = [
    { label: 'DDL SQL', value: schema, setter: setSchema, placeholder: 'CREATE TABLE employees (...)' },
    { label: 'Seed SQL', value: seed, setter: setSeed, placeholder: 'INSERT INTO employees VALUES (...)' },
    { label: 'Answer SQL', value: answer, setter: setAnswer, placeholder: 'SELECT * FROM employees WHERE ...' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {editors.map((editor) => (
          <div
            key={editor.label}
            className="bg-surface border border-line rounded-xl overflow-hidden"
          >
            <div className="px-4 py-2.5 bg-soft border-b border-line flex items-center justify-between">
              <span className="text-xs font-semibold text-ink">{editor.label}</span>
              <span className="text-xs text-muted tabular-nums">
                {editor.value.split('\n').length} dòng
              </span>
            </div>
            <textarea
              value={editor.value}
              onChange={(e) => editor.setter(e.target.value)}
              placeholder={editor.placeholder}
              spellCheck={false}
              rows={8}
              className="w-full p-4 bg-canvas text-ink font-mono text-xs leading-relaxed resize-y"
            />
          </div>
        ))}
      </div>

      <button
        type="button"
        data-solid-btn="true"
        onClick={handleVerify}
        disabled={verifyMutation.isPending || !answer.trim()}
        className="btn-primary w-full md:w-auto px-6 min-h-11 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {verifyMutation.isPending ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Đang kiểm tra SQL...</span>
          </>
        ) : (
          <span>Chạy kiểm tra SQL</span>
        )}
      </button>

      {result && (
        <div
          className={`rounded-xl p-5 space-y-2 ${
            result.status === 'pass' ? 'badge-easy' : 'badge-hard'
          }`}
        >
          <div className="flex items-center gap-2 font-semibold text-sm">
            {result.status === 'pass' ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <XCircle className="w-4 h-4" />
            )}
            <span>
              {result.status === 'pass' ? 'Kiểm tra thành công' : 'Kiểm tra chưa đạt'}
            </span>
          </div>
          {result.message && <p className="text-sm">{result.message}</p>}
          {result.details && (
            <pre className="mt-2 bg-surface border border-line rounded-lg p-3 overflow-auto text-xs text-ink max-h-[200px]">
              {result.details}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
