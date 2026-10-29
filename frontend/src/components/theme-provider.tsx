'use client';

import * as React from 'react';

export type ThemeMode = 'light' | 'dark';

interface ThemeContextValue {
  theme: ThemeMode;
  toggleTheme: () => void;
  setTheme: (t: ThemeMode) => void;
}

const ThemeContext = React.createContext<ThemeContextValue>({
  theme: 'light',
  toggleTheme: () => {},
  setTheme: () => {},
});

export function useTheme() {
  return React.useContext(ThemeContext);
}

function applyHtmlThemeClasses(mode: ThemeMode) {
  const el = document.documentElement;
  el.classList.remove('dark', 'light', 'hybrid');
  el.classList.add(mode);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<ThemeMode>('light');

  React.useEffect(() => {
    const saved = window.localStorage.getItem('sqlarena_theme_v7') as ThemeMode | null;
    const initial: ThemeMode = saved === 'dark' ? 'dark' : 'light';
    setThemeState(initial);
    applyHtmlThemeClasses(initial);
  }, []);

  const setTheme = React.useCallback((next: ThemeMode) => {
    setThemeState(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('sqlarena_theme_v7', next);
    }
    applyHtmlThemeClasses(next);
  }, []);

  const toggleTheme = React.useCallback(() => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
