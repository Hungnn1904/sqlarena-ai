'use client';

import React, { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Database } from 'lucide-react';
import AuthBar, { AppSection } from '../components/AuthBar';
import LearnerWorkbench from '../components/LearnerWorkbench';
import { LearnerProgressView, LeaderboardView } from '../components/ProgressAndLeaderboard';
import AdminPortal from '../components/AdminPortal';
import { UserProfile, getMe, loginUser, registerUser, extractApiError } from '../lib/api';

const SECTION_PATHS: Record<AppSection, string> = {
  workbench: '/',
  progress: '/progress',
  leaderboard: '/leaderboard',
  admin: '/admin',
};

function resolveSectionFromPath(pathname: string | null, fallback: AppSection): AppSection {
  if (!pathname) return fallback;
  if (pathname.startsWith('/admin')) return 'admin';
  if (pathname.startsWith('/progress')) return 'progress';
  if (pathname.startsWith('/leaderboard')) return 'leaderboard';
  return 'workbench';
}

export default function HomeClient({
  routeSection = 'workbench',
}: {
  routeSection?: AppSection;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const activeSection = resolveSectionFromPath(pathname, routeSection);

  const [user, setUser] = useState<UserProfile | null>(null);
  const [booting, setBooting] = useState(true);

  // Single Unified Login / Register Card State
  const [guestMode, setGuestMode] = useState<'login' | 'register'>('login');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regDisplayName, setRegDisplayName] = useState('');
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = window.localStorage.getItem('sqlarena_token');
        if (token) {
          const me = await getMe();
          setUser(me);
          if (me.role !== 'admin' && resolveSectionFromPath(window.location.pathname, routeSection) === 'admin') {
            router.replace('/');
          }
        }
      } catch {
        window.localStorage.removeItem('sqlarena_token');
        setUser(null);
      } finally {
        setBooting(false);
      }
    };
    initAuth();
  }, [routeSection, router]);

  // Enforce RBAC path guard whenever route or user changes
  useEffect(() => {
    if (!booting && user && user.role !== 'admin' && activeSection === 'admin') {
      router.replace('/');
    }
  }, [booting, user, activeSection, router]);

  const navigateSection = (section: AppSection) => {
    if (section === 'admin' && user?.role !== 'admin') {
      router.push('/');
      return;
    }
    const targetPath = SECTION_PATHS[section] || '/';
    if (pathname !== targetPath) {
      router.push(targetPath);
    }
  };

  const handleAuthSuccess = (token: string, u: UserProfile) => {
    window.localStorage.setItem('sqlarena_token', token);
    setUser(u);
    setAuthError(null);

    if (u.role === 'admin') {
      // Admin retains all learner paths (/, /progress, /leaderboard) plus /admin
      const dest =
        activeSection === 'progress' || activeSection === 'leaderboard'
          ? SECTION_PATHS[activeSection]
          : '/admin';
      router.push(dest);
    } else {
      const dest =
        activeSection === 'progress' || activeSection === 'leaderboard'
          ? SECTION_PATHS[activeSection]
          : '/';
      router.push(dest);
    }
  };

  const handleLogout = () => {
    window.localStorage.removeItem('sqlarena_token');
    setUser(null);
    setPassword('');
    if (pathname !== '/') {
      router.replace('/');
    }
  };

  const handleUnifiedLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError(null);
    try {
      const res = await loginUser(identifier.trim(), password);
      handleAuthSuccess(res.access_token, res.user);
    } catch (e: any) {
      setAuthError(extractApiError(e, 'Tài khoản hoặc mật khẩu chưa chính xác.'));
    } finally {
      setAuthBusy(false);
    }
  };

  const handleUnifiedRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError(null);
    try {
      const res = await registerUser({
        email: regEmail.trim(),
        username: regUsername.trim(),
        password,
        display_name: (regDisplayName || regUsername).trim(),
      });
      handleAuthSuccess(res.access_token, res.user);
    } catch (e: any) {
      setAuthError(
        extractApiError(e, 'Đăng ký không thành công. Tên đăng nhập hoặc email có thể đã tồn tại.')
      );
    } finally {
      setAuthBusy(false);
    }
  };

  const effectiveSection: AppSection =
    activeSection === 'admin' && user?.role !== 'admin' ? 'workbench' : activeSection;

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col relative z-10">
      <AuthBar
        user={user}
        activeSection={effectiveSection}
        onNavigateSection={navigateSection}
        onLogout={handleLogout}
        onUserUpdated={setUser}
        guestMode={guestMode}
        onSelectGuestMode={(m) => {
          setAuthError(null);
          setGuestMode(m);
        }}
      />

      <main className="flex-1 max-w-[1520px] w-full mx-auto px-4 sm:px-6 py-6">
        {booting ? (
          <div className="p-12 rounded-xl bg-surface border border-line text-center text-sm text-muted">
            Đang kết nối hệ thống PostgreSQL 17…
          </div>
        ) : !user ? (
          /* ================================================================
             SINGLE UNIFIED LOGIN / REGISTER CARD (ALL ROLES, ZERO CLUTTER)
          ================================================================ */
          <div className="max-w-md mx-auto my-12 bg-surface border border-line rounded-2xl p-6 sm:p-7 space-y-5">
            <div className="flex items-center gap-3">
              <div
                data-solid-btn="true"
                className="w-10 h-10 rounded-xl btn-primary flex items-center justify-center shrink-0"
              >
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-ink">SQLArena</h1>
                <p className="text-xs text-muted">
                  Thực hành &amp; chấm bài SQL tự động trên PostgreSQL 17
                </p>
              </div>
            </div>

            <div className="bg-soft p-1 rounded-lg grid grid-cols-2 gap-1 text-sm">
              <button
                type="button"
                onClick={() => {
                  setAuthError(null);
                  setGuestMode('login');
                }}
                className={`min-h-10 rounded-md font-medium whitespace-nowrap ${
                  guestMode === 'login'
                    ? 'bg-surface text-ink font-semibold border border-line'
                    : 'text-muted hover:text-ink'
                }`}
              >
                Đăng nhập
              </button>
              <button
                type="button"
                onClick={() => {
                  setAuthError(null);
                  setGuestMode('register');
                }}
                className={`min-h-10 rounded-md font-medium whitespace-nowrap ${
                  guestMode === 'register'
                    ? 'bg-surface text-ink font-semibold border border-line'
                    : 'text-muted hover:text-ink'
                }`}
              >
                Đăng ký
              </button>
            </div>

            {authError && (
              <div className="p-3 rounded-lg badge-hard text-sm">{authError}</div>
            )}

            {guestMode === 'login' ? (
              <form onSubmit={handleUnifiedLogin} className="space-y-3.5">
                <div>
                  <label className="block text-sm font-medium text-text2 mb-1">
                    Tên đăng nhập hoặc Email
                  </label>
                  <input
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="Nhập tên đăng nhập hoặc email…"
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text2 mb-1">
                    Mật khẩu
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Nhập mật khẩu…"
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={authBusy}
                  className="btn-primary w-full min-h-11 rounded-xl text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
                >
                  {authBusy ? 'Đang đăng nhập…' : 'Đăng nhập'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleUnifiedRegister} className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-text2 mb-1">
                      Tên đăng nhập
                    </label>
                    <input
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      placeholder="sv_ptit"
                      required
                      className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text2 mb-1">
                      Họ tên hiển thị
                    </label>
                    <input
                      value={regDisplayName}
                      onChange={(e) => setRegDisplayName(e.target.value)}
                      placeholder="Nguyễn Văn A"
                      className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text2 mb-1">
                    Địa chỉ Email
                  </label>
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="ban@stu.ptit.edu.vn"
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text2 mb-1">
                    Mật khẩu (tối thiểu 6 ký tự)
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Nhập mật khẩu…"
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={authBusy}
                  className="btn-primary w-full min-h-11 rounded-xl text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
                >
                  {authBusy ? 'Đang tạo tài khoản…' : 'Đăng ký tài khoản'}
                </button>
              </form>
            )}
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={effectiveSection}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
            >
              {effectiveSection === 'workbench' && <LearnerWorkbench />}
              {effectiveSection === 'progress' && <LearnerProgressView />}
              {effectiveSection === 'leaderboard' && <LeaderboardView />}
              {effectiveSection === 'admin' && user.role === 'admin' && (
                <AdminPortal isAdmin={true} />
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </main>
    </div>
  );
}
