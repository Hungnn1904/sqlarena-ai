'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Database,
  Sun,
  Moon,
  LogOut,
} from 'lucide-react';
import { useTheme } from './theme-provider';
import {
  UserProfile,
  updateProfile,
  changePassword,
  extractApiError,
} from '../lib/api';

export type AppSection = 'workbench' | 'progress' | 'leaderboard' | 'admin';

interface AuthBarProps {
  user: UserProfile | null;
  activeSection: AppSection;
  onNavigateSection: (section: AppSection) => void;
  onLogout: () => void;
  onUserUpdated: (user: UserProfile) => void;
  guestMode?: 'login' | 'register';
  onSelectGuestMode?: (mode: 'login' | 'register') => void;
}

export default function AuthBar({
  user,
  activeSection,
  onNavigateSection,
  onLogout,
  onUserUpdated,
  guestMode = 'login',
  onSelectGuestMode,
}: AuthBarProps) {
  const { theme, toggleTheme } = useTheme();
  const [profileOpen, setProfileOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const [profName, setProfName] = useState('');
  const [profBio, setProfBio] = useState('');
  const [curPwd, setCurPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');

  const openProfile = () => {
    if (!user) return;
    setProfName(user.display_name || user.username);
    setProfBio(user.bio || '');
    setCurPwd('');
    setNewPwd('');
    setErr(null);
    setMsg(null);
    setProfileOpen(true);
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

  const navItems: { id: AppSection; href: string; label: string }[] = user
    ? user.role === 'admin'
      ? [
          { id: 'workbench', href: '/', label: 'Làm bài' },
          { id: 'progress', href: '/progress', label: 'Tiến độ' },
          { id: 'leaderboard', href: '/leaderboard', label: 'Xếp hạng' },
          { id: 'admin', href: '/admin', label: 'Quản trị' },
        ]
      : [
          { id: 'workbench', href: '/', label: 'Làm bài' },
          { id: 'progress', href: '/progress', label: 'Tiến độ' },
          { id: 'leaderboard', href: '/leaderboard', label: 'Xếp hạng' },
        ]
    : [];

  const roleLabel = user?.role === 'admin' ? 'Quản trị viên' : 'Học viên';

  return (
    <>
      <header className="sticky top-0 z-40 bg-surface border-b border-line">
        <div className="max-w-[1520px] mx-auto px-4 sm:px-6 min-h-16 py-2 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-5">
            <Link
              href="/"
              onClick={(e) => {
                e.preventDefault();
                if (user) onNavigateSection('workbench');
              }}
              className="flex items-center gap-2.5 text-left min-h-10 whitespace-nowrap"
            >
              <div
                data-solid-btn="true"
                className="w-9 h-9 rounded-lg btn-primary flex items-center justify-center shrink-0"
              >
                <Database className="w-4 h-4" />
              </div>
              <div className="leading-tight whitespace-nowrap">
                <div className="font-bold text-ink text-base tracking-tight">
                  SQLArena
                </div>
                <div className="text-xs text-muted">
                  Thực hành PostgreSQL 17
                </div>
              </div>
            </Link>

            {navItems.length > 0 && (
              <nav
                aria-label="Điều hướng theo vai trò"
                className="flex items-center gap-1 overflow-x-auto scrollbar-hide"
              >
                {navItems.map((item) => {
                  const active = activeSection === item.id;
                  return (
                    <Link
                      key={item.id}
                      href={item.href}
                      onClick={(e) => {
                        e.preventDefault();
                        onNavigateSection(item.id);
                      }}
                      data-solid-btn={active ? 'true' : undefined}
                      className={`relative flex items-center px-3.5 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap ${
                        active
                          ? 'text-on-brand'
                          : 'text-text2 hover:text-ink hover:bg-soft'
                      }`}
                    >
                      {active && (
                        <motion.span
                          layoutId="activeRoleRouteTab"
                          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                          className="absolute inset-0 rounded-lg bg-brand -z-10"
                        />
                      )}
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            )}
          </div>

          <div className="flex items-center gap-2">
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

            {user ? (
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
                  <div className="hidden sm:block leading-tight whitespace-nowrap">
                    <div className="text-sm font-semibold text-ink">
                      {user.display_name || user.username}
                    </div>
                    <div className="text-xs text-muted">{roleLabel}</div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={onLogout}
                  title="Đăng xuất"
                  aria-label="Đăng xuất"
                  className="btn-secondary flex items-center gap-1.5 px-3 min-h-10 rounded-lg text-sm font-medium whitespace-nowrap"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden sm:inline">Đăng xuất</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  data-solid-btn={guestMode === 'register' ? 'true' : undefined}
                  onClick={() => onSelectGuestMode && onSelectGuestMode('register')}
                  className={`px-3.5 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap ${
                    guestMode === 'register' ? 'btn-primary' : 'btn-secondary'
                  }`}
                >
                  Đăng ký
                </button>
                <button
                  type="button"
                  data-solid-btn={guestMode === 'login' ? 'true' : undefined}
                  onClick={() => onSelectGuestMode && onSelectGuestMode('login')}
                  className={`px-4 min-h-10 rounded-lg text-sm font-semibold whitespace-nowrap ${
                    guestMode === 'login' ? 'btn-primary' : 'btn-secondary'
                  }`}
                >
                  Đăng nhập
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Profile Modal */}
      {profileOpen && user && (
        <div className="fixed inset-0 z-50 bg-overlay flex items-center justify-center p-4">
          <div className="bg-surface border border-line rounded-2xl max-w-md w-full p-6">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-line">
              <h3 className="text-base font-bold text-ink">
                Thiết lập hồ sơ &amp; mật khẩu
              </h3>
              <button
                type="button"
                onClick={() => setProfileOpen(false)}
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
                  className="w-full px-3.5 min-h-11 rounded-lg bg-canvas border border-line text-sm text-ink"
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
