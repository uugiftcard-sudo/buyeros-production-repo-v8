'use client';

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from 'react';
import { getRefunds, updateRefund, formatCents, formatDate } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import type { Refund } from '@/lib/api';

const STATUS_OPTIONS = [
  { value: '', label: '全部狀態' },
  { value: 'pending', label: '⏳ 待審批' },
  { value: 'approved', label: '👍 已批准' },
  { value: 'processing', label: '🔄 處理中' },
  { value: 'completed', label: '✅ 已完成' },
  { value: 'rejected', label: '❌ 已拒絕' },
];

export default function RefundsPage() {
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchRefunds = async (pageNum: number) => {
    setLoading(true);
    const { data } = await getRefunds({
      page: pageNum,
      status: statusFilter || undefined,
    });
    setRefunds(data?.data ?? []);
    setTotalPages(data?.meta?.pagination?.totalPages ?? 1);
    setLoading(false);
  };

  useEffect(() => {
    fetchRefunds(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter]);

  const handleAction = async (id: string, newStatus: string) => {
    const { data } = await updateRefund(id, { status: newStatus });
    if (data) setRefunds(prev => prev.map(r => r.id === id ? { ...r, status: newStatus } : r));
  };

  const pendingCount = refunds.filter(r => r.status === 'pending').length;

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">↩️ 退款管理</h1>
          <p className="page-subtitle">退款申請審批與處理</p>
        </div>

        {/* Alert */}
        {pendingCount > 0 && (
          <div className="card" style={{ background: '#fef3c7', border: '1px solid #f59e0b', marginBottom: '1rem' }}>
            <span style={{ color: '#92400e', fontWeight: 600 }}>⚠️ 有 {pendingCount} 筆退款待審批</span>
          </div>
        )}

        {/* Filter */}
        <div className="filter-bar">
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
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
          ) : refunds.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">↩️</div>
              <p>暫無退款記錄</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>退款號</th>
                  <th>客戶</th>
                  <th>金額</th>
                  <th>原因</th>
                  <th>狀態</th>
                  <th>申請日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {refunds.map(r => (
                  <tr key={r.id}>
                    <td><span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.refund_number}</span></td>
                    <td>{r.customer?.display_name ?? '—'}</td>
                    <td style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--color-danger)' }}>
                      -{formatCents(r.amount_cents)}
                    </td>
                    <td style={{ fontSize: '0.8rem', maxWidth: '200px' }}>
                      {r.reason ? (
                        <span>
                          <span className="badge badge-pending" style={{ marginRight: '0.25rem' }}>{r.reason}</span>
                          {r.reason_detail && <span style={{ color: 'var(--color-text-muted)' }}>{r.reason_detail}</span>}
                        </span>
                      ) : '—'}
                    </td>
                    <td>
                      <span className={`badge badge-${r.status === 'completed' ? 'completed' : r.status === 'rejected' ? 'cancelled' : r.status === 'pending' ? 'pending' : 'in_procurement'}`}>
                        {STATUS_OPTIONS.find(o => o.value === r.status)?.label ?? r.status}
                      </span>
                    </td>
                    <td>{r.created_at ? formatDate(r.created_at) : '—'}</td>
                    <td>
                      {r.status === 'pending' && (
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          <button
                            className="btn btn-sm"
                            style={{ background: '#d1fae5', color: '#065f46', border: '1px solid #6ee7b7', fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                            onClick={() => handleAction(r.id, 'approved')}
                          >批准</button>
                          <button
                            className="btn btn-sm"
                            style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5', fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                            onClick={() => handleAction(r.id, 'rejected')}
                          >拒絕</button>
                        </div>
                      )}
                      {r.status === 'approved' && (
                        <button className="btn btn-sm" style={{ background: '#ede9fe', color: '#5b21b6', border: '1px solid #c4b5fd', fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleAction(r.id, 'processing')}>處理中</button>
                      )}
                      {r.status === 'processing' && (
                        <button className="btn btn-sm" style={{ background: '#d1fae5', color: '#065f46', border: '1px solid #6ee7b7', fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleAction(r.id, 'completed')}>已完成</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <span>第 {page} / {totalPages} 頁</span>
            <div className="pagination-buttons">
              <button className="btn btn-outline btn-sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>← 上一頁</button>
              <button className="btn btn-outline btn-sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>下一頁 →</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
