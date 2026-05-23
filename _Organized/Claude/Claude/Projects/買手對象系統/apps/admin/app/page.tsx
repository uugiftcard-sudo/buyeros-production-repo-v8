'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getDashboardSummary, formatCents } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

interface DashboardSummary {
  orders?: { total: number; pending: number };
  buyers?: { active: number };
  customers?: { active: number };
  financials?: {
    total_revenue_cents: number;
    total_refunds_cents: number;
    net_revenue_cents: number;
  };
  generated_at?: string;
}

function StatCard({
  label, value, sub, accent = '#4f46e5', icon,
}: {
  label: string; value: string | number; sub?: string;
  accent?: string; icon?: string;
}) {
  return (
    <div className="stat-card" style={{ ['--stat-accent' as string]: accent }}>
      {icon && <div className="stat-icon">{icon}</div>}
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

function SystemStatusRow({
  label, detail, ok,
}: { label: string; detail: string; ok: boolean }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0.75rem 0',
      borderBottom: '1px solid var(--border-subtle)',
    }}>
      <div>
        <div style={{ fontSize: '0.875rem', fontWeight: 550, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: ok ? 'var(--success)' : 'var(--danger)', fontSize: '0.75rem' }}>●</span>
          {label}
        </div>
        <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)', marginTop: '1px' }}>{detail}</div>
      </div>
      <span className="badge" style={{ background: 'var(--success-light)', color: 'var(--success-text)', fontSize: '0.7rem' }}>
        {ok ? '正常' : '異常'}
      </span>
    </div>
  );
}

const quickLinks = [
  { label: '建立新訂單', href: '/orders/new', icon: '📦' },
  { label: '管理買手', href: '/buyers', icon: '🛒' },
  { label: '查閱交易記錄', href: '/transactions', icon: '💳' },
  { label: '月結管理', href: '/periods', icon: '📅' },
  { label: '團隊管理', href: '/teams', icon: '🏆' },
  { label: '員工管理', href: '/staff', icon: '👤' },
  { label: '審計日誌', href: '/audit-log', icon: '🕵️' },
  { label: '系統設定', href: '/settings', icon: '⚙️' },
];

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboardSummary()
      .then(({ data, error }) => {
        if (error) setError(error.message);
        else setSummary(data ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="loading" style={{ minHeight: '60vh' }}>
          <div className="loading-dot" />
          <div className="loading-dot" />
          <div className="loading-dot" />
          <span style={{ marginLeft: '0.5rem' }}>載入中...</span>
        </div>
      </main>
    </div>
  );

  if (error) return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="alert alert-danger">
          <span>⚠️</span>
          <span>載入失敗：{error}</span>
        </div>
      </main>
    </div>
  );

  const o = summary?.orders ?? { total: 0, pending: 0 };
  const b = summary?.buyers ?? { active: 0 };
  const c = summary?.customers ?? { active: 0 };
  const f = summary?.financials ?? {
    total_revenue_cents: 0, total_refunds_cents: 0, net_revenue_cents: 0
  };
  const timeStr = summary?.generated_at
    ? summary.generated_at.slice(0, 16).replace('T', ' ')
    : '';

  const hour = new Date().getHours();
  const greeting = hour < 12 ? '早安' : hour < 18 ? '午安' : '晚安';

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">

        {/* Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">{greeting}，Admin</h1>
            <p className="page-subtitle">
              買手對象系統實時總覽
              {timeStr && <span> · 更新於 {timeStr}</span>}
            </p>
          </div>
          <div className="page-header-right">
            <Link href="/orders/new" className="btn btn-primary">+ 新訂單</Link>
          </div>
        </div>

        {/* Stats */}
        <div className="stats-grid">
          <StatCard label="總訂單" value={o.total.toLocaleString()} sub="累計所有訂單" icon="📦" accent="#4f46e5" />
          <StatCard label="待處理" value={o.pending} sub="等待分配或確認" icon="⏳" accent="#d97706" />
          <StatCard label="活躍買手" value={b.active} sub="已啟用" icon="🛒" accent="#7c3aed" />
          <StatCard label="活躍客戶" value={c.active} sub="已註冊" icon="👥" accent="#0891b2" />
          <StatCard label="總收入" value={formatCents(f.total_revenue_cents)} sub="所有 confirmed 交易" icon="💰" accent="#059669" />
          <StatCard label="已退款" value={formatCents(f.total_refunds_cents)} sub="已審批退款" icon="↩️" accent="#dc2626" />
        </div>

        {/* Quick Actions */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <span className="card-title">⚡ 快速操作</span>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
            <Link href="/orders/new" className="btn btn-primary btn-sm">+ 新訂單</Link>
            <Link href="/customers" className="btn btn-secondary btn-sm">+ 新客戶</Link>
            <Link href="/orders?status=pending" className="btn btn-ghost btn-sm">⏳ 待處理</Link>
            <Link href="/refunds?status=pending" className="btn btn-ghost btn-sm">💸 待審批退款</Link>
            <Link href="/buyers" className="btn btn-ghost btn-sm">👤 買手管理</Link>
            <Link href="/financials" className="btn btn-ghost btn-sm">📊 財務報表</Link>
          </div>
        </div>

        {/* Two-column bottom section */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '1.5rem', alignItems: 'start' }}>

          {/* System Status */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">🔧 系統狀態</span>
            </div>
            <SystemStatusRow label="Database" detail="Supabase PostgreSQL" ok />
            <SystemStatusRow label="Edge Functions" detail="7 functions deployed" ok />
            <SystemStatusRow label="Auth" detail="Telegram + Supabase Auth" ok />
            <SystemStatusRow label="Storage" detail="Supabase Storage" ok />
            <SystemStatusRow label="會計層" detail="Journal entries active" ok />
            <SystemStatusRow label="備份" detail="Cloudflare R2 daily" ok />
          </div>

          {/* Right column */}
          <div>
            {/* Revenue summary card */}
            <div className="card" style={{
              background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
              border: 'none',
              color: '#fff',
            }}>
              <div style={{
                color: 'rgba(255,255,255,0.65)',
                fontSize: '0.75rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                marginBottom: '0.4rem',
              }}>淨收入</div>
              <div style={{
                fontSize: '2rem',
                fontWeight: 750,
                letterSpacing: '-0.03em',
                lineHeight: 1.1,
              }}>{formatCents(f.net_revenue_cents)}</div>
              <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.8rem', marginTop: '0.4rem' }}>
                總收入 − 已退款
              </div>
              <div style={{
                display: 'flex', gap: '1.5rem',
                marginTop: '1.25rem',
                paddingTop: '1rem',
                borderTop: '1px solid rgba(255,255,255,0.15)',
              }}>
                <div>
                  <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>總收入</div>
                  <div style={{ fontWeight: 650, fontSize: '0.95rem', marginTop: '2px' }}>
                    {formatCents(f.total_revenue_cents)}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>已退款</div>
                  <div style={{ fontWeight: 650, fontSize: '0.95rem', marginTop: '2px', color: '#fca5a5' }}>
                    {formatCents(f.total_refunds_cents)}
                  </div>
                </div>
              </div>
            </div>

            {/* Quick links */}
            <div className="card" style={{ marginTop: '1rem' }}>
              <div className="card-header">
                <span className="card-title" style={{ fontSize: '0.875rem' }}>📋 快捷導航</span>
              </div>
              <div style={{ display: 'grid', gap: '0.5rem' }}>
                {quickLinks.map(link => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="quick-link"
                  >
                    <span>{link.icon}</span>
                    {link.label}
                    <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.75rem' }}>→</span>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
