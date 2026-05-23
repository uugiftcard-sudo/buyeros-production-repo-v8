'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { formatDate, getBuyers, type Buyer } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

const STATUS_OPTIONS = [
  { value: '', label: '全部狀態' },
  { value: 'active', label: '啟用中' },
  { value: 'inactive', label: '停用' },
  { value: 'pending_kyc', label: '待 KYC' },
  { value: 'suspended', label: '停權' },
];

function BuyerStatCard({
  label, value, accent,
}: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="stat-card" style={{ ['--stat-accent' as string]: accent ?? '#4f46e5' }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function statusBadgeClass(status: string) {
  if (status === 'active') return 'badge-completed';
  if (status === 'inactive') return 'badge-cancelled';
  if (status === 'pending_kyc') return 'badge-pending';
  if (status === 'suspended') return 'badge-failed';
  return 'badge-pending';
}

function statusLabel(status: string) {
  return STATUS_OPTIONS.find(o => o.value === status)?.label ?? status;
}

export default function BuyersPage() {
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchBuyers = async () => {
    setLoading(true);
    try {
      const result = await getBuyers();
      setBuyers(result.data ?? []);
    } catch { /* silent */ }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchBuyers(); }, []);

  const filtered = statusFilter ? buyers.filter(b => b.status === statusFilter) : buyers;
  const activeCount = buyers.filter(b => b.status === 'active').length;
  const pendingKyc = buyers.filter(b => b.status === 'pending_kyc').length;
  const avgRating = buyers.filter(b => b.rating_avg).length > 0
    ? (buyers.reduce((s, b) => s + (b.rating_avg ?? 0), 0) / buyers.filter(b => b.rating_avg).length).toFixed(1)
    : '—';

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">🛒 買手管理</h1>
            <p className="page-subtitle">買手資料、評分與結算狀態</p>
          </div>
          <div className="page-header-right">
            <button className="btn btn-primary btn-sm">+ 新增買手</button>
          </div>
        </div>

        {/* Stats */}
        <div className="stats-grid">
          <BuyerStatCard label="總買手" value={buyers.length} accent="#4f46e5" />
          <BuyerStatCard label="啟用中" value={activeCount} accent="#059669" />
          <BuyerStatCard label="平均評分" value={`${avgRating} ⭐`} accent="#d97706" />
          <BuyerStatCard label="待 KYC" value={pendingKyc} accent="#dc2626" />
        </div>

        {/* Filter */}
        <div className="filter-bar">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="form-select"
          >
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            {filtered.length} 結果
          </span>
        </div>

        {/* Table */}
        <div className="table-wrap">
          {loading ? (
            <div className="loading">載入中...</div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🛒</div>
              <h3>暫無買手記錄</h3>
              <p>新增第一位買手以開始使用</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>買手名稱</th>
                  <th>電話</th>
                  <th>狀態</th>
                  <th>評分</th>
                  <th>佣金率</th>
                  <th>建立日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(b => (
                  <tr key={b.id}>
                    <td>
                      <Link href={`/buyers/${b.id}`} style={{ fontWeight: 600, color: 'var(--text)', textDecoration: 'none' }}
                        onMouseEnter={e => (e.currentTarget.style.color = 'var(--primary)')}
                        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text)')}
                      >
                        {b.display_name}
                      </Link>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{b.phone ?? '—'}</td>
                    <td>
                      <span className={`badge ${statusBadgeClass(b.status)}`}>
                        {statusLabel(b.status)}
                      </span>
                    </td>
                    <td>
                      {b.rating_avg ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <span>⭐</span>
                          <span style={{ fontWeight: 600 }}>{b.rating_avg.toFixed(1)}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.775rem' }}>({b.rating_count})</span>
                        </span>
                      ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </td>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', fontWeight: 550 }}>
                        {b.commission_rate != null ? `${(b.commission_rate * 100).toFixed(1)}%` : '—'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{formatDate(b.created_at)}</td>
                    <td>
                      <Link href={`/buyers/${b.id}`} className="btn btn-secondary btn-sm">查看</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
