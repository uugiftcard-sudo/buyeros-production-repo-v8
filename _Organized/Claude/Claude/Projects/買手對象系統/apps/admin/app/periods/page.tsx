'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';

interface AccountingPeriod {
  period: string;
  period_name?: string;
  status: 'open' | 'closed';
  opened_at: string | null;
  closed_at: string | null;
  opened_by: string | null;
  closed_by: string | null;
  notes: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

const EXAMPLE_PERIODS: AccountingPeriod[] = [
  { period: '2026-05', status: 'open',   opened_at: '2026-05-01T00:00:00Z', closed_at: null,            opened_by: 'admin', closed_by: null, notes: null },
  { period: '2026-04', status: 'closed', opened_at: '2026-04-01T00:00:00Z', closed_at: '2026-05-01T00:00:00Z', opened_by: 'admin', closed_by: 'admin', notes: null },
  { period: '2026-03', status: 'closed', opened_at: '2026-03-01T00:00:00Z', closed_at: '2026-04-01T00:00:00Z', opened_by: 'admin', closed_by: 'admin', notes: null },
  { period: '2026-02', status: 'closed', opened_at: '2026-02-01T00:00:00Z', closed_at: '2026-03-01T00:00:00Z', opened_by: 'admin', closed_by: 'admin', notes: null },
];

function formatPeriodLabel(period: string): string {
  const [year, month] = period.split('-');
  const d = new Date(parseInt(year), parseInt(month) - 1);
  return d.toLocaleDateString('zh-HK', { year: 'numeric', month: 'long' });
}

export default function PeriodsPage() {
  const [periods, setPeriods] = useState<AccountingPeriod[]>(EXAMPLE_PERIODS);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);
  const [tab, setTab] = useState<'list' | 'detail'>('list');
  const [periodFilter, setPeriodFilter] = useState('all');

  const currentYear = new Date().getFullYear();
  const [newYear, setNewYear] = useState(String(currentYear));
  const [newMonth, setNewMonth] = useState(String(new Date().getMonth() + 1).padStart(2, '0'));

  const handleCreatePeriod = async () => {
    const period = `${newYear}-${newMonth}`;
    if (periods.find(p => p.period === period)) { alert('該期間已存在'); return; }
    const lastDay = new Date(parseInt(newYear), parseInt(newMonth), 0).getDate();
    const { error } = await supabase.from('accounting_periods').insert({
      period,
      period_name: period,
      start_date: `${period}-01`,
      end_date: `${period}-${lastDay}`,
      status: 'open',
      opened_at: new Date().toISOString(),
      opened_by: null,
    });
    if (error) { alert('建立失敗：' + error.message); return; }
    setPeriods(prev => [{
      period, period_name: period, start_date: `${period}-01`,
      end_date: `${period}-${lastDay}`, status: 'open' as const,
      opened_at: new Date().toISOString(), closed_at: null,
      opened_by: null, closed_by: null, notes: null,
    }, ...prev]);
    alert(`期間 ${formatPeriodLabel(period)} 已建立`);
  };

  const handleReopenPeriod = async (period: string) => {
    if (!confirm(`確定要重新開放 ${formatPeriodLabel(period)}？`)) return;
    const { error } = await supabase.from('accounting_periods')
      .update({ status: 'open', closed_at: null, closed_by: null })
      .eq('period', period);
    if (error) { alert('失敗：' + error.message); return; }
    setPeriods(prev => prev.map(p => p.period === period ? {...p, status: 'open' as const, closed_at: null, closed_by: null} : p));
  };

  useEffect(() => {
    const fetchPeriods = async () => {
      setLoading(true);
      const { data, error } = await supabase
        .from('accounting_periods')
        .select('*')
        .order('period', { ascending: false })
        .limit(24);

      if (!error && data && data.length > 0) {
        setPeriods(data as AccountingPeriod[]);
      }
      setLoading(false);
    };
    fetchPeriods();
  }, []);

