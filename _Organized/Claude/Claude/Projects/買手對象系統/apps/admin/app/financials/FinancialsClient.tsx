'use client';

// BuyerOS — Financials Dashboard Client Root
// app/financials/FinancialsClient.tsx
//
// 'use client' root component — manages period state, React Query, and tab routing.

import { useState, useCallback } from 'react';
import { getFinancials, closePeriod, type FinancialsData } from '@/lib/api';
import StatCard from '@/components/StatCard';
import PeriodBadge from '@/components/PeriodBadge';
import ConfirmModal from '@/components/ConfirmModal';
import { SkeletonStats, SkeletonTable } from '@/components/SkeletonLoader';
import {
  formatCents, formatCentsShort, formatMonth,
  exportPnLCsv, exportTrialBalanceCsv, exportARAgingCsv,
  type TabId,
} from '@/lib/financials';

// ─── Tab Content Components ───────────────────────────────────────────────

function PnLTab({ data }: { data: FinancialsData }) {
  const { monthlyPnL, summary } = data;
  // Build chart data: last 12 months
  const months = [...new Set(monthlyPnL.map(r => r.month))].sort().slice(-12);
  const chartData = months.map(month => {
    const revenue = monthlyPnL
      .filter(r => r.month === month && r.type === 'revenue')
      .reduce((s, r) => s + r.amount_cents, 0);
    const expense = monthlyPnL
      .filter(r => r.month === month && r.type === 'expense')
      .reduce((s, r) => s + r.amount_cents, 0);
    return { month, revenue, expense };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
        <StatCard
          label="收入"
          value={formatCents(summary.totalRevenueCents)}
          accent="var(--success)"
        />
        <StatCard
          label="支出"
          value={formatCents(summary.totalExpenseCents)}
          accent="var(--danger)"
        />
        <StatCard
          label="淨利潤"
          value={formatCents(summary.netProfitCents)}
          accent={summary.netProfitCents >= 0 ? 'var(--primary)' : 'var(--danger)'}
        />
      </div>

      {/* SVG Bar Chart (no external lib) */}
      {chartData.length === 0 ? (
        <div className="card">
          <div className="card-header"><span className="card-title">月趨勢圖</span></div>
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
            暫無資料（請先在 Supabase Studio 執行 seed.sql 載入測試數據）
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-header">
            <span className="card-title">月收支趨勢圖</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              最近 {chartData.length} 個月
            </span>
          </div>
          <BarChart data={chartData} />
        </div>
      )}

      {/* Category breakdown */}
      {monthlyPnL.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">收支分類</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <CategoryList items={monthlyPnL.filter(r => r.type === 'revenue')} type="收入" accent="#059669" />
            <CategoryList items={monthlyPnL.filter(r => r.type === 'expense')} type="支出" accent="#dc2626" />
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Inline BarChart (pure SVG, no external chart lib needed) ───────────────

function BarChart({ data }: { data: Array<{ month: string; revenue: number; expense: number }> }) {
  if (data.length === 0) return null;

  const PADDING = { top: 16, right: 20, bottom: 36, left: 64 };
  const W = 700;
  const H = 220;
  const chartW = W - PADDING.left - PADDING.right;
  const chartH = H - PADDING.top - PADDING.bottom;

  const maxVal = Math.max(...data.map(d => Math.max(d.revenue, d.expense)), 1);
  const groupW = chartW / data.length;
  const barW = groupW * 0.32;
  const barGap = groupW * 0.06;

  const xScale = (i: number) => PADDING.left + i * groupW + barGap;
  const yScale = (v: number) => PADDING.top + chartH - (v / maxVal) * chartH;

  // Y axis ticks
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(frac => ({
    y: PADDING.top + chartH - frac * chartH,
    label: formatCentsShort(Math.round(maxVal * frac)),
  }));

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', maxWidth: W, display: 'block', fontFamily: 'var(--font-sans)' }}
      >
        {/* Grid lines */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={PADDING.left} y1={t.y} x2={W - PADDING.right} y2={t.y}
              stroke="var(--border)" strokeWidth={1} strokeDasharray="4,4" />
            <text x={PADDING.left - 6} y={t.y + 4} textAnchor="end"
              fontSize={9} fill="var(--color-text-muted)">{t.label}</text>
          </g>
        ))}

        {/* Bars */}
        {data.map((d, i) => {
          const revH = (d.revenue / maxVal) * chartH;
          const expH = (d.expense / maxVal) * chartH;
          const gx = xScale(i);
          const revY = PADDING.top + chartH - revH;
          const expY = PADDING.top + chartH - expH;

          return (
            <g key={d.month}>
              {/* Revenue bar */}
              <rect x={gx} y={revY} width={barW} height={revH}
                fill="#10b981" rx={2} opacity={0.85} />
              {/* Expense bar */}
              <rect x={gx + barW + 2} y={expY} width={barW} height={expH}
                fill="#f87171" rx={2} opacity={0.85} />
              {/* Month label */}
              <text
                x={gx + barW + 1}
                y={H - 8}
                textAnchor="middle"
                fontSize={9}
                fill="var(--color-text-muted)"
              >
                {formatMonth(d.month).replace(' ', '\n')}
              </text>
            </g>
          );
        })}

        {/* Axes */}
        <line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={PADDING.top + chartH}
          stroke="var(--border)" strokeWidth={1} />
        <line x1={PADDING.left} y1={PADDING.top + chartH} x2={W - PADDING.right} y2={PADDING.top + chartH}
          stroke="var(--border)" strokeWidth={1} />
      </svg>

      <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem', fontSize: '0.8rem', paddingLeft: '0.5rem' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ width: 12, height: 12, background: '#10b981', borderRadius: 2, display: 'inline-block' }}></span>
          收入
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ width: 12, height: 12, background: '#f87171', borderRadius: 2, display: 'inline-block' }}></span>
          支出
        </span>
      </div>
    </div>
  );
}

