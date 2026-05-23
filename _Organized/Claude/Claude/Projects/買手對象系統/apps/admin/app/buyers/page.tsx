'use client';

import { useEffect, useState } from 'react';
import { formatDate } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

interface Buyer {
  id: string;
  display_name: string;
  phone: string | null;
  status: string;
  rating_avg: number;
  rating_count: number;
  commission_rate: number | null;
  created_at: string;
  notes: string | null;
}

const STATUS_OPTIONS = [
  { value: '', label: '全部狀態' },
  { value: 'active', label: '✅ 啟用中' },
  { value: 'inactive', label: '❌ 停用' },
  { value: 'pending_kyc', label: '⏳ 待 KYC' },
  { value: 'suspended', label: '⚠️ 停權' },
];

export default function BuyersPage() {
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchBuyers = async () => {
    setLoading(true);
    try {
      const url = new URL(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/dashboard/buyers`);
      const res = await fetch(url.toString(), {
        headers: {
          'Authorization': `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
          'apikey': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        },
      });
      const json = await res.json();
      if (!res.ok) return;
      setBuyers(json.data ?? []);
    } catch {
      // 靜默失敗，頁面保持空列表
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchBuyers(); }, []);

  const filtered = statusFilter
    ? buyers.filter(b => b.status === statusFilter)
    : buyers;

  const avgRating = buyers.length > 0
    ? (buyers.reduce((sum, b) => sum + (b.rating_avg ?? 0), 0) / buyers.filter(b => b.rating_avg).length).toFixed(1)
    : '—';

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">🛒 買手管理</h1>
          <p className="page-subtitle">買手資料、評分與結算狀態</p>
        </div>

        {/* Stats */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">總買手</div>
            <div className="stat-value">{buyers.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">啟用中</div>
            <div className="stat-value" style={{ color: 'var(--color-success)' }}>
              {buyers.filter(b => b.status === 'active').length}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">平均評分</div>
            <div className="stat-value">{avgRating} ⭐</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">待 KYC</div>
            <div className="stat-value" style={{ color: 'var(--color-warning)' }}>
              {buyers.filter(b => b.status === 'pending_kyc').length}
            </div>
          </div>
        </div>

        {/* Filter */}
        <div className="filter-bar">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="form-select"
            style={{ width: 'auto', minWidth: '150px' }}
          >
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="loading">載入中...</div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🛒</div>
              <p>暫無買手記錄</p>
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
                    <td style={{ fontWeight: 600 }}>{b.display_name}</td>
                    <td>{b.phone ?? '—'}</td>
                    <td>
                      <span className={`badge badge-${b.status === 'active' ? 'completed' : b.status === 'inactive' ? 'cancelled' : 'pending'}`}>
                        {STATUS_OPTIONS.find(o => o.value === b.status)?.label ?? b.status}
                      </span>
                    </td>
                    <td>
                      {b.rating_avg ? (
                        <span>⭐ {b.rating_avg.toFixed(1)} <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>({b.rating_count})</span></span>
                      ) : '—'}
                    </td>
                    <td style={{ fontFamily: 'monospace' }}>{b.commission_rate ? `${(b.commission_rate * 100).toFixed(1)}%` : '—'}</td>
                    <td>{formatDate(b.created_at)}</td>
                    <td>
                      <button className="btn btn-outline btn-sm">查看</button>
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