  const handleClosePeriod = async (period: string) => {
    if (!confirm(`確定要結算 ${formatPeriodLabel(period)} 的帳目嗎？\n\n結算後：\n• 該月的 journal entries 將被鎖定，不可修改\n• P&L 將被固化\n• 需要管理員確認方可重新打開`)) return;

    setClosing(true);
    try {
      const { error } = await supabase.rpc('close_accounting_period', { p_period: period });
      if (error) throw error;
      setPeriods(prev =>
        prev.map(p => p.period === period ? { ...p, status: 'closed' as const, closed_at: new Date().toISOString() } : p)
      );
      setTab('list');
    } catch (err) {
      alert(`結算失敗：${err instanceof Error ? err.message : '未知錯誤'}\n\n請確認 Supabase 中已執行會計層 migration，並有 close_accounting_period 函數。`);
    } finally {
      setClosing(false);
    }
  };

  const filteredPeriods = periods.filter(p => {
    if (periodFilter === 'open') return p.status === 'open';
    if (periodFilter === 'closed') return p.status === 'closed';
    return true;
  });

  const openCount = periods.filter(p => p.status === 'open').length;
  const closedCount = periods.filter(p => p.status === 'closed').length;

  const selectedPeriodData = selectedPeriod ? periods.find(p => p.period === selectedPeriod) : null;

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">📅 月結管理</h1>
          <p className="page-subtitle">管理會計期間的開帳與結帳</p>
        </div>

        {/* Summary */}
        <div className="stats-grid" style={{ marginBottom: '2rem' }}>
          <div className="stat-card">
            <div className="stat-label">当前开放期间</div>
            <div className="stat-value" style={{ color: 'var(--color-success)' }}>{openCount}</div>
            <div className="stat-sub">个期间</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">已结帐期间</div>
            <div className="stat-value">{closedCount}</div>
            <div className="stat-sub">个期间</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">最近结帐</div>
            <div className="stat-value" style={{ fontSize: '1rem', color: 'var(--color-text)' }}>
              {periods.find(p => p.status === 'closed')?.period
                ? formatPeriodLabel(periods.find(p => p.status === 'closed')!.period)
                : '—'}
            </div>
          </div>
        </div>

