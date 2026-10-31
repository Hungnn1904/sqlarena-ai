'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import AuthBar from '../components/AuthBar';
import LearnerWorkbench from '../components/LearnerWorkbench';
import { LearnerProgressView, LeaderboardView } from '../components/ProgressAndLeaderboard';
import AdminPortal from '../components/AdminPortal';
import { UserProfile, getMe, loginUser } from '../lib/api';

export default function HomeClient() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<string>('workbench');
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = window.localStorage.getItem('sqlarena_token');
        if (token) {
          const me = await getMe();
          setUser(me);
          setBooting(false);
          return;
        }
      } catch {
        window.localStorage.removeItem('sqlarena_token');
      }
      try {
        const res = await loginUser('nguyen_ptit', 'demo123');
        window.localStorage.setItem('sqlarena_token', res.access_token);
        setUser(res.user);
      } catch {}
      setBooting(false);
    };
    initAuth();
  }, []);

  const handleAuthSuccess = (token: string, u: UserProfile) => {
    window.localStorage.setItem('sqlarena_token', token);
    setUser(u);
  };

  const handleLogout = () => {
    window.localStorage.removeItem('sqlarena_token');
    setUser(null);
  };

  return (
    <div className="min-h-screen bg-[#060911] text-[#e2e8f0] flex flex-col transition-colors duration-300">
      <AuthBar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onAuthSuccess={handleAuthSuccess}
        onLogout={handleLogout}
        onUserUpdated={setUser}
      />

      <main className="flex-1 max-w-[1520px] w-full mx-auto px-5 py-5 relative z-10">
        {booting ? (
          <div className="p-12 text-center text-xs font-mono text-[#64748b]">
            Initializing PostgreSQL 17 Enterprise Sandbox & Unified API...
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            >
              {activeTab === 'workbench' && <LearnerWorkbench />}
              {activeTab === 'progress' && <LearnerProgressView />}
              {activeTab === 'leaderboard' && <LeaderboardView />}
              {activeTab === 'admin' && <AdminPortal isAdmin={user?.role === 'admin'} />}
            </motion.div>
          </AnimatePresence>
        )}
      </main>

      <footer className="border-t border-[var(--line)] bg-[var(--paper)] py-3 px-5 text-xs text-[var(--muted)] font-mono relative z-10">
        <div className="max-w-[1520px] mx-auto flex items-center justify-between">
          <span>sqlarena · Nền tảng học & chấm thi SQL tự động trên PostgreSQL 17</span>
        </div>
      </footer>
    </div>
  );
}
