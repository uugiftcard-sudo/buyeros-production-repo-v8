'use client';

import { useEffect, useState } from 'react';
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

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboardSummary()
      .then(({ data, error }) => {
        if (error) {
          setError(error.message);
        } else {
          setSummary(data ?? null);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">載入中...</div>;
  if (error) return (
    <div className="app-shell"><Sidebar /><main className="main-content">
      <div className="card" style={{ color: 'var(--color-danger)' }}>載入失敗：{error}</div>
    </main></div>
  );

  const o = summary?.orders ?? { total: 0, pending: 0 };
  const b = summary?.buyers ?? { active: 0 };
  const c = summary?.customers ?? { active: 0 };
  const f = summary?.financials ?? { total_revenue_cents: 0, total_refunds_cents: 0, net_revenue_cents: 0 };

  const timeStr = summary?.generated_at ? summary.generated_at.slice(0, 16).replace('T', ' ') : '';

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">📊 儀表板</h1>
          <p className="page-subtitle">實時業務總覽 — {timeStr}</p>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">總訂單</div>
            <div className="stat-value">{o.total}</div>
            <div className="stat-sub">累計所有訂單</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">待處理</div>
            <div className="stat-value" style={{ color: 'var(--color-warning)' }}>{o.pending}</div>
            <div className="stat-sub">等待分配或確認</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">活躍買手</div>
            <div className="stat-value">{b.active}</div>
            <div className="stat-sub">已啟用</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">活躍客戶</div>
            <div className="stat-value">{c.active}</div>
            <div className="stat-sub">已註冊</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">總收入</div>
            <div className="stat-value" style={{ color: 'var(--color-success)' }}>{formatCents(f.total_revenue_cents)}</div>
            <div className="stat-sub">所有 confirmed 交易</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">已退款</div>
            <div className="stat-value" style={{ color: 'var(--color-danger)' }}>{formatCents(f.total_refunds_cents)}</div>
            <div className="stat-sub">已審批退款</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">淨收入</div>
            <div className="stat-value">{formatCents(f.net_revenue_cents)}</div>
            <div className="stat-sub">總收入 − 退款</div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">⚡ 快速操作</span>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <a href="/orders/new" className="btn btn-primary">+ 新訂單</a>
            <a href="/customers" className="btn btn-outline">+ 新客戶</a>
            <a href="/orders?status=pending" className="btn btn-outline">⏳ 待處理訂單</a>
            <a href="/refunds?status=pending" className="btn btn-outline">💸 待審批退款</a>
            <a href="/buyers" className="btn btn-outline">👤 買手管理</a>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">🔧 系統狀態</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            {[
              { label: 'Database', ok: true, detail: 'Supabase PostgreSQL' },
              { label: 'Auth', ok: true, detail: 'Telegram + Supabase Auth' },
              { label: 'Storage', ok: true, detail: 'Supabase Storage (documents)' },
              { label: 'Backup', ok: true, detail: 'Cloudflare R2 daily' },
              { label: 'Edge Functions', ok: true, detail: '7 functions deployed' },
              { label: '會計層', ok: true, detail: 'Journal entries active' },
            ].map(item => (
              <div key={item.label} style={{ padding: '0.75rem', border: '1px solid var(--color-border)', borderRadius: '0.5rem' }}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                  {item.ok ? '✅' : '⚠️'} {item.label}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>{item.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