// ─── Category List ─────────────────────────────────────────────────────────

function CategoryList({
  items,
  type,
  accent,
}: {
  items: Array<{ account_name: string; amount_cents: number }>;
  type: string;
  accent: string;
}) {
  const total = items.reduce((s, i) => s + i.amount_cents, 0);
  return (
    <div>
      <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '0.5rem', color: accent }}>
        {type} — {formatCents(total)}
      </div>
      {items.map(item => (
        <div key={item.account_name} style={{
          display: 'flex', justifyContent: 'space-between',
          fontSize: '0.8rem', padding: '0.25rem 0',
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          <span style={{ color: 'var(--color-text-muted)' }}>{item.account_name}</span>
          <span style={{ fontFamily: 'monospace', color: accent }}>
            {formatCents(item.amount_cents)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Trial Balance Tab ─────────────────────────────────────────────────────

function TrialBalanceTab({ data }: { data: FinancialsData }) {
  const [sortKey, setSortKey] = useState<string>('account_code');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const rows = data.trialBalance
    .filter(r => !typeFilter || r.type === typeFilter)
    .sort((a, b) => {
      const av = a[sortKey as keyof typeof a];
      const bv = b[sortKey as keyof typeof b];
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    });

  const totalDebit = rows.reduce((s, r) => s + r.total_debit_cents, 0);
  const totalCredit = rows.reduce((s, r) => s + r.total_credit_cents, 0);

  const SortIcon = ({ col }: { col: string }) => (
    <span style={{ marginLeft: 4, fontSize: '0.7rem', opacity: sortKey === col ? 1 : 0.4 }}>
      {sortKey === col ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
    </span>
  );

  const TYPE_LABELS: Record<string, string> = {
    asset: '資產', liability: '負債', equity: '權益', revenue: '收入', expense: '支出',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>篩選類型：</span>
        {['', 'asset', 'liability', 'equity', 'revenue', 'expense'].map(t => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`btn btn-sm ${typeFilter === t ? 'btn-primary' : 'btn-ghost'}`}
          >
            {t === '' ? '全部' : TYPE_LABELS[t] ?? t}
          </button>
        ))}
        <button
          className="btn btn-sm btn-ghost"
          style={{ marginLeft: 'auto' }}
          onClick={() => exportTrialBalanceCsv(rows)}
        >
          ⬇ 匯出 CSV
        </button>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('account_code')} style={{ cursor: 'pointer' }}>
                科目編碼 <SortIcon col="account_code" />
              </th>
              <th onClick={() => handleSort('account_name')} style={{ cursor: 'pointer' }}>
                科目名稱 <SortIcon col="account_name" />
              </th>
              <th onClick={() => handleSort('type')} style={{ cursor: 'pointer' }}>
                類型 <SortIcon col="type" />
              </th>
              <th style={{ textAlign: 'right' }}>借方 (DR)</th>
              <th style={{ textAlign: 'right' }}>貸方 (CR)</th>
              <th style={{ textAlign: 'right' }}>餘額</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {row.account_code}
                </td>
                <td>{row.account_name}</td>
                <td>
                  <span className={`badge ${TYPE_LABELS[row.type] ? 'badge-muted' : ''}`}>
                    {TYPE_LABELS[row.type] ?? row.type}
                  </span>
                </td>
                <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {row.total_debit_cents > 0 ? formatCents(row.total_debit_cents) : '—'}
                </td>
                <td style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  {row.total_credit_cents > 0 ? formatCents(row.total_credit_cents) : '—'}
                </td>
                <td style={{
                  textAlign: 'right', fontFamily: 'monospace', fontSize: '0.85rem',
                  fontWeight: 600,
                  color: row.balance_cents < 0 ? 'var(--danger)' : undefined,
                }}>
                  {formatCents(row.balance_cents)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ background: 'var(--page-bg)', fontWeight: 700 }}>
              <td colSpan={3} style={{ fontSize: '0.85rem' }}>合計</td>
              <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-success)' }}>
                {formatCents(totalDebit)}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-success)' }}>
                {formatCents(totalCredit)}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'monospace', color: totalDebit === totalCredit ? 'var(--success)' : 'var(--danger)' }}>
                {totalDebit === totalCredit ? '✓ 平衡' : `✗ 不平衡`}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

// ─── Balance Sheet Tab ─────────────────────────────────────────────────────

function BalanceSheetTab({ data }: { data: FinancialsData }) {
  const { balanceSheet } = data;
  const assets = balanceSheet.filter(r => r.type === 'asset');
  const liabilities = balanceSheet.filter(r => r.type === 'liability');
  const equity = balanceSheet.filter(r => r.type === 'equity');

  const sum = (rows: typeof balanceSheet) =>
    rows.reduce((s, r) => s + r.balance_cents, 0);

  const totalAssets = sum(assets);
  const totalLiabilities = sum(liabilities);
  const totalEquity = sum(equity);

  function Section({ title, rows, color }: { title: string; rows: typeof balanceSheet; color: string }) {
    const [open, setOpen] = useState(true);
    const total = sum(rows);
    return (
      <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '0.75rem 1rem', background: 'var(--surface)', border: 'none',
            borderBottom: open ? '1px solid var(--border)' : 'none',
            cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem',
          }}
        >
          <span style={{ color }}>{title}</span>
          <span style={{ fontFamily: 'monospace', marginRight: '0.5rem' }}>
            {formatCents(total)}
            <span style={{ marginLeft: 8, fontSize: '0.8rem', color: 'var(--color-text-muted)', fontWeight: 400 }}>
              {open ? '▲' : '▼'}
            </span>
          </span>
        </button>
        {open && (
          <div style={{ padding: '0.5rem 0' }}>
            {rows.map(r => (
              <div key={r.account_code} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '0.35rem 1rem', fontSize: '0.85rem',
                borderBottom: '1px solid var(--border-subtle)',
              }}>
                <span style={{ fontFamily: 'monospace', color: 'var(--color-text-muted)', marginRight: '0.5rem' }}>
                  {r.account_code}
                </span>
                <span>{r.account_name}</span>
                <span style={{ fontFamily: 'monospace', minWidth: 100, textAlign: 'right' }}>
                  {formatCents(r.balance_cents)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <Section title="資產 (Assets)" rows={assets} color="#0284c7" />
      <Section title="負債 (Liabilities)" rows={liabilities} color="#dc2626" />
      <Section title="權益 (Equity)" rows={equity} color="#059669" />

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem', padding: '1rem',
        background: 'var(--primary-light)',
        borderRadius: 'var(--radius)',
        fontWeight: 700, fontSize: '0.9rem',
      }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#0284c7', marginBottom: '0.25rem' }}>總資產</div>
          <div style={{ fontFamily: 'monospace', color: '#0284c7' }}>{formatCents(totalAssets)}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#dc2626', marginBottom: '0.25rem' }}>總負債</div>
          <div style={{ fontFamily: 'monospace', color: '#dc2626' }}>{formatCents(totalLiabilities)}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#059669', marginBottom: '0.25rem' }}>總權益</div>
          <div style={{ fontFamily: 'monospace', color: '#059669' }}>{formatCents(totalEquity)}</div>
        </div>
      </div>

      <div style={{
        textAlign: 'center', padding: '0.75rem',
        background: totalAssets === totalLiabilities + totalEquity
          ? 'var(--success-light)' : 'var(--danger-light)',
        borderRadius: 'var(--radius)', fontWeight: 600,
        color: totalAssets === totalLiabilities + totalEquity
          ? 'var(--success-text)' : 'var(--danger-text)',
      }}>
        {totalAssets === totalLiabilities + totalEquity
          ? `✓ 資產 = 負債 + 權益（${formatCents(totalAssets)}）`
          : `✗ 不平衡：資產 ${formatCents(totalAssets)} ≠ 負債+權益 ${formatCents(totalLiabilities + totalEquity)}`
        }
      </div>
    </div>
  );
}

// ─── AR Aging Tab ──────────────────────────────────────────────────────────

function ARAgingTab({ data, period }: { data: FinancialsData; period: string }) {
  const { arAging } = data;
  const has90plus = arAging.some(r => r.bucket === '90plus');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Alert banner */}
      {has90plus && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.75rem',
          padding: '0.75rem 1rem',
          background: 'var(--danger-light)', border: '1px solid var(--danger)',
          borderRadius: 'var(--radius)', color: 'var(--danger-text)', fontWeight: 600,
        }}>
          <span style={{ fontSize: '1.2rem' }}>⚠️</span>
          有 {arAging.filter(r => r.bucket === '90plus').length} 筆帳款逾期超過 90 天，需要立即跟進
        </div>
      )}

      {/* Summary by bucket */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem' }}>
        {(['current', '30', '60', '90', '90plus'] as const).map(bucket => {
          const BUCKET_LABELS: Record<string, string> = {
            current: '未逾期', '30': '逾期 1-30 天', '60': '逾期 31-60 天',
            '90': '逾期 61-90 天', '90plus': '逾期 90+ 天',
          };
          const BUCKET_COLORS: Record<string, string> = {
            current: 'var(--success)', '30': 'var(--warning)', '60': '#ea580c',
            '90': 'var(--danger)', '90plus': '#991b1b',
          };
          const items = arAging.filter(r => r.bucket === bucket);
          const total = items.reduce((s, r) => s + r.amount_cents, 0);
          return (
            <div key={bucket} style={{
              padding: '0.75rem', border: '1px solid var(--border)',
              borderRadius: 'var(--radius)', textAlign: 'center',
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>
                {BUCKET_LABELS[bucket]}
              </div>
              <div style={{ fontFamily: 'monospace', fontWeight: 700, color: BUCKET_COLORS[bucket], fontSize: '1rem' }}>
                {formatCents(total)}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                {items.length} 筆
              </div>
            </div>
          );
        })}
      </div>

      {/* Detail table */}
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>客戶</th>
              <th>逾期天數</th>
              <th>帳齡</th>
              <th style={{ textAlign: 'right' }}>金額</th>
            </tr>
          </thead>
          <tbody>
            {arAging.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                  暫無逾期帳款
                </td>
              </tr>
            ) : (
              arAging.map((row, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{row.customer_name}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                    {row.days_overdue > 0 ? `${row.days_overdue} 天` : '—'}
                  </td>
                  <td>
                    <span className={`badge ${
                      row.bucket === 'current' ? 'badge-success'
                      : row.bucket === '30' ? 'badge-warning'
                      : row.bucket === '60' ? 'badge-orange'
                      : 'badge-danger'
                    }`}>
                      {{
                        current: '未逾期', '30': '逾期 1-30 天', '60': '逾期 31-60 天',
                        '90': '逾期 61-90 天', '90plus': '逾期 90+ 天',
                      }[row.bucket] ?? row.bucket}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600,
                    color: row.bucket === '90plus' ? 'var(--danger)' : undefined,
                  }}>
                    {formatCents(row.amount_cents)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <button className="btn btn-sm btn-ghost" onClick={() => exportARAgingCsv(arAging)}>
        ⬇ 匯出 AR 帳齡 CSV
      </button>
    </div>
  );
}

// ─── Main Client Component ─────────────────────────────────────────────────

export default function FinancialsClient() {
  const [period, setPeriod] = useState(() => new Date().toISOString().slice(0, 7));
  const [tab, setTab] = useState<TabId>('pnl');
  const [data, setData] = useState<FinancialsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeResult, setCloseResult] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await getFinancials({ period, months: 12 });
    if (result.error) {
      setError(result.error.message);
    } else if (result.data) {
      setData(result.data);
    }
    setLoading(false);
  }, [period]);

  // Initial fetch + re-fetch on period change
  useState(() => { fetchData(); });

  const TABS: { id: TabId; label: string }[] = [
    { id: 'pnl', label: 'P&L 損益表' },
    { id: 'trial-balance', label: '試算表' },
    { id: 'balance-sheet', label: '資產負債表' },
    { id: 'ar-aging', label: 'AR 帳齡' },
  ];

  const handleClosePeriod = async () => {
    setClosing(true);
    const result = await closePeriod(period);
    setClosing(false);
    setShowCloseModal(false);
    if (result.error) {
      setCloseResult(`結帳失敗：${result.error.message}`);
    } else {
      setCloseResult(`期間 ${period} 已成功結帳`);
      fetchData();
    }
    setTimeout(() => setCloseResult(null), 5000);
  };

  const periodStatus = data?.periodStatus ?? 'open';

  return (
    <>
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h1 className="page-title">📈 財務報表</h1>
          <p className="page-subtitle">實時驅動自 Supabase 會計視圖</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Period status badge */}
          <PeriodBadge status={periodStatus} />

          {/* Period selector */}
          <input
            type="month"
            value={period}
            onChange={e => setPeriod(e.target.value)}
            className="form-input"
            style={{ width: 'auto' }}
          />

          {/* Refresh */}
          <button className="btn btn-secondary btn-sm" onClick={fetchData} disabled={loading}>
            {loading ? '載入中...' : '↻ 刷新'}
          </button>

          {/* Export P&L */}
          {data && (
            <button
              className="btn btn-sm btn-ghost"
              onClick={() => exportPnLCsv(data.monthlyPnL, data.summary as unknown as Array<{ label: string; amount_cents: number }>, period)}
            >
              ⬇ 匯出 P&L
            </button>
          )}

          {/* Period close */}
          {periodStatus === 'open' && (
            <button
              className="btn btn-sm btn-danger"
              onClick={() => setShowCloseModal(true)}
            >
              🔒 月結
            </button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div style={{
          padding: '0.75rem 1rem', marginBottom: '1rem',
          background: 'var(--danger-light)', color: 'var(--danger-text)',
          borderRadius: 'var(--radius)', border: '1px solid var(--danger)',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Success toast */}
      {closeResult && (
        <div style={{
          padding: '0.75rem 1rem', marginBottom: '1rem',
          background: 'var(--success-light)', color: 'var(--success-text)',
          borderRadius: 'var(--radius)', border: '1px solid var(--success)',
        }}>
          ✓ {closeResult}
        </div>
      )}

      {/* Summary cards */}
      {loading ? (
        <SkeletonStats count={3} />
      ) : data ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <StatCard
            label="收入"
            value={formatCents(data.summary.totalRevenueCents)}
            accent="var(--success)"
          />
          <StatCard
            label="支出"
            value={formatCents(data.summary.totalExpenseCents)}
            accent="var(--danger)"
          />
          <StatCard
            label="淨利潤"
            value={formatCents(data.summary.netProfitCents)}
            accent={data.summary.netProfitCents >= 0 ? 'var(--primary)' : 'var(--danger)'}
          />
          <StatCard
            label="逾期帳款"
            value={formatCents(data.arAging.reduce((s, r) => s + r.amount_cents, 0))}
            accent={data.arAging.length > 0 ? 'var(--warning)' : 'var(--success)'}
          />
        </div>
      ) : null}

      {/* Tab navigation */}
      <div style={{
        display: 'flex', borderBottom: '1px solid var(--border)',
        marginBottom: '1.5rem', overflowX: 'auto',
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`tab-btn ${tab === t.id ? 'active' : ''}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {loading ? (
        <SkeletonTable rows={6} cols={5} />
      ) : data ? (
        <>
          {tab === 'pnl' && <PnLTab data={data} />}
          {tab === 'trial-balance' && <TrialBalanceTab data={data} />}
          {tab === 'balance-sheet' && <BalanceSheetTab data={data} />}
          {tab === 'ar-aging' && <ARAgingTab data={data} period={period} />}
        </>
      ) : !error ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
          選擇月份後點擊「刷新」載入資料
        </div>
      ) : null}

      {/* Close Period Modal */}
      <ConfirmModal
        open={showCloseModal}
        title={`月結：${period}`}
        body={`確定要結帳嗎？結帳後該期間的分錄將被鎖定，無法再修改。`}
        confirmLabel="確認結帳"
        cancelLabel="取消"
        variant="danger"
        loading={closing}
        onConfirm={handleClosePeriod}
        onCancel={() => setShowCloseModal(false)}
      />
    </>
  );
}
