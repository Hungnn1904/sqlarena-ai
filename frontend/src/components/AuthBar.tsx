'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Database,
  ShieldCheck,
  Sun,
  Moon,
  LogOut,
  X,
} from 'lucide-react';
import { useTheme } from './theme-provider';
import {
  UserProfile,
  loginUser,
  registerUser,
  updateProfile,
  changePassword,
  extractApiError,
} from '../lib/api';

interface AuthBarProps {
  surface: 'learner' | 'admin';
  user: UserProfile | null;
  activeTab: string;
  setActiveTab: (t: string) => void;
  onAuthSuccess: (token: string, user: UserProfile, targetTab?: string) => void;
  onLogout: () => void;
  onUserUpdated: (user: UserProfile) => void;
  authModalTrigger?: number;
  initialAuthMode?: 'login' | 'register';
}

export default function AuthBar({
  surface,
  user,
  activeTab,
  setActiveTab,
  onAuthSuccess,
  onLogout,
  onUserUpdated,
  authModalTrigger,
  initialAuthMode = 'login',
}: AuthBarProps) {
  const { theme, toggleTheme } = useTheme();
  const [modal, setModal] = useState<'none' | 'login' | 'register' | 'profile'>('none');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regDisplayName, setRegDisplayName] = useState('');
  const [profName, setProfName] = useState('');
  const [profBio, setProfBio] = useState('');
  const [curPwd, setCurPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');

  useEffect(() => {
    if (surface === 'learner' && authModalTrigger && authModalTrigger > 0) {
      setErr(null);
      setMsg(null);
      setModal(initialAuthMode);
    }
  }, [authModalTrigger, initialAuthMode, surface]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      const res = await loginUser(identifier, password);
      onAuthSuccess(res.access_token, res.user, 'workbench');
      setModal('none');
    } catch (e: any) {
      setErr(extractApiError(e, 'Thông tin đăng nhập chưa chính xác. Vui lòng kiểm tra lại.'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      const res = await registerUser({
        email: regEmail,
        username: regUsername,
        password,
        display_name: regDisplayName || regUsername,
      });
      onAuthSuccess(res.access_token, res.user, 'workbench');
      setModal('none');
    } catch (e: any) {
      setErr(extractApiError(e, 'Đăng ký không thành công. Tên đăng nhập hoặc email có thể đã tồn tại.'));
    } finally {
      setLoading(false);
    }
  };

  const openProfile = () => {
    if (!user) return;
    setProfName(user.display_name || user.username);
    setProfBio(user.bio || '');
    setCurPwd('');
    setNewPwd('');
    setErr(null);
    setMsg(null);
    setModal('profile');
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    setMsg(null);
    try {
      const updated = await updateProfile({ display_name: profName, bio: profBio });
      onUserUpdated(updated);
      if (curPwd && newPwd) {
        await changePassword(curPwd, newPwd);
        setCurPwd('');
        setNewPwd('');
      }
      setMsg('Đã lưu thông tin hồ sơ cá nhân.');
    } catch (e: any) {
      setErr(extractApiError(e, 'Cập nhật hồ sơ không thành công'));
    } finally {
      setLoading(false);
    }
  };

  const learnerTabs =
    surface === 'learner' && user
      ? [
          { id: 'workbench', label: 'Làm bài' },
          { id: 'progress', label: 'Tiến độ' },
          { id: 'leaderboard', label: 'Xếp hạng' },
        ]
      : [];

  const isAdminSession = surface === 'admin' && user?.role === 'admin';

  return (
    <>
      <header className="sticky top-0 z-40 bg-surface border-b border-line">
        <div className="max-w-[1520px] mx-auto px-4 sm:px-6 min-h-16 py-2 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-5">
            {surface === 'admin' ? (
              <div className="flex items-center gap-2.5 min-h-10">
                <div
                  data-solid-btn="true"
                  className="w-9 h-9 rounded-lg btn-primary flex items-center justify-center shrink-0"
                >
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div className="leading-tight whitespace-nowrap">
                  <div className="font-bold text-ink text-base tracking-tight">
                    SQLArena · Quản trị
                  </div>
                  <div className="text-xs text-muted">
                    Quản trị hệ thống &amp; Ngân hàng đề
                  </div>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => user && setActiveTab('workbench')}
                className="flex items-center gap-2.5 text-left min-h-10 whitespace-nowrap"
              >
                <div
                  data-solid-btn="true"
                  className="w-9 h-9 rounded-lg btn-primary flex items-center justify-center shrink-0"
                >
                  <Database className="w-4 h-4" />
                </div>
                <div className="leading-tight">
                  <div className="font-bold text-ink text-base tracking-tight">
                    SQLArena
                  </div>
                  <div className="text-xs text-muted">
                    Thực hành PostgreSQL 17
                  </div>
                </div>
              </button>
            )}

            {learnerTabs.length > 0 && (
              <nav
                aria-label="Điều hướng học viên"
                className="flex items-center gap-1 overflow-x-auto scrollbar-hide"
              >
                {learnerTabs.map((t) => {
                  const active = activeTab === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setActiveTab(t.id)}
                      data-solid-btn={active ? 'true' : undefined}
                      className={`relative flex items-center px-3.5 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap ${
                        active
                          ? 'text-on-brand'
                          : 'text-text2 hover:text-ink hover:bg-soft'
                      }`}
                    >
                      {active && (
                        <motion.span
                          layoutId="activeLearnerTab"
                          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                          className="absolute inset-0 rounded-lg bg-brand -z-10"
                        />
                      )}
                      <span>{t.label}</span>
                    </button>
                  );
                })}
              </nav>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Theme Toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              className="btn-secondary flex items-center gap-2 px-3 min-h-10 rounded-lg text-sm font-medium whitespace-nowrap"
              title="Đổi giao diện Sáng hoặc Tối"
              aria-label="Đổi giao diện Sáng hoặc Tối"
            >
              {theme === 'light' ? (
                <>
                  <Sun className="w-4 h-4 text-copper" />
                  <span className="hidden md:inline">Sáng</span>
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4 text-brand" />
                  <span className="hidden md:inline">Tối</span>
                </>
              )}
            </button>

            {surface === 'admin' ? (
              isAdminSession && user ? (
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={openProfile}
                    className="btn-secondary flex items-center gap-2 px-3 min-h-10 rounded-lg text-left whitespace-nowrap"
                  >
                    <div
                      data-solid-btn="true"
                      className="w-7 h-7 rounded-full btn-primary flex items-center justify-center text-xs font-bold"
                    >
                      {(user.display_name || user.username).slice(0, 2).toUpperCase()}
                    </div>
                    <div className="hidden sm:block leading-tight">
                      <div className="text-sm font-semibold text-ink">
                        {user.display_name || user.username}
                      </div>
                      <div className="text-xs text-muted">Quản trị viên</div>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={onLogout}
                    title="Đăng xuất"
                    aria-label="Đăng xuất"
                    className="btn-secondary flex items-center gap-1.5 px-3 min-h-10 rounded-lg text-sm font-medium hover:text-danger whitespace-nowrap"
                  >
                    <LogOut className="w-4 h-4" />
                    <span className="hidden sm:inline">Đăng xuất</span>
                  </button>
                </div>
              ) : null
            ) : user ? (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={openProfile}
                  className="btn-secondary flex items-center gap-2 px-3 min-h-10 rounded-lg text-left whitespace-nowrap"
                >
                  <div
                    data-solid-btn="true"
                    className="w-7 h-7 rounded-full btn-primary flex items-center justify-center text-xs font-bold"
                  >
                    {(user.display_name || user.username).slice(0, 2).toUpperCase()}
                  </div>
                  <div className="hidden sm:block leading-tight">
                    <div className="text-sm font-semibold text-ink">
                      {user.display_name || user.username}
                    </div>
                    <div className="text-xs text-muted">Học viên</div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={onLogout}
                  title="Đăng xuất"
                  aria-label="Đăng xuất"
                  className="btn-secondary flex items-center gap-1.5 px-3 min-h-10 rounded-lg text-sm font-medium hover:text-danger whitespace-nowrap"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden xl:inline">Đăng xuất</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => {
                    setErr(null);
                    setModal('register');
                  }}
                  className="btn-secondary px-3.5 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap"
                >
                  Đăng ký
                </button>
                <button
                  type="button"
                  data-solid-btn="true"
                  onClick={() => {
                    setErr(null);
                    setModal('login');
                  }}
                  className="btn-primary px-4 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap"
                >
                  Đăng nhập
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Learner Login / Register Modal */}
      {surface === 'learner' && (modal === 'login' || modal === 'register') && (
        <div className="fixed inset-0 z-50 bg-overlay flex items-center justify-center p-4">
          <div className="bg-surface text-ink border border-line rounded-2xl max-w-md w-full p-6 relative">
            <button
              type="button"
              onClick={() => setModal('none')}
              className="btn-secondary absolute top-4 right-4 px-2.5 min-h-9 rounded-lg text-xs font-medium flex items-center gap-1 whitespace-nowrap"
            >
              <X className="w-3.5 h-3.5" />
              <span>Đóng</span>
            </button>

            <h3 className="text-xl font-bold text-ink mb-4">
              {modal === 'login' ? 'Đăng nhập Học viên' : 'Đăng ký tài khoản Học viên'}
            </h3>

            <div className="bg-soft p-1 rounded-lg grid grid-cols-2 gap-1 mb-5 text-sm">
              <button
                type="button"
                onClick={() => {
                  setErr(null);
                  setModal('login');
                }}
                className={`min-h-10 rounded-md font-medium whitespace-nowrap ${
                  modal === 'login'
                    ? 'bg-surface text-ink font-semibold border border-line'
                    : 'text-muted hover:text-ink'
                }`}
              >
                Đăng nhập
              </button>
              <button
                type="button"
                onClick={() => {
                  setErr(null);
                  setModal('register');
                }}
                className={`min-h-10 rounded-md font-medium whitespace-nowrap ${
                  modal === 'register'
                    ? 'bg-surface text-ink font-semibold border border-line'
                    : 'text-muted hover:text-ink'
                }`}
              >
                Đăng ký
              </button>
            </div>

            {err && (
              <div className="mb-4 p-3 rounded-lg badge-hard text-sm">
                {err}
              </div>
            )}

            {modal === 'login' ? (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text2 mb-1.5">
                    Tên đăng nhập hoặc Email
                  </label>
                  <input
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="Ví dụ: nguyen_ptit"
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text2 mb-1.5">
                    Mật khẩu
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Nhập mật khẩu"
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={loading}
                  className="btn-primary font-semibold min-h-11 rounded-lg w-full text-sm disabled:opacity-50 whitespace-nowrap"
                >
                  {loading ? 'Đang đăng nhập…' : 'Đăng nhập vào hệ thống'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-text2 mb-1">
                      Tên đăng nhập
                    </label>
                    <input
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      placeholder="sv_ptit_01"
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
                    required
                    className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                  />
                </div>
                <button
                  type="submit"
                  data-solid-btn="true"
                  disabled={loading}
                  className="btn-primary font-semibold min-h-11 rounded-lg w-full text-sm disabled:opacity-50 whitespace-nowrap"
                >
                  {loading ? 'Đang khởi tạo…' : 'Tạo tài khoản mới'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Profile Modal */}
      {modal === 'profile' && user && (
        <div className="fixed inset-0 z-50 bg-overlay flex items-center justify-center p-4">
          <div className="bg-surface border border-line rounded-2xl max-w-md w-full p-6">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
              <h3 className="text-base font-bold text-ink">
                Thiết lập hồ sơ &amp; mật khẩu
              </h3>
              <button
                type="button"
                onClick={() => setModal('none')}
                className="btn-secondary px-3 min-h-9 rounded-lg text-xs font-medium whitespace-nowrap"
              >
                Đóng
              </button>
            </div>
            {err && (
              <div className="mb-3 p-3 rounded-lg badge-hard text-sm">
                {err}
              </div>
            )}
            {msg && (
              <div className="mb-3 p-3 rounded-lg badge-easy text-sm">
                {msg}
              </div>
            )}
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text2 mb-1">
                  Tên hiển thị
                </label>
                <input
                  value={profName}
                  onChange={(e) => setProfName(e.target.value)}
                  className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text2 mb-1">
                  Ghi chú học tập / chuyên môn
                </label>
                <textarea
                  value={profBio}
                  onChange={(e) => setProfBio(e.target.value)}
                  rows={2}
                  className="w-full p-3 rounded-lg bg-canvas border border-line text-ink text-sm"
                />
              </div>
              <div className="pt-3 border-t border-line space-y-3">
                <div className="text-sm font-semibold text-ink">Đổi mật khẩu</div>
                <input
                  type="password"
                  placeholder="Mật khẩu hiện tại"
                  value={curPwd}
                  onChange={(e) => setCurPwd(e.target.value)}
                  className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                />
                <input
                  type="password"
                  placeholder="Mật khẩu mới (tối thiểu 6 ký tự)"
                  value={newPwd}
                  onChange={(e) => setNewPwd(e.target.value)}
                  className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-ink text-sm"
                />
              </div>
              <button
                type="submit"
                data-solid-btn="true"
                disabled={loading}
                className="btn-primary w-full min-h-11 rounded-lg font-semibold text-sm disabled:opacity-50 whitespace-nowrap"
              >
                {loading ? 'Đang lưu…' : 'Lưu thiết lập'}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
