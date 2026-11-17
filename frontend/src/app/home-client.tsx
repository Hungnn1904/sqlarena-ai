'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  ShieldCheck,
  UserPlus,
  CheckCircle2,
  Database,
  Layers,
  Sparkles,
} from 'lucide-react';
import AuthBar from '../components/AuthBar';
import LearnerWorkbench from '../components/LearnerWorkbench';
import { LearnerProgressView, LeaderboardView } from '../components/ProgressAndLeaderboard';
import AdminPortal from '../components/AdminPortal';
import { UserProfile, getMe, loginUser, extractApiError } from '../lib/api';

const VALID_TABS = new Set(['workbench', 'progress', 'leaderboard', 'admin']);

const HERO_DEMO_QUERIES = [
  {
    id: 'easy',
    label: '1. Lọc dữ liệu cơ bản (Dễ)',
    sql: `SELECT category_id, name\nFROM categories\nORDER BY category_id ASC\nLIMIT 4;`,
    columns: ['category_id', 'name'],
    runtimeMs: '2.4',
    rows: [
      ['1', 'Thiết bị điện tử & Máy tính'],
      ['2', 'Phụ kiện văn phòng'],
      ['3', 'Thiết bị mạng doanh nghiệp'],
      ['4', 'Lưu trữ & Đám mây'],
    ],
  },
  {
    id: 'join',
    label: '2. Kết nối bảng JOIN (Trung bình)',
    sql: `SELECT d.name AS phong_ban,\n       COUNT(e.employee_id) AS so_nhan_su\nFROM departments d\nLEFT JOIN employees e ON e.department_id = d.department_id\nGROUP BY d.department_id, d.name\nORDER BY so_nhan_su DESC;`,
    columns: ['phong_ban', 'so_nhan_su'],
    runtimeMs: '4.1',
    rows: [
      ['Kỹ thuật phần mềm', '18'],
      ['Vận hành kho vận', '14'],
      ['Kinh doanh B2B', '11'],
      ['Tài chính kế toán', '7'],
    ],
  },
  {
    id: 'agg',
    label: '3. Phân tích doanh thu (Khó)',
    sql: `SELECT c.tier AS hang_khach,\n       COUNT(o.order_id) AS tong_don,\n       SUM(o.total_amount) AS doanh_thu\nFROM customers c\nJOIN orders o ON o.customer_id = c.customer_id\nWHERE o.status = 'completed'\nGROUP BY c.tier\nORDER BY doanh_thu DESC;`,
    columns: ['hang_khach', 'tong_don', 'doanh_thu'],
    runtimeMs: '6.8',
    rows: [
      ['Enterprise', '42', '1,284,500,000'],
      ['Business', '89', '742,000,000'],
      ['Standard', '156', '318,900,000'],
    ],
  },
];

