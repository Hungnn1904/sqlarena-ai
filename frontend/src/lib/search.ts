/**
 * Shared Vietnamese accent-insensitive multi-token record matcher.
 * Matches strictly against visible rendered fields passed by the caller:
 * - Numeric or >=3-char tokens match anywhere in the visible record text (e.g. '2' -> 'SQL2', 'SQL23', 'SQL24', '2026').
 * - Short 1..2-char letter tokens match word prefixes (e.g. 'de' -> 'Dễ', without matching mid-word 'or[de]rs').
 */
export function normalizeSearchText(val: unknown): string {
  if (val === null || val === undefined) return '';
  return String(val)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim();
}

export function matchesVisibleRecord(rawQuery: string, ...visibleFields: unknown[]): boolean {
  const kw = normalizeSearchText(rawQuery);
  if (!kw) return true;
  const tokens = kw.split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return true;

  const haystack = normalizeSearchText(
    visibleFields
      .map((f) => (Array.isArray(f) ? f.join(' ') : f ?? ''))
      .join(' ')
  );
  const words = haystack.split(/[^a-z0-9]+/).filter(Boolean);

  return tokens.every((tok) => {
    if (/\d/.test(tok) || tok.length >= 3) {
      return haystack.includes(tok);
    }
    return words.some((w) => w.startsWith(tok));
  });
}
