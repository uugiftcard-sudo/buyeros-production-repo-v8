'use client';

import { useEffect, useState } from 'react';
import { formatCents } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import { supabase } from '@/lib/supabase';

export default function FinancialsPage() {
  const [trialBalance, setTrialBalance] = useState<Record<string, unknown>[]>([]);
  const [pnl, setPnl] = useState<Record<string, unknown>[]>([]);
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      const [tbResult, pnlResult] = await Promise.all([
        supabase.from('v_trial_balance').select('*'),
        supabase.from('v_pnl_summary').select('*').eq('period', period).order('sort_order'),
      ]);
      setTrialBalance(tbResult.data ?? []);
      setPnl(pnlResult.data ?? []);
      setLoading(false);
    };
    fetchData();
  }, [period]);

  if (loading) return <div className="loading">載入財務數據中...</div>;

  const revenue = pnl.find(r => (r as { label?: string }).label === 'Revenue');
  const expenses = pnl.find(r => (r as { label?: string }).label === 'Expenses');
  const netProfit = pnl.find(r => (r as { label?: string }).label === 'Net Profit');

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">📈 財務報表</h1>
          <p className="page-subtitle">
            <input
              type="month"
              value={period}
              onChange={e => setPeriod(e.target.value)}
              className="form-input"
              style={{ width: 'auto', display: 'inline-block' }}
            />
          </p>
        </div>

        {/* P&L Summary */}
        <div className="stats-grid" style={{ marginBottom: '2rem' }}>
          <div className="stat-card">
            <div className="stat-label">收入 (Revenue)</div>
            <div className="stat-value" style={{ color: 'var(--color-success)' }}>
              {revenue ? formatCents(Number(revenue.amount_cents)) : '—'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">支出 (Expenses)</div>
            <div className="stat-value" style={{ color: 'var(--color-danger)' }}>
              {expenses ? formatCents(Number(expenses.amount_cents)) : '—'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">淨利潤 (Net Profit)</div>
            <div className="stat-value">
              {netProfit ? formatCents(Number(netProfit.amount_cents)) : '—'}
            </div>
          </div>
        </div>

        {/* Trial Balance */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📊 試算表 (Trial Balance)</span>
          </div>
          {trialBalance.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '2rem' }}>
              暂无会计分录数据（请先在 Supabase Studio 应用会计层 migration）
            </p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>科目編碼</th>
                  <th>科目名稱</th>
                  <th>類型</th>
                  <th style={{ textAlign: 'right' }}>借方 (DR)</th>
                  <th style={{ textAlign: 'right' }}>貸方 (CR)</th>
                  <th style={{ textAlign: 'right' }}>餘額</th>
                </tr>
              </thead>
              <tbody>
                {trialBalance.map((row, i) => {
                  const r = row as Record<string, unknown>;
                  return (
                  <tr key={i}>
                    <td style={{ fontFamily: 'monospace' }}>{String(r.account_code ?? '')}</td>
                    <td>{String(r.account_name ?? '')}</td>
                    <td><span className="badge badge-pending">{String(r.type ?? '')}</span></td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      {Number(r.total_debit_cents) > 0 ? formatCents(Number(r.total_debit_cents)) : '—'}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                      {Number(r.total_credit_cents) > 0 ? formatCents(Number(r.total_credit_cents)) : '—'}
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 600, fontFamily: 'monospace' }}>
                      {formatCents(Math.abs(Number(r.balance_cents)))}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* P&L Bar Chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📊 月度收支趨勢圖</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>最近 6 期</span>
          </div>
          {(() => {
            // Mock 6-month data for visualization (replace with real API data when available)
            const mockMonths = ['2025-12', '2026-01', '2026-02', '2026-03', '2026-04', '2026-05'];
            const mockRevenue = [1250000, 1480000, 1100000, 1650000, 1320000, 980000];
            const mockExpenses = [820000, 950000, 740000, 1080000, 880000, 650000];
            const maxVal = Math.max(...mockRevenue, ...mockExpenses);

            const chartH = 200;
            const chartW = 600;
            const barGroupW = chartW / mockMonths.length;
            const barW = barGroupW * 0.35;
            const labelH = 28;
            const scale = (chartH - labelH) / maxVal;

            return (
              <div style={{ overflowX: 'auto' }}>
                <svg
                  viewBox={`0 0 ${chartW} ${chartH}`}
                  style={{ width: '100%', maxWidth: chartW, height: 'auto', display: 'block', fontFamily: 'monospace' }}
                >
                  {/* Grid lines */}
                  {[0, 0.25, 0.5, 0.75, 1].map((frac, i) => {
                    const y = chartH - labelH - frac * (chartH - labelH);
                    const val = Math.round(maxVal * frac / 10000) * 10000;
                    return (
                      <g key={i}>
                        <line x1={0} y1={y} x2={chartW} y2={y} stroke="#e5e7eb" strokeWidth={1} />
                        <text x={chartW - 4} y={y - 3} textAnchor="end" fontSize={9} fill="#9ca3af">
                          HK${(val / 100).toFixed(0)}k
                        </text>
                      </g>
                    );
                  })}

                  {/* Bars */}
                  {mockMonths.map((month, i) => {
                    const groupX = i * barGroupW + barGroupW * 0.15;
                    const revH = mockRevenue[i] * scale;
                    const expH = mockExpenses[i] * scale;
                    const revY = chartH - labelH - revH;
                    const expY = chartH - labelH - expH;
                    const label = month.slice(5) + '月';

                    return (
                      <g key={month}>
                        {/* Revenue bar */}
                        <rect
                          x={groupX} y={revY}
                          width={barW} height={revH}
                          fill="#10b981" rx={2}
                        />
                        {/* Expense bar */}
                        <rect
                          x={groupX + barW + 4} y={expY}
                          width={barW} height={expH}
                          fill="#f87171" rx={2}
                        />
                        {/* Month label */}
                        <text
                          x={groupX + barW + 2} y={chartH - 8}
                          textAnchor="middle" fontSize={10} fill="#6b7280"
                        >
                          {label}
                        </text>
                      </g>
                    );
                  })}
                </svg>
                <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem', fontSize: '0.8rem' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ width: 12, height: 12, background: '#10b981', borderRadius: 2, display: 'inline-block' }}></span>
                    收入 (Revenue)
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ width: 12, height: 12, background: '#f87171', borderRadius: 2, display: 'inline-block' }}></span>
                    支出 (Expenses)
                  </span>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
                  💡 圖表使用示例數據。Supabase 中執行 <code style={{ background: '#f3f4f6', padding: '0.1rem 0.3rem' }}>SELECT * FROM v_pnl_summary ORDER BY period DESC LIMIT 6</code> 以獲取真實數據。
                </p>
              </div>
            );
          })()}
        </div>

        {/* Monthly P&L Detail */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📋 月度收支明細</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>期間</th>
                <th>類別</th>
                <th>金額 (Cents)</th>
              </tr>
            </thead>
            <tbody>
              {pnl.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                    暂无 P&L 数据（请先应用会计层 migration）
                  </td>
                </tr>
              ) : (
                pnl.map((r, i) => {
                  const r2 = r as Record<string, unknown>;
                  return (
                  <tr key={i}>
                    <td>{String(r2.period ?? '')}</td>
                    <td>{String(r2.label ?? '')}</td>
                    <td style={{ fontFamily: 'monospace' }}>{formatCents(Math.abs(Number(r2.amount_cents)))}</td>
                  </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Quick SQL reference */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔧 快速 SQL 參考</span>
          </div>
          <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', background: '#f3f4f6', padding: '1rem', borderRadius: '0.375rem' }}>
            <p>-- 試算表<br/>SELECT * FROM v_trial_balance;</p>
            <p style={{ marginTop: '0.5rem' }}>-- 月度損益<br/>SELECT * FROM v_pnl_summary ORDER BY period, sort_order;</p>
            <p>-- 資產負債表（截至某日）<br/>SELECT * FROM v_balance_sheet(&#39;2026-05-31&#39;);</p>
            <p style={{ marginTop: '0.5rem' }}>-- 應收帳齡<br/>SELECT * FROM v_ar_aging;</p>
            <p style={{ marginTop: '0.5rem' }}>-- 月結<br/>SELECT close_accounting_period(&#39;2026-05&#39;);</p>
          </div>
        </div>
      </main>
    </div>
  );
}
