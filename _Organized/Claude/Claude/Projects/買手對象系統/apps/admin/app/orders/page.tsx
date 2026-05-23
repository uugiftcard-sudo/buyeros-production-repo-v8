'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getOrders, updateOrder, getOrder, formatCents, formatDate } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import type { Order } from '@/lib/api';

const STATUS_OPTIONS = [
  { value: '', label: '全部狀態' },
  { value: 'pending', label: '⏳ 待處理' },
  { value: 'assigned', label: '👤 已分配' },
  { value: 'in_procurement', label: '🛒 採購中' },
  { value: 'received', label: '📦 已到貨' },
  { value: 'delivered', label: '🚚 已配送' },
  { value: 'completed', label: '✅ 已完成' },
  { value: 'cancelled', label: '❌ 已取消' },
];

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchOrders = async (pageNum: number, status: string) => {
    setLoading(true);
    const { data } = await getOrders({ page: pageNum, status: status || undefined });
    setOrders(data?.data ?? []);
    setTotalPages(data?.meta?.pagination?.totalPages ?? 1);
    setLoading(false);
  };

  useEffect(() => {
    fetchOrders(page, statusFilter);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter]);

  const handleStatusChange = (orderId: string, newStatus: string) => {
    updateOrder(orderId, { status: newStatus }).then(() => {
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: newStatus } : o));
    });
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">📦 訂單管理</h1>
          <p className="page-subtitle">所有訂單</p>
        </div>

        <div className="filter-bar">
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
            className="form-select"
            style={{ width: 'auto', minWidth: '150px' }}
          >
            {STATUS_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <Link href="/orders/new" className="btn btn-primary">+ 新訂單</Link>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="loading">載入中...</div>
          ) : orders.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📦</div>
              <p>暫無訂單</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>訂單號</th>
                  <th>客戶</th>
                  <th>買手</th>
                  <th>狀態</th>
                  <th>總額</th>
                  <th>已付</th>
                  <th>尚欠</th>
                  <th>建立日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(order => (
                  <tr key={order.id}>
                    <td>
                      <Link href={`/orders/${order.id}`} style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                        {order.order_number}
                      </Link>
                    </td>
                    <td>{order.customer?.display_name ?? '—'}</td>
                    <td>{order.buyer?.display_name ?? <span style={{ color: 'var(--color-text-muted)' }}>未分配</span>}</td>
                    <td>
                      <select
                        value={order.status}
                        onChange={e => handleStatusChange(order.id, e.target.value)}
                        className={`badge badge-${order.status}`}
                        style={{ cursor: 'pointer', border: 'none', background: 'transparent', fontSize: 'inherit' }}
                      >
                        {STATUS_OPTIONS.filter(o => o.value).map(o => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </td>
                    <td style={{ fontWeight: 600 }}>{formatCents(order.total_amount_cents)}</td>
                    <td>{formatCents(order.deposit_paid_cents)}</td>
                    <td style={{ color: order.balance_due_cents > 0 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                      {formatCents(order.balance_due_cents)}
                    </td>
                    <td>{formatDate(order.created_at)}</td>
                    <td>
                      <Link href={`/orders/${order.id}`} className="btn btn-outline btn-sm">查看</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {totalPages > 1 && (
          <div className="pagination">
            <span>共 {totalPages} 頁</span>
            <div className="pagination-buttons">
              <button className="btn btn-outline btn-sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>← 上一頁</button>
              <span style={{ padding: '0.3rem 0.75rem' }}>第 {page} 頁</span>
              <button className="btn btn-outline btn-sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>下一頁 →</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
