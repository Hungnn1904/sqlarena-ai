'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Database } from 'lucide-react';
import AuthBar from '../components/AuthBar';
import LearnerWorkbench from '../components/LearnerWorkbench';
import { LearnerProgressView, LeaderboardView } from '../components/ProgressAndLeaderboard';
import AdminPortal from '../components/AdminPortal';
import { UserProfile, getMe, loginUser, registerUser, extractApiError } from '../lib/api';

const LEARNER_TABS = new Set(['workbench', 'progress', 'leaderboard']);
const ADMIN_ALLOWED_TABS = new Set(['workbench', 'progress', 'leaderboard', 'admin']);

function detectWebSurface(forceSurface?: 'learner' | 'admin'): 'learner' | 'admin' {
  if (forceSurface) return forceSurface;
  if (typeof window !== 'undefined') {
    const port = window.location.port;
    const pathname = window.location.pathname || '';
    if (port === '4000' || port === '4005' || pathname.startsWith('/admin')) {
      return 'admin';
    }
  }
  return 'learner';
}

export default function HomeClient({
  forceSurface,
}: {
  forceSurface?: 'learner' | 'admin';
}) {
  const [surface, setSurface] = useState<'learner' | 'admin'>(forceSurface || 'learner');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTabState] = useState<string>('workbench');
  const [booting, setBooting] = useState(true);

  // Clean Guest Auth Card State (Login / Register only — zero marketing clutter)
  const [guestMode, setGuestMode] = useState<'login' | 'register'>('login');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regDisplayName, setRegDisplayName] = useState('');
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Dedicated Admin Surface Login State
  const [adminIdentifier, setAdminIdentifier] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminLoginBusy, setAdminLoginBusy] = useState(false);
  const [adminLoginError, setAdminLoginError] = useState<string | null>(null);

  const setActiveTab = (nextTab: string, roleOverride?: 'learner' | 'admin') => {
    const effectiveRole = roleOverride ?? user?.role;
    const allowed = effectiveRole === 'admin' ? ADMIN_ALLOWED_TABS : LEARNER_TABS;
    const safeTab = allowed.has(nextTab) ? nextTab : 'workbench';
    setActiveTabState(safeTab);
    if (typeof window !== 'undefined' && surface === 'learner') {
      window.sessionStorage.setItem('sqlarena_active_tab', safeTab);
      const url = new URL(window.location.href);
      url.searchParams.set('tab', safeTab);
      window.history.replaceState(null, '', `${url.pathname}${url.search}`);
    }
  };

  useEffect(() => {
    const detected = detectWebSurface(forceSurface);
    setSurface(detected);

    const initAuth = async () => {
      try {
        const token = window.localStorage.getItem('sqlarena_token');
        if (token) {
          const me = await getMe();
          setUser(me);
          if (typeof window !== 'undefined' && detected === 'learner') {
            const params = new URLSearchParams(window.location.search);
            const fromUrl = params.get('tab');
            const fromSession = window.sessionStorage.getItem('sqlarena_active_tab');
            const allowed = me.role === 'admin' ? ADMIN_ALLOWED_TABS : LEARNER_TABS;
            const defaultTab = me.role === 'admin' ? 'admin' : 'workbench';
            const candidate =
              fromUrl && allowed.has(fromUrl)
                ? fromUrl
                : fromSession && allowed.has(fromSession)
                ? fromSession
                : defaultTab;
            setActiveTabState(candidate);
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
  }, [forceSurface]);

  const handleAuthSuccess = (token: string, u: UserProfile, targetTab?: string) => {
    window.localStorage.setItem('sqlarena_token', token);
    setUser(u);
    setAuthError(null);
    setAdminLoginError(null);
    if (surface === 'learner') {
      const next = targetTab || (u.role === 'admin' ? 'admin' : 'workbench');
      setActiveTab(next, u.role);
    }
  };

  const handleLogout = () => {
    window.localStorage.removeItem('sqlarena_token');
    setUser(null);
    setPassword('');
    setAdminPassword('');
    if (surface === 'learner') {
      setActiveTab('workbench', 'learner');
    }
  };

  const handleGuestLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthBusy(true);
    setAuthError(null);
    try {
      const res = await loginUser(identifier.trim(), password);
      handleAuthSuccess(
        res.access_token,
        res.user,
        res.user.role === 'admin' ? 'admin' : 'workbench'
      );
    } catch (e: any) {
      setAuthError(extractApiError(e, 'Tài khoản hoặc mật khẩu chưa chính xác.'));
    } finally {
      setAuthBusy(false);
    }
  };

  const handleGuestRegister = async (e: React.FormEvent) => {
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
      handleAuthSuccess(res.access_token, res.user, 'workbench');
    } catch (e: any) {
      setAuthError(
        extractApiError(e, 'Đăng ký không thành công. Tên đăng nhập hoặc email có thể đã tồn tại.')
      );
    } finally {
      setAuthBusy(false);
    }
  };

  const handleAdminFormLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdminLoginBusy(true);
    setAdminLoginError(null);
    try {
      const res = await loginUser(adminIdentifier.trim(), adminPassword);
      if (res.user.role !== 'admin') {
        setAdminLoginError(
          'Tài khoản này không có quyền Quản trị viên. Vui lòng đăng nhập bằng tài khoản Admin.'
        );
        return;
      }
      handleAuthSuccess(res.access_token, res.user, 'admin');
    } catch (e: any) {
      setAdminLoginError(extractApiError(e, 'Thông tin đăng nhập Quản trị chưa chính xác.'));
    } finally {
      setAdminLoginBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col relative z-10">
      <AuthBar
        surface={surface}
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onAuthSuccess={handleAuthSuccess}
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
        ) : surface === 'admin' ? (
          /* ================================================================
             DEDICATED ADMIN WEB (:4000 / /admin)
          ================================================================ */
          !user || user.role !== 'admin' ? (
            <div className="max-w-md mx-auto my-12 bg-surface border border-line rounded-2xl p-6 sm:p-7 space-y-5">
              <div className="flex items-center gap-3">
                <div
                  data-solid-btn="true"
                  className="w-10 h-10 rounded-xl btn-primary flex items-center justify-center shrink-0"
                >
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-ink">Đăng nhập Quản trị</h1>
                  <p className="text-xs text-muted">
                    Cổng Quản trị hệ thống &amp; Ngân hàng đề SQL
                  </p>
                </div>
              </div>

              {user && user.role !== 'admin' && (
                <div className="p-3 rounded-lg badge-medium text-xs leading-relaxed">
                  Phiên hiện tại (<strong>@{user.username}</strong>) là tài khoản Học viên. Vui lòng đăng nhập tài khoản Quản trị viên bên dưới.
                </div>
              )}

              {adminLoginError && (
                <div className="p-3 rounded-lg badge-hard text-sm">{adminLoginError}</div>
              )}

              <form onSubmit={handleAdminFormLogin} className="space-y-3.5">
                <div>
                  <label className="block text-sm font-medium text-text2 mb-1">
                    Tài khoản Quản trị
                  </label>
                  <input
                    value={adminIdentifier}
                    onChange={(e) => setAdminIdentifier(e.target.value)}
                    placeholder="Nhập tài khoản hoặc email Admin…"
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
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    placeholder="Nhập mật khẩu…"
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={adminLoginBusy}
                  className="btn-primary w-full min-h-11 rounded-xl text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
                >
                  {adminLoginBusy ? 'Đang xác thực…' : 'Đăng nhập Quản trị'}
                </button>
              </form>
            </div>
          ) : (
            <AdminPortal isAdmin={true} />
          )
        ) : !user ? (
          /* ================================================================
             UNAUTHENTICATED VIEW — MINIMAL TITLE + LOGIN / REGISTER CARD ONLY
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
              <form onSubmit={handleGuestLogin} className="space-y-3.5">
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
              <form onSubmit={handleGuestRegister} className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-text2 mb-1">
                      Tên đăng nhập
                    </label>
                    <input
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      placeholder="hocvien_ptit"
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
              key={activeTab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
            >
              {activeTab === 'workbench' && <LearnerWorkbench />}
              {activeTab === 'progress' && <LearnerProgressView />}
              {activeTab === 'leaderboard' && <LeaderboardView />}
              {activeTab === 'admin' && user.role === 'admin' && <AdminPortal isAdmin={true} />}
            </motion.div>
          </AnimatePresence>
        )}
      </main>
    </div>
  );
}
