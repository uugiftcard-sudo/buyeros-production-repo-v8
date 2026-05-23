'use client';

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from 'react';
import { getTransactions, formatCents, formatDate, downloadCsv } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import type { Transaction } from '@/lib/api';

const TYPE_OPTIONS = [
  { value: '', label: '全部類型' },
  { value: 'deposit', label: '💰 定金' },
  { value: 'balance', label: '💵 尾款' },
  { value: 'payment', label: '💳 付款' },
  { value: 'commission', label: '🏧 佣金' },
  { value: 'refund', label: '↩️ 退款' },
];

const STATUS_OPTIONS = [
  { value: '', label: '全部狀態' },
  { value: 'pending', label: '⏳ 待確認' },
  { value: 'confirmed', label: '✅ 已確認' },
  { value: 'failed', label: '❌ 失敗' },
  { value: 'reversed', label: '↩️ 已逆轉' },
];

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchTransactions = async (pageNum: number) => {
    setLoading(true);
    const { data } = await getTransactions({
      page: pageNum,
      type: typeFilter || undefined,
      status: statusFilter || undefined,
    });
    setTransactions(data?.data ?? []);
    setTotalPages(data?.meta?.pagination?.totalPages ?? 1);
    setLoading(false);
  };

  useEffect(() => {
    fetchTransactions(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, typeFilter, statusFilter]);

  const totalCents = transactions.reduce((sum, t) => t.status === 'confirmed' ? sum + t.amount_cents : sum, 0);

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">💰 交易記錄</h1>
            <p className="page-subtitle">
              {transactions.length > 0 ? `已確認交易合計：${formatCents(totalCents)}` : '所有收款、付款、佣金記錄'}
            </p>
          </div>
          <div className="page-header-right">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (transactions.length === 0) return;
                downloadCsv(
                  transactions.map(t => ({
                    交易號: t.transaction_number,
                    訂單: t.order_id ?? '',
                    客戶: t.customer_id ?? '',
                    類型: t.type,
                    金額: formatCents(t.amount_cents),
                    貨幣: t.currency,
                    方式: t.payment_method ?? '',
                    狀態: t.status,
                    付款日期: t.paid_at ? formatDate(t.paid_at) : '',
                    建立日期: formatDate(t.created_at),
                  })),
                  'transactions'
                );
              }}
            >
              📥 導出 CSV
            </button>
          </div>
        </div>

        {/* Filter */}
        <div className="filter-bar">
          <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); }} className="form-select" style={{ width: 'auto', minWidth: '140px' }}>
            {TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }} className="form-select" style={{ width: 'auto', minWidth: '140px' }}>
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="loading">載入中...</div>
          ) : transactions.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">💰</div>
              <p>暫無交易記錄</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>交易號</th>
                  <th>訂單</th>
                  <th>客戶</th>
                  <th>類型</th>
                  <th>金額</th>
                  <th>方式</th>
                  <th>狀態</th>
                  <th>付款日期</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map(txn => (
                  <tr key={txn.id}>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{txn.transaction_number}</span>
                    </td>
                    <td>
                      {txn.order_id
                        ? <span style={{ fontSize: '0.8rem', color: 'var(--color-primary)' }}>{txn.order_id.slice(0, 8)}...</span>
                        : '—'}
                    </td>
                    <td>{txn.customer_id ? <span style={{ fontSize: '0.8rem' }}>{txn.customer_id.slice(0, 8)}...</span> : '—'}</td>
                    <td>
                      <span className={`badge badge-${txn.type === 'deposit' ? 'in_procurement' : txn.type === 'commission' ? 'assigned' : 'pending'}`}>
                        {TYPE_OPTIONS.find(o => o.value === txn.type)?.label ?? txn.type}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontWeight: 600, color: txn.type === 'refund' ? 'var(--color-danger)' : 'var(--color-success)' }}>
                      {txn.type === 'refund' ? '-' : '+'}{formatCents(txn.amount_cents)}
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{txn.payment_method ?? '—'}</td>
                    <td>
                      <span className={`badge badge-${txn.status === 'confirmed' ? 'completed' : txn.status === 'failed' ? 'cancelled' : 'pending'}`}>
                        {STATUS_OPTIONS.find(o => o.value === txn.status)?.label ?? txn.status}
                      </span>
                    </td>
                    <td>{txn.paid_at ? formatDate(txn.paid_at) : '—'}</td>
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
