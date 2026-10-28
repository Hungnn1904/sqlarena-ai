'use client';

import React, { useState } from 'react';
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
}

export default function AuthBar({
  user,
  activeTab,
  setActiveTab,
  onAuthSuccess,
  onLogout,
  onUserUpdated,
}: AuthBarProps) {
  const [modal, setModal] = useState<'none' | 'login' | 'register' | 'profile'>('none');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  // Form states
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
      setErr(e?.response?.data?.error?.message || 'Lỗi đăng nhập nhanh');
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
      setErr(e?.response?.data?.error?.message || 'Sai tài khoản hoặc mật khẩu');
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
      setErr(e?.response?.data?.error?.message || 'Đăng ký thất bại');
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
      setMsg('Đã lưu hồ sơ thành công!');
    } catch (e: any) {
      setErr(e?.response?.data?.error?.message || 'Cập nhật thất bại');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'workbench', label: '💻 Luyện Tập SQL (Sandbox)' },
    { id: 'progress', label: '📈 Tiến Độ & Kỹ Năng' },
    { id: 'leaderboard', label: '🏆 Bảng Xếp Hạng' },
    { id: 'admin', label: '🛡️ Quản Trị AI & Kiểm Duyệt' },
    { id: 'pipeline', label: '⚙️ Kiến Trúc 7-Step AI' },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 bg-[#0b1120]/95 backdrop-blur border-b border-[#1e2d45]">
        <div className="max-w-[1440px] mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#00d4ff] to-[#00e5a0] flex items-center justify-center text-[#0a0e17] font-black text-lg shadow-lg">
              SQL
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white tracking-tight text-base">
                  SQLArena AI
                </span>
                <span className="text-[0.68rem] font-mono uppercase px-2 py-0.5 rounded bg-[#00d4ff]/15 text-[#00d4ff] border border-[#00d4ff]/30">
                  Unified v7 · PostgreSQL 17
                </span>
              </div>
              <p className="text-[0.72rem] text-[#8ba3c7]">
                Hệ thống Sinh đề AI 2-Model, Read-Only SQL Sandbox & Bảng xếp hạng Thời gian thực
              </p>
            </div>
          </div>

          {/* Quick Demo Switchers + User Controls */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 bg-[#111827] border border-[#1e2d45] rounded-lg px-2 py-1">
              <span className="text-[0.68rem] font-mono text-[#5a7298] uppercase px-1">
                Chuyển nhanh:
              </span>
              <button
                onClick={() => quickLogin('nguyen_ptit', 'demo123', 'workbench')}
                disabled={loading}
                className={`text-xs px-2.5 py-1 rounded font-medium transition ${
                  user?.username === 'nguyen_ptit'
                    ? 'bg-[#00e5a0] text-[#0a0e17] font-semibold'
                    : 'text-[#8ba3c7] hover:text-white hover:bg-[#1e2d45]'
                }`}
              >
                🎓 Học viên (nguyen_ptit)
              </button>
              <button
                onClick={() => quickLogin('admin', 'admin123', 'admin')}
                disabled={loading}
                className={`text-xs px-2.5 py-1 rounded font-medium transition ${
                  user?.role === 'admin'
                    ? 'bg-[#ffb830] text-[#0a0e17] font-semibold'
                    : 'text-[#8ba3c7] hover:text-white hover:bg-[#1e2d45]'
                }`}
              >
                🛡️ Admin (admin)
              </button>
            </div>

            {user ? (
              <div className="flex items-center gap-2 bg-[#111827] border border-[#1e2d45] rounded-lg px-3 py-1.5">
                <button
                  onClick={openProfile}
                  className="text-left hover:opacity-90 transition flex items-center gap-2"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      user.role === 'admin' ? 'bg-[#ffb830]' : 'bg-[#00e5a0]'
                    }`}
                  />
                  <div>
                    <div className="text-xs font-semibold text-white leading-none">
                      {user.display_name || user.username}
                    </div>
                    <div className="text-[0.65rem] font-mono text-[#8ba3c7] uppercase">
                      @{user.username} · {user.role.toUpperCase()}
                    </div>
                  </div>
                </button>
                <button
                  onClick={openProfile}
                  className="text-xs px-2 py-1 rounded bg-[#1e2d45]/70 text-[#00d4ff] hover:bg-[#1e2d45]"
                >
                  Hồ sơ
                </button>
                <button
                  onClick={onLogout}
                  className="text-xs px-2 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20"
                >
                  Thoát
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setErr(null);
                    setModal('login');
                  }}
                  className="text-xs px-3 py-1.5 rounded-lg bg-[#00d4ff] text-[#0a0e17] font-semibold hover:opacity-90"
                >
                  Đăng nhập
                </button>
                <button
                  onClick={() => {
                    setErr(null);
                    setModal('register');
                  }}
                  className="text-xs px-3 py-1.5 rounded-lg border border-[#00d4ff]/40 text-[#00d4ff] hover:bg-[#00d4ff]/10"
                >
                  Đăng ký
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Bar */}
        <div className="max-w-[1440px] mx-auto px-4 flex items-center gap-1 overflow-x-auto border-t border-[#1e2d45]/60">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition ${
                activeTab === t.id
                  ? 'border-[#00d4ff] text-[#00d4ff] bg-[#00d4ff]/5 font-semibold'
                  : 'border-transparent text-[#8ba3c7] hover:text-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>

      {/* Modals for Login / Register / Profile */}
      {modal !== 'none' && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-[#1e2d45] rounded-xl max-w-md w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-white">
                {modal === 'login' && 'Đăng nhập SQLArena'}
                {modal === 'register' && 'Đăng ký tài khoản Học viên'}
                {modal === 'profile' && 'Hồ sơ cá nhân & Đổi mật khẩu'}
              </h3>
              <button
                onClick={() => setModal('none')}
                className="text-[#8ba3c7] hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {err && (
              <div className="mb-3 p-2.5 rounded bg-red-500/15 border border-red-500/30 text-red-300 text-xs">
                {err}
              </div>
            )}
            {msg && (
              <div className="mb-3 p-2.5 rounded bg-[#00e5a0]/15 border border-[#00e5a0]/30 text-[#00e5a0] text-xs">
                {msg}
              </div>
            )}

            {modal === 'login' && (
              <form onSubmit={handleLogin} className="space-y-3">
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">
                    Email hoặc Username
                  </label>
                  <input
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="nguyen_ptit hoặc admin@sqlarena.local"
                    required
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">Mật khẩu</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 rounded bg-[#00d4ff] text-[#0a0e17] font-bold text-sm"
                >
                  {loading ? 'Đang xử lý...' : 'Đăng nhập'}
                </button>
              </form>
            )}

            {modal === 'register' && (
              <form onSubmit={handleRegister} className="space-y-3">
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">Email</label>
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">
                    Username (3-50 ký tự)
                  </label>
                  <input
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">Họ và tên hiển thị</label>
                  <input
                    value={regDisplayName}
                    onChange={(e) => setRegDisplayName(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">
                    Mật khẩu (tối thiểu 6 ký tự)
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 rounded bg-[#00e5a0] text-[#0a0e17] font-bold text-sm"
                >
                  {loading ? 'Đang tạo tài khoản...' : 'Đăng ký ngay'}
                </button>
              </form>
            )}

            {modal === 'profile' && user && (
              <form onSubmit={handleSaveProfile} className="space-y-3">
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">Tên hiển thị</label>
                  <input
                    value={profName}
                    onChange={(e) => setProfName(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[#8ba3c7] mb-1">Giới thiệu (Bio)</label>
                  <textarea
                    value={profBio}
                    onChange={(e) => setProfBio(e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <div className="pt-2 border-t border-[#1e2d45]">
                  <div className="text-xs font-semibold text-[#00d4ff] mb-2">
                    Đổi mật khẩu (bỏ trống nếu không đổi)
                  </div>
                  <input
                    type="password"
                    placeholder="Mật khẩu hiện tại"
                    value={curPwd}
                    onChange={(e) => setCurPwd(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm mb-2"
                  />
                  <input
                    type="password"
                    placeholder="Mật khẩu mới (>= 6 ký tự)"
                    value={newPwd}
                    onChange={(e) => setNewPwd(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0a0e17] border border-[#1e2d45] text-white text-sm"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 rounded bg-[#00d4ff] text-[#0a0e17] font-bold text-sm"
                >
                  {loading ? 'Đang lưu...' : 'Lưu thay đổi'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