        {/* Monthly Revenue Bar Chart */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <span className="card-title">📊 月度收支趨勢</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>最近 4 期</span>
          </div>
          {(() => {
            const chartData = [
              { label: '2026-02', revenue: 11000, expenses: 7400 },
              { label: '2026-03', revenue: 16500, expenses: 10800 },
              { label: '2026-04', revenue: 13200, expenses: 8800 },
              { label: '2026-05', revenue: 9800,  expenses: 6500 },
            ];
            const maxVal = Math.max(...chartData.map(d => Math.max(d.revenue, d.expenses)));
            return (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', marginTop: '0.75rem' }}>
                {chartData.map(d => {
                  const revPct = (d.revenue / maxVal) * 100;
                  const expPct = (d.expenses / maxVal) * 100;
                  const net = d.revenue - d.expenses;
                  return (
                    <div key={d.label} style={{ textAlign: 'center' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', height: '120px', justifyContent: 'flex-end' }}>
                        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                          <div style={{ width: '32px', background: '#10b981', borderRadius: '2px 2px 0 0', height: `${revPct * 0.9}px`, minHeight: '4px' }} title={`收入 HK$${d.revenue.toLocaleString()}`} />
                          <div style={{ width: '32px', background: '#f87171', borderRadius: '0 0 2px 2px', height: `${expPct * 0.9}px`, minHeight: '4px' }} title={`支出 HK$${d.expenses.toLocaleString()}`} />
                        </div>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>{d.label}</div>
                      <div style={{ fontSize: '0.7rem', color: net >= 0 ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 600 }}>
                        {net >= 0 ? '+' : ''}{net >= 0 ? '' : ''}{net.toLocaleString()}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
          <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.75rem', fontSize: '0.75rem', justifyContent: 'center' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: 12, height: 12, background: '#10b981', borderRadius: 2, display: 'inline-block' }}></span>
              收入
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ width: 12, height: 12, background: '#f87171', borderRadius: 2, display: 'inline-block' }}></span>
              支出
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.5rem', textAlign: 'center' }}>
            💡 示例數據。執行會計 migration 後可顯示真實數據。
          </p>
        </div>

        {/* Filter */}
        <div className="filter-bar">
          <button
            className={`btn btn-sm ${periodFilter === 'all' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setPeriodFilter('all')}
          >
            全部 ({periods.length})
          </button>
          <button
            className={`btn btn-sm ${periodFilter === 'open' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setPeriodFilter('open')}
          >
            開放中 ({openCount})
          </button>
          <button
            className={`btn btn-sm ${periodFilter === 'closed' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setPeriodFilter('closed')}
          >
            已結帳 ({closedCount})
          </button>
        </div>

        {loading ? (
          <div className="loading">載入期間數據中...</div>
        ) : filteredPeriods.length === 0 ? (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">📅</div>
              <p>暫無會計期間記錄</p>
              <p style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: 'var(--color-text-muted)' }}>
                請先在 Supabase 中執行會計層 migration
              </p>
            </div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>期間</th>
                  <th>狀態</th>
                  <th>開始日期</th>
                  <th>結帳日期</th>
                  <th>結帳人</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredPeriods.map(p => (
                  <tr key={p.period} style={{ background: p.period === selectedPeriod ? '#f0f9ff' : undefined }}>
                    <td>
                      <span style={{ fontWeight: 600 }}>{formatPeriodLabel(p.period)}</span>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>{p.period}</div>
                    </td>
                    <td>
                      {p.status === 'open' ? (
                        <span className="badge badge-assigned">🟢 開放中</span>
                      ) : (
                        <span className="badge badge-completed">🔒 已結帳</span>
                      )}
                    </td>
                    <td>{p.opened_at ? new Date(p.opened_at).toLocaleDateString('zh-HK') : '—'}</td>
                    <td>{p.closed_at ? new Date(p.closed_at).toLocaleDateString('zh-HK') : '—'}</td>
                    <td>{p.closed_by ?? '—'}</td>
                    <td>
                      {p.status === 'open' && (
                        <button
                          className="btn btn-sm"
                          style={{ background: '#fef3c7', color: '#92400e', border: '1px solid #f59e0b', fontSize: '0.75rem' }}
                          onClick={() => handleClosePeriod(p.period)}
                          disabled={closing}
                        >
                          {closing ? '結算中...' : '🔒 結帳'}
                        </button>
                      )}
                      {p.status === 'closed' && (
                        <>
                          <button className="btn btn-sm btn-outline" style={{fontSize:'0.75rem'}} onClick={() => handleReopenPeriod(p.period)}>🔓 重新開帳</button>
                          <button
                            className="btn btn-sm btn-outline"
                            style={{ fontSize: '0.75rem' }}
                            onClick={() => { setSelectedPeriod(p.period); setTab('detail'); }}
                          >
                            📊 查看報表
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Period Detail */}
        {tab === 'detail' && selectedPeriodData && (
          <div style={{ marginTop: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
              <button className="btn btn-outline btn-sm" onClick={() => setTab('list')}>← 返回列表</button>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>{formatPeriodLabel(selectedPeriodData.period)} 財務報表</h2>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              {/* P&L */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">📈 損益表 (P&L)</span>
                </div>
                <div style={{ fontSize: '0.875rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)' }}>
                    <span style={{ color: 'var(--color-text-muted)' }}>收入</span>
                    <span style={{ fontFamily: 'monospace', color: 'var(--color-success)' }}>—</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)' }}>
                    <span style={{ color: 'var(--color-text-muted)' }}>支出</span>
                    <span style={{ fontFamily: 'monospace', color: 'var(--color-danger)' }}>—</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', fontWeight: 700 }}>
                    <span>淨利潤</span>
                    <span style={{ fontFamily: 'monospace' }}>—</span>
                  </div>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.75rem' }}>
                  💡 查詢：<code style={{ background: '#f3f4f6', padding: '0.1rem 0.3rem', borderRadius: '0.2rem' }}>SELECT * FROM v_pnl_summary WHERE period = '{selectedPeriodData.period}'</code>
                </p>
              </div>

              {/* Balance Sheet */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">🏦 資產負債表</span>
                </div>
                <div style={{ fontSize: '0.875rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)' }}>
                    <span style={{ color: 'var(--color-text-muted)' }}>總資產</span>
                    <span style={{ fontFamily: 'monospace' }}>—</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)' }}>
                    <span style={{ color: 'var(--color-text-muted)' }}>總負債</span>
                    <span style={{ fontFamily: 'monospace' }}>—</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', fontWeight: 700 }}>
                    <span>淨資產</span>
                    <span style={{ fontFamily: 'monospace' }}>—</span>
                  </div>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.75rem' }}>
                  💡 查詢：<code style={{ background: '#f3f4f6', padding: '0.1rem 0.3rem', borderRadius: '0.2rem' }}>SELECT * FROM v_balance_sheet('{selectedPeriodData.period}-31')</code>
                </p>
              </div>

              {/* Journal Summary */}
              <div className="card" style={{ gridColumn: '1 / -1' }}>
                <div className="card-header">
                  <span className="card-title">📒 Journal Entries 摘要</span>
                </div>
                <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                  該期間共有 <strong>—</strong> 筆記帳分錄，請在 Supabase Studio 中執行以下 SQL 查看詳情：
                </p>
                <div style={{ background: '#1f2937', color: '#d1d5db', fontFamily: 'monospace', fontSize: '0.8rem', padding: '1rem', borderRadius: '0.375rem', marginTop: '0.75rem', overflowX: 'auto' }}>
                  <p style={{ color: '#9ca3af' }}>-- 查看 {selectedPeriodData.period} 的所有分錄</p>
                  <p>SELECT je.id, je.entry_date, a.account_name, jl.debit_cents, jl.credit_cents</p>
                  <p style={{ color: '#6b7280' }}>FROM journal_entries je</p>
                  <p style={{ color: '#6b7280' }}>JOIN journal_lines jl ON jl.entry_id = je.id</p>
                  <p style={{ color: '#6b7280' }}>JOIN accounts a ON a.id = jl.account_id</p>
                  <p>WHERE je.period = '{selectedPeriodData.period}'</p>
                  <p style={{ color: '#6b7280' }}>ORDER BY je.entry_date;</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Open New Period */}
        <div className="card" style={{ marginTop: '1.5rem', border: '1px dashed var(--color-border)' }}>
          <div className="card-header">
            <span className="card-title">➕ 新增期間</span>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
            手動開啟一個新的會計期間（系統會在每月自動創建，通常無需手動操作）
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              className="form-select"
              style={{ width: 'auto', minWidth: '120px' }}
              value={newYear}
              onChange={e => setNewYear(e.target.value)}
            >
              <option value="" disabled>年份</option>
              {Array.from({ length: 3 }, (_, i) => String(currentYear - i)).map(y => <option key={y} value={y}>{y}年</option>)}
            </select>
            <select
              className="form-select"
              style={{ width: 'auto', minWidth: '100px' }}
              value={newMonth}
              onChange={e => setNewMonth(e.target.value)}
            >
              <option value="" disabled>月份</option>
              {Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')).map(m => (
                <option key={m} value={m}>{m}月</option>
              ))}
            </select>
            <button
              className="btn btn-outline"
              onClick={handleCreatePeriod}
            >
              開啟期間
            </button>
          </div>
        </div>

        {/* Help */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">ℹ️ 月結流程說明</span>
          </div>
          <div style={{ fontSize: '0.875rem', display: 'grid', gap: '0.75rem' }}>
            {[
              ['1', '核對試算表', '在 Supabase Studio 執行 SELECT * FROM v_trial_balance 確認借貸平衡'],
              ['2', '確認所有交易已入帳', '檢查 transactions 表，確保所有收付款已生成 journal entries'],
              ['3', '生成月度報表', '在 Supabase Studio 執行 SELECT * FROM v_pnl_summary WHERE period = \'YYYY-MM\''],
              ['4', '結帳確認', '在本頁按「結帳」，系統將鎖定該月 journal entries'],
              ['5', '開啟新期間', '結帳後自動創建下一期間（或按上方「新增期間」手動創建）'],
            ].map(([num, title, desc]) => (
              <div key={num} style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                <span style={{ minWidth: '1.5rem', height: '1.5rem', borderRadius: '50%', background: 'var(--color-primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 700, flexShrink: 0 }}>{num}</span>
                <div>
                  <strong>{title}</strong>
                  <p style={{ color: 'var(--color-text-muted)', marginTop: '0.2rem' }}>{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