export default function HomeClient() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTabState] = useState<string>('workbench');
  const [booting, setBooting] = useState(true);
  const [demoLoading, setDemoLoading] = useState<'learner' | 'admin' | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [authModalTrigger, setAuthModalTrigger] = useState(0);
  const [initialAuthMode, setInitialAuthMode] = useState<'login' | 'register'>('login');
  const [selectedHeroDemo, setSelectedHeroDemo] = useState(0);

  const setActiveTab = (nextTab: string) => {
    const safeTab = VALID_TABS.has(nextTab) ? nextTab : 'workbench';
    setActiveTabState(safeTab);
    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem('sqlarena_active_tab', safeTab);
      const url = new URL(window.location.href);
      url.searchParams.set('tab', safeTab);
      window.history.replaceState(null, '', `${url.pathname}${url.search}`);
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const fromUrl = params.get('tab');
      const fromSession = window.sessionStorage.getItem('sqlarena_active_tab');
      const candidate = fromUrl && VALID_TABS.has(fromUrl)
        ? fromUrl
        : fromSession && VALID_TABS.has(fromSession)
        ? fromSession
        : 'workbench';
      setActiveTabState(candidate);
    }

    const initAuth = async () => {
      try {
        const token = window.localStorage.getItem('sqlarena_token');
        if (token) {
          const me = await getMe();
          setUser(me);
          if (me.role !== 'admin') {
            setActiveTabState((prev) => (prev === 'admin' ? 'workbench' : prev));
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
  }, []);

  const handleAuthSuccess = (token: string, u: UserProfile, targetTab?: string) => {
    window.localStorage.setItem('sqlarena_token', token);
    setUser(u);
    setDemoError(null);
    if (targetTab) {
      setActiveTab(u.role !== 'admin' && targetTab === 'admin' ? 'workbench' : targetTab);
    } else if (u.role !== 'admin' && activeTab === 'admin') {
      setActiveTab('workbench');
    }
  };

  const handleLogout = () => {
    window.localStorage.removeItem('sqlarena_token');
    setUser(null);
    setActiveTab('workbench');
  };

  const handleQuickDemo = async (role: 'learner' | 'admin') => {
    setDemoLoading(role);
    setDemoError(null);
    try {
      if (role === 'learner') {
        const res = await loginUser('nguyen_ptit', 'demo123');
        handleAuthSuccess(res.access_token, res.user, 'workbench');
      } else {
        const res = await loginUser('admin', 'admin123');
        handleAuthSuccess(res.access_token, res.user, 'admin');
      }
    } catch (e: any) {
      setDemoError(extractApiError(e, 'Không kết nối được tới máy chủ API. Vui lòng kiểm tra container backend.'));
    } finally {
      setDemoLoading(null);
    }
  };

  const currentHeroSample = HERO_DEMO_QUERIES[selectedHeroDemo] || HERO_DEMO_QUERIES[0];

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col">
      <AuthBar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onAuthSuccess={handleAuthSuccess}
        onLogout={handleLogout}
        onUserUpdated={setUser}
        authModalTrigger={authModalTrigger}
        initialAuthMode={initialAuthMode}
      />

      <main className="flex-1 max-w-[1520px] w-full mx-auto px-4 sm:px-6 py-6">
        {booting ? (
          <div className="p-12 rounded-xl bg-surface border border-line text-center text-sm text-muted">
            Đang kết nối hệ thống chấm bài PostgreSQL 17...
          </div>
        ) : !user ? (
          /* Interactive SQL Arena Quick-Start Welcome Hero */
          <section
            data-ui="sql-arena-quickstart"
            className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch pt-2 pb-8"
          >
            <div className="lg:col-span-7 bg-surface border border-line rounded-2xl p-6 sm:p-8 flex flex-col justify-between gap-6">
              <div className="space-y-5">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full badge-easy text-xs font-semibold">
                  <Database className="w-3.5 h-3.5" />
                  <span>Môi trường thực hành PostgreSQL 17 an toàn (Read-Only Sandbox)</span>
                </div>

                <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-ink tracking-tight leading-tight">
                  Luyện viết truy vấn SQL và ra đề tự động trên dữ liệu thực tế
                </h1>

                <div className="space-y-3 text-base text-text2 leading-relaxed">
                  <p>
                    <strong className="text-ink">1. Dành cho người học:</strong> Đọc đề bài tiếng Việt rõ ràng, tra cứu sơ đồ 13 bảng dữ liệu kèm khóa chính (<code className="text-sm px-1.5 py-0.5 rounded bg-soft text-ink">PK</code>) và khóa ngoại (<code className="text-sm px-1.5 py-0.5 rounded bg-soft text-ink">FK</code>), gõ lệnh SQL và xem kết quả ngay lập tức.
                  </p>
                  <p>
                    <strong className="text-ink">2. Trợ lý học tập tích hợp:</strong> Tự động lưu nháp theo từng bài, gợi ý hướng giải khi bí ý tưởng, giải thích lỗi cú pháp SQL dễ hiểu và đo chi phí truy vấn (<code className="text-sm px-1.5 py-0.5 rounded bg-soft text-ink">EXPLAIN</code>).
                  </p>
                  <p>
                    <strong className="text-ink">3. Dành cho giảng viên:</strong> Tạo đề bằng AI hoặc soạn thủ công, kéo thả gom nhiều câu hỏi vào một nhóm và đăng toàn bộ lên kệ bài tập chỉ với 1 lần bấm.
                  </p>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t border-line">
                {demoError && (
                  <div className="p-3 rounded-lg badge-hard text-sm">
                    {demoError}
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    data-solid-btn="true"
                    disabled={demoLoading !== null}
                    onClick={() => handleQuickDemo('learner')}
                    className="btn-primary min-h-12 px-5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <Play className="w-4 h-4" />
                    <span>
                      {demoLoading === 'learner'
                        ? 'Đang mở bàn làm bài...'
                        : 'Vào làm bài ngay (Tài khoản Sinh viên Demo)'}
                    </span>
                  </button>

                  <button
                    type="button"
                    data-solid-btn="true"
                    disabled={demoLoading !== null}
                    onClick={() => handleQuickDemo('admin')}
                    className="btn-blue min-h-12 px-5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>
                      {demoLoading === 'admin'
                        ? 'Đang mở cổng Giảng viên...'
                        : 'Vào cổng Giảng viên / Ra đề Demo'}
                    </span>
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setInitialAuthMode('login');
                    setAuthModalTrigger((c) => c + 1);
                  }}
                  className="btn-secondary w-full min-h-11 px-5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
                >
                  <UserPlus className="w-4 h-4 text-muted" />
                  <span>Đăng nhập / Tạo tài khoản riêng</span>
                </button>
              </div>
            </div>

            {/* Right Interactive Visual Artifact: Live SQL Sandbox Preview */}
            <div
              data-ui="interactive-sql-preview"
              className="lg:col-span-5 bg-surface border border-line rounded-2xl overflow-hidden flex flex-col justify-between"
            >
              <div>
                <div className="px-5 py-3.5 bg-soft border-b border-line flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm font-semibold text-ink">
                    <Layers className="w-4 h-4 text-brand" />
                    <span>Xem thử cách hệ thống chấm bài</span>
                  </div>
                  <span className="badge-easy px-2.5 py-0.5 rounded-md text-xs font-semibold">
                    PostgreSQL 17
                  </span>
                </div>

                <div className="p-4 border-b border-line bg-canvas flex flex-wrap gap-1.5">
                  {HERO_DEMO_QUERIES.map((item, idx) => {
                    const active = selectedHeroDemo === idx;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        data-solid-btn={active ? 'true' : undefined}
                        onClick={() => setSelectedHeroDemo(idx)}
                        className={`px-3 min-h-9 rounded-lg text-xs font-semibold ${
                          active ? 'btn-primary' : 'btn-secondary'
                        }`}
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>

                <div className="p-4 border-b border-line space-y-2">
                  <div className="flex items-center justify-between text-xs text-muted">
                    <span>Câu lệnh truy vấn mẫu (query.sql)</span>
                    <span className="tabular-nums">Thời gian chạy: {currentHeroSample.runtimeMs} ms</span>
                  </div>
                  <pre className="p-3.5 rounded-xl bg-canvas border border-line text-xs text-ink overflow-x-auto leading-relaxed">
                    {currentHeroSample.sql}
                  </pre>
                </div>

                <div className="p-4 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-text2">
                      Bảng dữ liệu kết quả ({currentHeroSample.rows.length} dòng)
                    </span>
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-brand">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Đạt 3/3 Test Cases (100 điểm)</span>
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-line">
                    <table className="w-full text-left border-collapse text-sm tabular-nums">
                      <thead>
                        <tr className="bg-soft border-b border-line text-ink font-semibold">
                          {currentHeroSample.columns.map((col) => (
                            <th key={col} className="px-3 py-2 text-xs font-mono">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {currentHeroSample.rows.map((r, rIdx) => (
                          <tr key={rIdx} className="bg-surface">
                            {r.map((cell, cIdx) => (
                              <td key={cIdx} className="px-3 py-2 text-xs text-ink">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <div className="px-5 py-3 bg-soft border-t border-line flex items-center justify-between text-xs text-text2">
                <span className="inline-flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-copper" />
                  <span>Chọn một tài khoản Demo bên trái để bắt đầu gõ SQL thật</span>
                </span>
              </div>
            </div>
          </section>
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
              {activeTab === 'admin' && (
                <AdminPortal
                  isAdmin={user.role === 'admin'}
                  onJumpToWorkbench={() => setActiveTab('workbench')}
                />
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </main>

      <footer className="border-t border-line bg-surface py-3.5 px-4 sm:px-6 text-xs text-muted">
        <div className="max-w-[1520px] mx-auto flex flex-wrap items-center justify-between gap-2">
          <span>SQL Arena PTIT: Hệ thống học tập, gom nhóm ra đề và chấm điểm SQL tự động trên PostgreSQL 17</span>
          <span>Chế độ thực thi an toàn (Read-Only Sandbox)</span>
        </div>
      </footer>
    </div>
  );
}
