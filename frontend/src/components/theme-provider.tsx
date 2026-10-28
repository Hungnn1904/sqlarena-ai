'use client';

import * as React from 'react';

type ThemeMode = 'dark' | 'light';

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

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<ThemeMode>('light');

  React.useEffect(() => {
    const saved = window.localStorage.getItem('sqlarena_theme_v2') as ThemeMode | null;
    const initial: ThemeMode = saved === 'dark' ? 'dark' : 'light';
    setThemeState(initial);
    document.documentElement.classList.remove('dark', 'light');
    document.documentElement.classList.add(initial);
  }, []);

  const setTheme = React.useCallback((next: ThemeMode) => {
    setThemeState(next);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('sqlarena_theme_v2', next);
    }
    document.documentElement.classList.remove('dark', 'light');
    document.documentElement.classList.add(next);
  }, []);

  const toggleTheme = React.useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  }, [theme, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
