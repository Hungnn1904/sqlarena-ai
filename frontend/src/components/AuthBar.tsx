'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Database,
  Terminal,
  BarChart3,
  Trophy,
  ShieldCheck,
  GitBranch,
  User,
  LogOut,
  ArrowRightLeft,
  Sun,
  Moon,
  Presentation,
  X,
} from 'lucide-react';
import { useTheme } from './theme-provider';
import {
  UserProfile,
  loginUser,
  registerUser,
  updateProfile,
  changePassword,
} from '../lib/api';

interface AuthBarProps {
  user: UserProfile | null;
  activeTab: string;
  setActiveTab: (t: string) => void;
  onAuthSuccess: (token: string, user: UserProfile) => void;
  onLogout: () => void;
  onUserUpdated: (user: UserProfile) => void;
  pitchOpen?: boolean;
  onTogglePitch?: () => void;
}

export default function AuthBar({
  user,
  activeTab,
  setActiveTab,
  onAuthSuccess,
  onLogout,
  onUserUpdated,
  pitchOpen,
  onTogglePitch,
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

  const quickLogin = async (id: string, pwd: string, targetTab?: string) => {
    setLoading(true);
    setErr(null);
    try {
      const res = await loginUser(id, pwd);
      onAuthSuccess(res.access_token, res.user);
      if (targetTab) setActiveTab(targetTab);
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Không thể chuyển tài khoản');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      const res = await loginUser(identifier, password);
      onAuthSuccess(res.access_token, res.user);
      setModal('none');
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Thông tin đăng nhập không hợp lệ');
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
      onAuthSuccess(res.access_token, res.user);
      setModal('none');
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Đăng ký không thành công');
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
      setMsg('Đã cập nhật thông tin tài khoản.');
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Cập nhật thất bại');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'workbench', label: 'Làm bài' },
    { id: 'progress', label: 'Tiến độ' },
    { id: 'leaderboard', label: 'Xếp hạng' },
    { id: 'admin', label: 'Quản trị' },
    { id: 'pipeline', label: 'Kiến trúc' },
  ];

  return (
    <>
      <header className="command-header sticky top-0 z-40 bg-[var(--paper)]/95 backdrop-blur-md border-b border-[var(--line)]">
        <div className="max-w-[1520px] mx-auto px-5 h-[60px] flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5">
              <div className="relative w-8 h-8 rounded-full bg-[#5C7F71] flex items-center justify-center text-[#F5EDDC] font-mono text-[10px] font-bold tracking-tighter shadow-xs">
                SQL
                <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#B2653B] border-2 border-[var(--paper)]" />
              </div>
              <div className="leading-tight">
                <div className="font-bold text-[var(--ink)] tracking-tight text-base">
                  sqlarena
                </div>
                <div className="text-[9px] font-mono tracking-[0.18em] uppercase text-[var(--muted)]">
                  HỌC SQL
                </div>
              </div>
            </div>

            <nav className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
              {tabs.map((t) => {
                const active = activeTab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setActiveTab(t.id)}
                    className={`relative group flex items-center px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                      active
                        ? 'text-[var(--on-accent)]'
                        : 'text-[var(--text2)] hover:text-[var(--ink)] hover:bg-[var(--soft)]'
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="activeNavTab"
                        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        className="absolute inset-0 rounded-lg bg-[var(--green)] -z-10"
                      />
                    )}
                    <span>{t.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Right Account + Pitch + Theme Controls */}
          <div className="flex items-center gap-2">
            {/* Quick Role Switch */}
            <div className="hidden lg:flex items-center bg-[var(--soft)] p-0.5 rounded-lg border border-[var(--line)] text-[11px] font-mono">
              <button
                onClick={() => quickLogin('nguyen_ptit', 'demo123', 'workbench')}
                disabled={loading}
                className={`px-2 py-1 rounded-md transition ${
                  user?.role !== 'admin'
                    ? 'bg-[var(--surface)] text-[var(--ink)] font-semibold shadow-2xs'
                    : 'text-[var(--muted)] hover:text-[var(--ink)]'
                }`}
              >
                Học viên
              </button>
              <button
                onClick={() => quickLogin('admin', 'admin123', 'admin')}
                disabled={loading}
                className={`px-2 py-1 rounded-md transition ${
                  user?.role === 'admin'
                    ? 'bg-[var(--surface)] text-[var(--copper)] font-semibold shadow-2xs'
                    : 'text-[var(--muted)] hover:text-[var(--ink)]'
                }`}
              >
                Admin
              </button>
            </div>

            {/* SÁNG / TỐI Switch */}
            <button
              onClick={toggleTheme}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--soft)] border border-[var(--line)] text-[10px] font-mono font-bold tracking-wider text-[var(--text2)] transition"
              title="Chuyển đổi giao diện Sáng / Tối"
            >
              <span className={theme === 'light' ? 'text-[var(--ink)]' : 'text-[var(--muted)]'}>
                SÁNG
              </span>
              <span className="w-7 h-3.5 rounded-full bg-[var(--surface)] border border-[var(--line)] relative flex items-center px-0.5">
                <span
                  className={`w-2.5 h-2.5 rounded-full bg-[var(--copper)] transition-transform duration-200 ${
                    theme === 'dark' ? 'translate-x-3' : 'translate-x-0'
                  }`}
                />
              </span>
              <span className={theme === 'dark' ? 'text-[var(--ink)]' : 'text-[var(--muted)]'}>
                TỐI
              </span>
            </button>

            {user ? (
              <div className="flex items-center gap-1.5">
                <button
                  onClick={openProfile}
                  className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[var(--surface)] hover:bg-[var(--soft)] border border-[var(--line)] transition text-left"
                >
                  <div className="w-6 h-6 rounded-full bg-[var(--green)] flex items-center justify-center text-[10px] font-mono font-bold text-[var(--on-accent)]">
                    {(user.display_name || user.username).slice(0, 2).toUpperCase()}
                  </div>
                  <div className="hidden sm:block">
                    <div className="text-xs font-semibold text-[var(--ink)] leading-none">
                      {user.display_name || user.username}
                    </div>
                    <div className="text-[10px] font-mono text-[var(--muted)] mt-0.5">
                      {user.role === 'admin' ? 'Admin' : 'Học viên'}
                    </div>
                  </div>
                </button>
                <button
                  onClick={onLogout}
                  title="Đăng xuất"
                  className="px-2.5 py-1.5 rounded-lg bg-[var(--surface)] hover:bg-[var(--red)]/15 border border-[var(--line)] text-xs font-medium text-[var(--muted)] hover:text-[var(--red)] transition"
                >
                  Đăng xuất
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  setErr(null);
                  setModal('login');
                }}
                className="text-xs px-3 py-1.5 rounded-lg bg-[var(--green)] hover:bg-[var(--green-hover)] text-[var(--on-accent)] font-semibold transition"
              >
                Đăng nhập
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Editorial Auth & Profile Modal */}
      {(modal === 'login' || modal === 'register') && (
        <div className="fixed inset-0 z-50 bg-black/65 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#F5EDDC] text-[#181818] border border-[rgba(24,24,24,0.16)] rounded-2xl max-w-3xl w-full p-2.5 shadow-2xl grid grid-cols-1 md:grid-cols-12 gap-2 relative">
            <button
              onClick={() => setModal('none')}
              className="absolute top-5 right-5 text-xs font-medium text-[#6F6B60] hover:text-[#181818] px-2 py-1 rounded z-10"
              title="Đóng"
            >
              Đóng
            </button>

            {/* Left Editorial Sage Panel */}
            <div className="md:col-span-5 bg-[#5C7F71] text-[#F5EDDC] rounded-xl p-7 flex flex-col justify-between min-h-[340px]">
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-[#181818] text-[#F5EDDC] flex items-center justify-center font-mono text-[9px] font-bold">
                    SQL
                  </div>
                  <span className="font-bold text-sm tracking-tight">sqlarena</span>
                </div>
                <h2 className="text-2xl font-bold leading-snug pt-2">
                  Học bằng cách{' '}
                  <span className="editorial-serif text-[#E3C08D]">đặt câu hỏi.</span>
                </h2>
                <p className="text-xs text-[#F5EDDC]/90 leading-relaxed">
                  Luyện SQL qua đề được sinh, duyệt và chấm tự động trên PostgreSQL.
                </p>
              </div>

              <div className="bg-[#181818] text-[#F5EDDC] p-3.5 rounded-lg font-mono text-xs leading-relaxed shadow-inner">
                SELECT skill, progress FROM learners ORDER BY progress DESC;
              </div>
            </div>

            {/* Right Warm Paper Form Panel */}
            <div className="md:col-span-7 bg-[#F5EDDC] text-[#181818] p-7 flex flex-col justify-center">
              <div className="text-[#B2653B] text-[11px] font-bold tracking-[0.14em] uppercase mb-1">
                BẮT ĐẦU HÀNH TRÌNH
              </div>
              <h3 className="text-2xl font-bold text-[#181818] mb-4">
                {modal === 'login' ? 'Đăng nhập.' : 'Tạo tài khoản.'}
              </h3>

              {/* Segmented Pill Switcher */}
              <div className="bg-[#EBE2CD] p-1 rounded-lg grid grid-cols-2 mb-5 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setErr(null);
                    setModal('login');
                  }}
                  className={`py-1.5 rounded-md transition ${
                    modal === 'login'
                      ? 'bg-[#FBF7EC] text-[#181818] shadow-xs font-semibold'
                      : 'text-[#6F6B60] hover:text-[#181818]'
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
                  className={`py-1.5 rounded-md transition ${
                    modal === 'register'
                      ? 'bg-[#FBF7EC] text-[#181818] shadow-xs font-semibold'
                      : 'text-[#6F6B60] hover:text-[#181818]'
                  }`}
                >
                  Tạo tài khoản
                </button>
              </div>

              {err && (
                <div className="mb-3 p-2.5 rounded-lg bg-[#802520]/10 border border-[#802520]/30 text-[#802520] text-xs">
                  {err}
                </div>
              )}

              {modal === 'login' ? (
                <form onSubmit={handleLogin} className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-[#45423A] mb-1">
                      Tên đăng nhập hoặc Email
                    </label>
                    <input
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      placeholder="nguyen_ptit"
                      required
                      className="w-full px-3 py-2 rounded-lg bg-[#FBF7EC] border border-[rgba(24,24,24,0.16)] text-[#181818] text-xs focus:outline-none focus:border-[#5C7F71]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#45423A] mb-1">
                      Mật khẩu
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-lg bg-[#FBF7EC] border border-[rgba(24,24,24,0.16)] text-[#181818] text-xs focus:outline-none focus:border-[#5C7F71]"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="bg-[#5C7F71] hover:bg-[#496B5D] text-[#F5EDDC] font-semibold py-2.5 rounded-lg w-full text-xs transition mt-1"
                  >
                    {loading ? 'Đang xử lý...' : 'Đăng nhập →'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleRegister} className="space-y-2.5">
                  <div className="grid grid-cols-2 gap-2.5">
                    <div>
                      <label className="block text-xs font-medium text-[#45423A] mb-1">
                        Username
                      </label>
                      <input
                        value={regUsername}
                        onChange={(e) => setRegUsername(e.target.value)}
                        required
                        className="w-full px-3 py-2 rounded-lg bg-[#FBF7EC] border border-[rgba(24,24,24,0.16)] text-[#181818] text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-[#45423A] mb-1">
                        Họ tên hiển thị
                      </label>
                      <input
                        value={regDisplayName}
                        onChange={(e) => setRegDisplayName(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-[#FBF7EC] border border-[rgba(24,24,24,0.16)] text-[#181818] text-xs"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#45423A] mb-1">
                      Địa chỉ Email
                    </label>
                    <input
                      type="email"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-lg bg-[#FBF7EC] border border-[rgba(24,24,24,0.16)] text-[#181818] text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#45423A] mb-1">
                      Mật khẩu (tối thiểu 6 ký tự)
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-lg bg-[#FBF7EC] border border-[rgba(24,24,24,0.16)] text-[#181818] text-xs"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="bg-[#5C7F71] hover:bg-[#496B5D] text-[#F5EDDC] font-semibold py-2.5 rounded-lg w-full text-xs transition mt-1"
                  >
                    {loading ? 'Đang khởi tạo...' : 'Tạo tài khoản →'}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      {modal === 'profile' && user && (
        <div className="fixed inset-0 z-50 bg-black/65 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[var(--line)]">
              <h3 className="text-sm font-semibold text-[var(--ink)]">
                Thiết lập hồ sơ & bảo mật
              </h3>
              <button
                onClick={() => setModal('none')}
                className="text-xs font-medium text-[var(--muted)] hover:text-[var(--ink)] px-2 py-1"
              >
                Đóng
              </button>
            </div>
            {err && (
              <div className="mb-3 p-2.5 rounded bg-[var(--red)]/10 border border-[var(--red)]/30 text-[var(--red)] text-xs">
                {err}
              </div>
            )}
            {msg && (
              <div className="mb-3 p-2.5 rounded bg-[var(--green)]/15 border border-[var(--green)]/30 text-[var(--green)] text-xs">
                {msg}
              </div>
            )}
            <form onSubmit={handleSaveProfile} className="space-y-3.5">
              <div>
                <label className="block text-xs text-[var(--text2)] mb-1">Tên hiển thị</label>
                <input
                  value={profName}
                  onChange={(e) => setProfName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--paper)] border border-[var(--line)] text-[var(--ink)] text-xs"
                />
              </div>
              <div>
                <label className="block text-xs text-[var(--text2)] mb-1">Ghi chú chuyên môn</label>
                <textarea
                  value={profBio}
                  onChange={(e) => setProfBio(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--paper)] border border-[var(--line)] text-[var(--ink)] text-xs"
                />
              </div>
              <div className="pt-3 border-t border-[var(--line)] space-y-2.5">
                <div className="text-xs font-medium text-[var(--ink)]">Thay đổi mật khẩu</div>
                <input
                  type="password"
                  placeholder="Mật khẩu hiện tại"
                  value={curPwd}
                  onChange={(e) => setCurPwd(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--paper)] border border-[var(--line)] text-[var(--ink)] text-xs"
                />
                <input
                  type="password"
                  placeholder="Mật khẩu mới (tối thiểu 6 ký tự)"
                  value={newPwd}
                  onChange={(e) => setNewPwd(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--paper)] border border-[var(--line)] text-[var(--ink)] text-xs"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-[var(--green)] hover:bg-[var(--green-hover)] text-[var(--on-accent)] font-semibold text-xs transition"
              >
                {loading ? 'Đang lưu...' : 'Lưu thiết lập'}
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
