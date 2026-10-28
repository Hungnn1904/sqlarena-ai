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
    { id: 'workbench', label: 'SQL Workspace', code: '01', icon: Terminal },
    { id: 'progress', label: 'Tiến độ & Kỹ năng', code: '02', icon: BarChart3 },
    { id: 'leaderboard', label: 'Bảng xếp hạng', code: '03', icon: Trophy },
    { id: 'admin', label: 'Quản trị & Kiểm duyệt', code: '04', icon: ShieldCheck },
    { id: 'pipeline', label: 'Kiến trúc Hệ thống', code: '05', icon: GitBranch },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 bg-[#090d16]/95 backdrop-blur-md border-b border-[#1b2436]">
        {/* Top Engineering Telemetry Bar */}
        <div className="border-b border-[#151d2c] bg-[#060911] px-5 py-1.5">
          <div className="max-w-[1520px] mx-auto flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-[#64748b]">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 text-[#94a3b8]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                PG-17 ENGINE ONLINE
              </span>
              <span className="hidden sm:inline text-[#334155]">|</span>
              <span className="hidden sm:inline">
                SANDBOX: <strong className="text-[#cbd5e1] font-normal">enterprise_db (read-only)</strong>
              </span>
              <span className="hidden md:inline text-[#334155]">|</span>
              <span className="hidden md:inline">
                SCHEMA: <strong className="text-[#cbd5e1] font-normal">13 tables · 13,400+ rows</strong>
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-[#64748b] flex items-center gap-1">
                <ArrowRightLeft className="w-3 h-3 text-[#475569]" />
                Chế độ kiểm thử nhanh:
              </span>
              <button
                onClick={() => quickLogin('nguyen_ptit', 'demo123', 'workbench')}
                disabled={loading}
                className={`px-2 py-0.5 rounded transition border ${
                  user?.username === 'nguyen_ptit'
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                    : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#131b2e]'
                }`}
              >
                Learner (nguyen_ptit)
              </button>
              <button
                onClick={() => quickLogin('admin', 'admin123', 'admin')}
                disabled={loading}
                className={`px-2 py-0.5 rounded transition border ${
                  user?.role === 'admin'
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                    : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#131b2e]'
                }`}
              >
                Admin (admin)
              </button>
            </div>
          </div>
        </div>

        {/* Main Navigation Row */}
        <div className="max-w-[1520px] mx-auto px-5 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded bg-[#111827] border border-[#26334d] flex items-center justify-center text-[#38bdf8]">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white tracking-tight text-sm">
                    SQLArena
                  </span>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-[#131c2e] text-[#94a3b8] border border-[#22304a]">
                    v7.0
                  </span>
                </div>
                <div className="text-[10px] font-mono text-[#64748b] hidden sm:block">
                  PTIT Data Engineering Platform
                </div>
              </div>
            </div>

            <nav className="flex items-center gap-1 overflow-x-auto">
              {tabs.map((t) => {
                const Icon = t.icon;
                const active = activeTab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setActiveTab(t.id)}
                    className={`relative group flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition ${
                      active
                        ? 'text-white'
                        : 'text-[#94a3b8] hover:text-white hover:bg-[#111827]'
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="activeNavTab"
                        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        className="absolute inset-0 rounded-md bg-[#152036] border border-[#293b5f] -z-10"
                      />
                    )}
                    <Icon
                      className={`w-3.5 h-3.5 ${
                        active ? 'text-[#38bdf8]' : 'text-[#64748b] group-hover:text-[#94a3b8]'
                      }`}
                    />
                    <span>{t.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Right Account + Pitch + Theme Controls */}
          <div className="flex items-center gap-2">
            {onTogglePitch && (
              <button
                onClick={onTogglePitch}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium border transition ${
                  pitchOpen
                    ? 'bg-[#0284c7] text-white border-[#38bdf8]'
                    : 'bg-[#111827] hover:bg-[#172033] text-[#cbd5e1] border-[#1f2b42]'
                }`}
                title="Mở kịch bản trình chiếu & hướng dẫn sử dụng"
              >
                <Presentation className="w-3.5 h-3.5 text-[#38bdf8]" />
                <span className="hidden xl:inline">Pitch & Hướng dẫn</span>
              </button>
            )}

            <button
              onClick={toggleTheme}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-[#111827] hover:bg-[#172033] border border-[#1f2b42] text-xs font-mono text-[#cbd5e1] transition"
              title="Chuyển đổi giao diện Sáng / Tối"
            >
              <motion.span
                key={theme}
                initial={{ rotate: -45, opacity: 0, scale: 0.7 }}
                animate={{ rotate: 0, opacity: 1, scale: 1 }}
                transition={{ duration: 0.25 }}
                className="flex items-center"
              >
                {theme === 'dark' ? (
                  <Sun className="w-3.5 h-3.5 text-amber-400" />
                ) : (
                  <Moon className="w-3.5 h-3.5 text-sky-500" />
                )}
              </motion.span>
              <span className="hidden md:inline">
                {theme === 'dark' ? 'Light' : 'Dark'}
              </span>
            </button>
            {user ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={openProfile}
                  className="flex items-center gap-2.5 px-3 py-1.5 rounded-md bg-[#111827] hover:bg-[#172033] border border-[#1f2b42] transition text-left"
                >
                  <div className="w-6 h-6 rounded bg-[#1e293b] border border-[#334155] flex items-center justify-center text-[11px] font-mono font-semibold text-white">
                    {(user.display_name || user.username).slice(0, 2).toUpperCase()}
                  </div>
                  <div className="hidden sm:block">
                    <div className="text-xs font-medium text-white leading-none">
                      {user.display_name || user.username}
                    </div>
                    <div className="text-[10px] font-mono text-[#64748b] mt-0.5">
                      @{user.username} ·{' '}
                      <span
                        className={
                          user.role === 'admin' ? 'text-amber-400' : 'text-emerald-400'
                        }
                      >
                        {user.role}
                      </span>
                    </div>
                  </div>
                </button>
                <button
                  onClick={onLogout}
                  title="Đăng xuất"
                  className="p-2 rounded-md bg-[#111827] hover:bg-red-950/40 border border-[#1f2b42] hover:border-red-900/50 text-[#94a3b8] hover:text-red-300 transition"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setErr(null);
                    setModal('login');
                  }}
                  className="text-xs px-3 py-1.5 rounded-md bg-[#1e293b] hover:bg-[#334155] text-white font-medium border border-[#334155] transition"
                >
                  Đăng nhập
                </button>
                <button
                  onClick={() => {
                    setErr(null);
                    setModal('register');
                  }}
                  className="text-xs px-3 py-1.5 rounded-md bg-[#0284c7] hover:bg-[#0369a1] text-white font-medium transition"
                >
                  Tạo tài khoản
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Clean Modal */}
      {modal !== 'none' && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#0f1624] border border-[#22304a] rounded-lg max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#1b263b]">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-[#38bdf8]" />
                <h3 className="text-sm font-semibold text-white">
                  {modal === 'login' && 'Đăng nhập hệ thống'}
                  {modal === 'register' && 'Đăng ký tài khoản học viên'}
                  {modal === 'profile' && 'Thiết lập hồ sơ & bảo mật'}
                </h3>
              </div>
              <button
                onClick={() => setModal('none')}
                className="text-[#64748b] hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {err && (
              <div className="mb-4 p-2.5 rounded bg-red-950/40 border border-red-900/60 text-red-300 text-xs">
                {err}
              </div>
            )}
            {msg && (
              <div className="mb-4 p-2.5 rounded bg-emerald-950/40 border border-emerald-900/60 text-emerald-300 text-xs">
                {msg}
              </div>
            )}

            {modal === 'login' && (
              <form onSubmit={handleLogin} className="space-y-3.5">
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">
                    Tên đăng nhập hoặc Email
                  </label>
                  <input
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="nguyen_ptit"
                    required
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs focus:outline-none focus:border-[#38bdf8]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Mật khẩu</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs focus:outline-none focus:border-[#38bdf8]"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 rounded bg-[#0284c7] hover:bg-[#0369a1] text-white font-medium text-xs transition"
                >
                  {loading ? 'Đang xác thực...' : 'Đăng nhập'}
                </button>
              </form>
            )}

            {modal === 'register' && (
              <form onSubmit={handleRegister} className="space-y-3.5">
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Địa chỉ Email</label>
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">
                    Username (3–50 ký tự)
                  </label>
                  <input
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Họ tên hiển thị</label>
                  <input
                    value={regDisplayName}
                    onChange={(e) => setRegDisplayName(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">
                    Mật khẩu (tối thiểu 6 ký tự)
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 rounded bg-[#0284c7] hover:bg-[#0369a1] text-white font-medium text-xs transition"
                >
                  {loading ? 'Đang khởi tạo...' : 'Hoàn tất đăng ký'}
                </button>
              </form>
            )}

            {modal === 'profile' && user && (
              <form onSubmit={handleSaveProfile} className="space-y-3.5">
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Tên hiển thị</label>
                  <input
                    value={profName}
                    onChange={(e) => setProfName(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Ghi chú chuyên môn</label>
                  <textarea
                    value={profBio}
                    onChange={(e) => setProfBio(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                </div>
                <div className="pt-3 border-t border-[#1b263b] space-y-2.5">
                  <div className="text-xs font-medium text-[#cbd5e1]">
                    Thay đổi mật khẩu
                  </div>
                  <input
                    type="password"
                    placeholder="Mật khẩu hiện tại"
                    value={curPwd}
                    onChange={(e) => setCurPwd(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                  <input
                    type="password"
                    placeholder="Mật khẩu mới (tối thiểu 6 ký tự)"
                    value={newPwd}
                    onChange={(e) => setNewPwd(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#090d16] border border-[#22304a] text-white text-xs"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 rounded bg-[#0284c7] hover:bg-[#0369a1] text-white font-medium text-xs transition"
                >
                  {loading ? 'Đang lưu...' : 'Lưu thiết lập'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
