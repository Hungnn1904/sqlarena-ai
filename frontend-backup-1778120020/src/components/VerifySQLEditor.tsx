'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface VerifySQLEditorProps {
  defaultSchema?: string;
  defaultQuery?: string;
  defaultExpected?: string;
  onVerify?: (data: { schema: string; query: string; expected: string }) => void;
}

// Simple SQL syntax highlighting
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
    const tokens: React.ReactNode[] = [];
    let remaining = line;
    let key = 0;

    // Comment
    if (remaining.trim().startsWith('--')) {
      tokens.push(
        <span key={`${lineIndex}-comment`} className="text-[#3d5a7a]">
          {remaining}
        </span>
      );
      return (
        <div key={lineIndex} className="min-h-[1.5em]">
          {tokens}
        </div>
      );
    }

    // Process token by token roughly
    const regex = new RegExp(
      `('[^']*')|("[^"]*")|(\b(?:${keywords.join('|')})\b)|(\b(?:${types.join('|')})\b)|(\b(?:${functions.join('|')})\b)|(\b\d+\b)|(--.*$)`,
      'gi'
    );

    let lastIndex = 0;
    let match;
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
      if (match[1]) className = 'text-[#00e5a0]'; // string single
      else if (match[2]) className = 'text-[#00e5a0]'; // string double
      else if (match[3]) className = 'text-[#00d4ff]'; // keyword
      else if (match[4]) className = 'text-[#a78bfa]'; // type
      else if (match[5]) className = 'text-[#ffb830]'; // function
      else if (match[6]) className = 'text-[#ffb830]'; // number
      else if (match[7]) className = 'text-[#3d5a7a]'; // comment

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

export default function VerifySQLEditor({
  defaultSchema = '',
  defaultQuery = '',
  defaultExpected = '',
  onVerify,
}: VerifySQLEditorProps) {
  const [schema, setSchema] = React.useState(defaultSchema);
  const [query, setQuery] = React.useState(defaultQuery);
  const [expected, setExpected] = React.useState(defaultExpected);
  const [result, setResult] = React.useState<{ status: 'pass' | 'fail'; message: string; details?: string } | null>(null);
  const [isVerifying, setIsVerifying] = React.useState(false);

  const handleVerify = async () => {
    setIsVerifying(true);

    // Simulate verification
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const hasError = query.toLowerCase().includes('error') || query.trim().length < 10;

    if (hasError) {
      setResult({
        status: 'fail',
        message: 'Execution failed',
        details: 'Syntax error near "SELECT" at line 1',
      });
    } else {
      setResult({
        status: 'pass',
        message: 'All checks passed',
        details: 'Output matches expected result (5 rows, 3 columns)',
      });
    }

    onVerify?.({ schema, query, expected });
    setIsVerifying(false);
  };

  const editors = [
    { label: 'Schema SQL', value: schema, setter: setSchema },
    { label: 'Answer Query', value: query, setter: setQuery },
    { label: 'Expected Output', value: expected, setter: setExpected },
  ];

  return (
    <div className="space-y-6">
      {/* Editors Grid */}
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
              <span className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-[#5a7298]">
                {editor.label}
              </span>
              <span className="text-[0.65rem] text-[#3d5a7a] font-mono">
                {editor.value.split('\n').length} lines
              </span>
            </div>
            <div className="relative">
              <textarea
                value={editor.value}
                onChange={(e) => editor.setter(e.target.value)}
                placeholder={`Enter ${editor.label.toLowerCase()}...`}
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

      {/* Verify Button */}
      <motion.button
        onClick={handleVerify}
        disabled={isVerifying || !query.trim()}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`w-full md:w-auto px-8 py-3 rounded-lg font-semibold text-sm uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2 ${
          isVerifying || !query.trim()
            ? 'bg-[#1e2d45] text-[#5a7298] cursor-not-allowed'
            : 'bg-gradient-to-r from-[#00d4ff] to-[#00e5a0] text-[#080c14] hover:shadow-[0_0_32px_rgba(0,212,255,0.25)]'
        }`}
      >
        <AnimatePresence mode="wait">
          {isVerifying ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2"
            >
              <span className="relative flex h-4 w-4">
                <span className="animate-spin absolute inline-flex h-full w-full rounded-full border-2 border-current border-t-transparent opacity-75" />
              </span>
              Verifying...
            </motion.div>
          ) : (
            <motion.span
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              Run Verification
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Result */}
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
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    result.status === 'pass' ? 'bg-[#00e5a0]/10' : 'bg-[#ff4d6d]/10'
                  }`}
                >
                  {result.status === 'pass' ? (
                    <svg className="w-5 h-5 text-[#00e5a0]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-[#ff4d6d]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                </div>
                <span
                  className={`font-semibold text-sm uppercase tracking-wider ${
                    result.status === 'pass' ? 'text-[#00e5a0]' : 'text-[#ff4d6d]'
                  }`}
                >
                  {result.message}
                </span>
              </div>
              {result.details && (
                <p className="text-[0.85rem] text-[#8ba3c7] ml-11">
                  {result.details}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
