'use client';

import * as React from 'react';

export type ThemeMode = 'hybrid' | 'light' | 'dark';

interface ThemeContextValue {
  theme: ThemeMode;
  toggleTheme: () => void;
  setTheme: (t: ThemeMode) => void;
}

const ThemeContext = React.createContext<ThemeContextValue>({
  theme: 'hybrid',
  toggleTheme: () => {},
  setTheme: () => {},
});

export function useTheme() {
  return React.useContext(ThemeContext);
}

function applyHtmlThemeClasses(mode: ThemeMode) {
  const el = document.documentElement;
  el.classList.remove('dark', 'light', 'hybrid');
  if (mode === 'dark') {
    el.classList.add('dark');
  } else if (mode === 'light') {
    el.classList.add('light');
  } else {
    el.classList.add('light', 'hybrid');
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<ThemeMode>('hybrid');

  React.useEffect(() => {
    const saved = window.localStorage.getItem('sqlarena_theme_v6') as ThemeMode | null;
    const initial: ThemeMode =
      saved === 'light' || saved === 'dark' || saved === 'hybrid' ? saved : 'hybrid';
    setThemeState(initial);
    applyHtmlThemeClasses(initial);
  }, []);

  const setTheme = React.useCallback((next: ThemeMode) => {
    setThemeState(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('sqlarena_theme_v6', next);
    }
    applyHtmlThemeClasses(next);
  }, []);

  const toggleTheme = React.useCallback(() => {
    const order: ThemeMode[] = ['hybrid', 'light', 'dark'];
    const next = order[(order.indexOf(theme) + 1) % order.length];
    setTheme(next);
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
