'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVerifySQL } from '@/lib/hooks';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

function highlightSQL(sql: string): React.ReactNode[] {
  if (!sql) return [];
  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON',
    'GROUP', 'BY', 'HAVING', 'ORDER', 'LIMIT', 'OFFSET', 'INSERT', 'UPDATE',
    'DELETE', 'CREATE', 'TABLE', 'DROP', 'ALTER', 'INDEX', 'VIEW', 'AS',
    'AND', 'OR', 'NOT', 'NULL', 'IS', 'IN', 'BETWEEN', 'LIKE', 'EXISTS',
    'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'DISTINCT', 'UNION', 'ALL',
    'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'WITH', 'CTE', 'RECURSIVE',
    'OVER', 'PARTITION', 'ROW_NUMBER', 'RANK', 'DENSE_RANK',
  ];
  const types = ['INT', 'VARCHAR', 'TEXT', 'DATE', 'DATETIME', 'TIMESTAMP', 'BOOLEAN', 'FLOAT', 'DOUBLE', 'DECIMAL'];
  const functions = ['COALESCE', 'IFNULL', 'NULLIF', 'CAST', 'CONVERT', 'CONCAT', 'SUBSTRING', 'TRIM', 'UPPER', 'LOWER', 'ROUND', 'DATE_FORMAT'];

  const lines = sql.split('\n');
  return lines.map((line, lineIndex) => {
    if (line.trim().startsWith('--')) {
      return (
        <div key={lineIndex} className="min-h-[1.5em]">
          <span className="text-[#3d5a7a]">{line}</span>
        </div>
      );
    }

    const regex = new RegExp(
      `('[^']*')|("[^"]*")|(\\b(?:${keywords.join('|')})\\b)|(\\b(?:${types.join('|')})\\b)|(\\b(?:${functions.join('|')})\\b)|(\\b\\d+\\b)|(--.*$)`,
      'gi'
    );

    let lastIndex = 0;
    let match;
    const tokens: React.ReactNode[] = [];
    let key = 0;
    const localRegex = new RegExp(regex.source, regex.flags);

    while ((match = localRegex.exec(line)) !== null) {
      if (match.index > lastIndex) {
        tokens.push(
          <span key={`${lineIndex}-${key++}`} className="text-[#a8c4e8]">
            {line.slice(lastIndex, match.index)}
          </span>
        );
      }

      const token = match[0];
      let className = 'text-[#a8c4e8]';
      if (match[1]) className = 'text-[#00e5a0]';
      else if (match[2]) className = 'text-[#00e5a0]';
      else if (match[3]) className = 'text-[#00d4ff]';
      else if (match[4]) className = 'text-[#a78bfa]';
      else if (match[5]) className = 'text-[#ffb830]';
      else if (match[6]) className = 'text-[#ffb830]';
      else if (match[7]) className = 'text-[#3d5a7a]';

      tokens.push(
        <span key={`${lineIndex}-${key++}`} className={className}>
          {token}
        </span>
      );
      lastIndex = localRegex.lastIndex;
    }

    if (lastIndex < line.length) {
      tokens.push(
        <span key={`${lineIndex}-${key++}`} className="text-[#a8c4e8]">
          {line.slice(lastIndex)}
        </span>
      );
    }

    return (
      <div key={lineIndex} className="min-h-[1.5em]">
        {tokens.length > 0 ? tokens : line}
      </div>
    );
  });
}

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
        {editors.map((editor, index) => (
          <motion.div
            key={editor.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
            className="bg-[#0d1320] border border-[#1e2d45] rounded-lg overflow-hidden"
          >
            <div className="px-4 py-2.5 border-b border-[#1e2d45] flex items-center justify-between">
              <span className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-[#5a7298]">{editor.label}</span>
              <span className="text-[0.65rem] text-[#3d5a7a] font-mono">{editor.value.split('\n').length} lines</span>
            </div>
            <div className="relative">
              <textarea
                value={editor.value}
                onChange={(e) => editor.setter(e.target.value)}
                placeholder={editor.placeholder}
                spellCheck={false}
                className="absolute inset-0 w-full h-full p-4 bg-transparent text-transparent caret-[#00d4ff] font-mono text-[0.82rem] leading-[1.6] resize-none focus:outline-none z-10"
                style={{ tabSize: 2 }}
              />
              <pre className="p-4 min-h-[200px] max-h-[300px] overflow-auto font-mono text-[0.82rem] leading-[1.6] pointer-events-none select-none">
                {highlightSQL(editor.value)}
              </pre>
            </div>
          </motion.div>
        ))}
      </div>

      <motion.button
        onClick={handleVerify}
        disabled={verifyMutation.isPending || !answer.trim()}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`w-full md:w-auto px-8 py-3 rounded-lg font-semibold text-sm uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2 ${
          verifyMutation.isPending || !answer.trim()
            ? 'bg-[#1e2d45] text-[#5a7298] cursor-not-allowed'
            : 'bg-gradient-to-r from-[#00d4ff] to-[#00e5a0] text-[#080c14] hover:shadow-[0_0_32px_rgba(0,212,255,0.25)]'
        }`}
      >
        <AnimatePresence mode="wait">
          {verifyMutation.isPending ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Verifying…
            </motion.div>
          ) : (
            <motion.span key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              Run Verification
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35 }}
            className="overflow-hidden"
          >
            <div
              className={`rounded-lg border p-5 ${
                result.status === 'pass'
                  ? 'bg-[rgba(0,229,160,0.06)] border-[#00e5a0]/30'
                  : 'bg-[rgba(255,77,109,0.06)] border-[#ff4d6d]/30'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    result.status === 'pass' ? 'bg-[#00e5a0]/10' : 'bg-[#ff4d6d]/10'
                  }`}
                >
                  {result.status === 'pass' ? (
                    <CheckCircle2 className="w-5 h-5 text-[#00e5a0]" />
                  ) : (
                    <XCircle className="w-5 h-5 text-[#ff4d6d]" />
                  )}
                </motion.div>
                <span
                  className={`font-semibold text-sm uppercase tracking-wider ${
                    result.status === 'pass' ? 'text-[#00e5a0]' : 'text-[#ff4d6d]'
                  }`}
                >
                  {result.status === 'pass' ? 'Verification Passed' : 'Verification Failed'}
                </span>
              </div>
              {result.message && (
                <p className="text-[0.85rem] text-[#8ba3c7] ml-11">{result.message}</p>
              )}
              {result.details && (
                <pre className="mt-3 ml-11 bg-[#080c14] border border-[#1e2d45] rounded-lg p-3 overflow-auto text-[0.75rem] leading-[1.5] font-mono text-[#a8c4e8] max-h-[200px]">
                  {result.details}
                </pre>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
