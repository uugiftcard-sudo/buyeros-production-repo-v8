'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { getOrders, updateOrder, assignBuyer, formatCents, formatDate, getBuyers, exportOrdersCsv, batchUpdateOrders, batchAssignBuyer, type Order, type Buyer } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

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

const STATUS_BADGE: Record<string, string> = {
  pending: 'badge-pending',
  assigned: 'badge-assigned',
  in_procurement: 'badge-in_procurement',
  received: 'badge-received',
  delivered: 'badge-delivered',
  completed: 'badge-completed',
  cancelled: 'badge-cancelled',
};

function BatchActionBar({
  selectedCount,
  onAssign,
  onStatusChange,
  onCancel,
}: {
  selectedCount: number;
  onAssign: () => void;
  onStatusChange: () => void;
  onCancel: () => void;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.6rem',
      padding: '0.75rem 1rem',
      background: 'var(--primary-light)',
      borderRadius: 'var(--radius)',
      marginBottom: '1rem',
      border: '1px solid #c7d2fe',
    }}>
      <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--primary-dark)' }}>
        ✅ 已選擇 {selectedCount} 項
      </span>
      <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
        <button className="btn btn-primary btn-sm" onClick={onAssign}>📋 批量分配買手</button>
        <button className="btn btn-secondary btn-sm" onClick={onStatusChange}>🔄 批量更新狀態</button>
        <button className="btn btn-ghost btn-sm" onClick={onCancel}>取消選擇</button>
      </div>
    </div>
  );
}

function BuyerSelectModal({
  buyers, onAssign, onClose,
}: {
  buyers: Buyer[];
  onAssign: (buyerId: string) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState('');
  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">📋 分配買手</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="form-group">
            <label className="form-label">選擇買手</label>
            <select className="form-select" value={selected} onChange={e => setSelected(e.target.value)}>
              <option value="">— 請選擇 —</option>
              {buyers.filter(b => b.status === 'active').map(b => (
                <option key={b.id} value={b.id}>
                  {b.display_name} {b.phone ? `(${b.phone})` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={() => { if (selected) { onAssign(selected); onClose(); } }} disabled={!selected}>
            確認分配
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusSelectModal({
  currentStatus, onChange, onClose,
}: {
  currentStatus: string;
  onChange: (status: string) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(currentStatus);
  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">🔄 批量更新狀態</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="form-group">
            <label className="form-label">新狀態</label>
            <select className="form-select" value={selected} onChange={e => setSelected(e.target.value)}>
              {STATUS_OPTIONS.filter(o => o.value).map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={() => { onChange(selected); onClose(); }}>確認更新</button>
        </div>
      </div>
    </div>
  );
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [showBuyerModal, setShowBuyerModal] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [batchResult, setBatchResult] = useState<{ updated: number; failed: number } | null>(null);

  const fetchOrders = useCallback(async (pageNum: number, status: string) => {
    setLoading(true);
    const { data } = await getOrders({ page: pageNum, status: status || undefined });
    setOrders(data?.data ?? []);
    setTotal(data?.meta?.pagination?.total ?? 0);
    setTotalPages(data?.meta?.pagination?.totalPages ?? 1);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchOrders(page, statusFilter);
  }, [page, statusFilter, fetchOrders]);

  useEffect(() => {
    getBuyers().then(({ data }) => { if (data) setBuyers(data); });
  }, []);

  const handleStatusChange = (orderId: string, newStatus: string) => {
    updateOrder(orderId, { status: newStatus }).then(() => {
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: newStatus } : o));
    });
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === orders.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(orders.map(o => o.id)));
    }
  };

  const handleBatchAssign = async (buyerId: string) => {
    const ids = Array.from(selectedIds);
    const result = await batchAssignBuyer(ids, buyerId);
    setBatchResult(result.data ?? { updated: 0, failed: ids.length });
    if (result.data?.updated) {
      fetchOrders(page, statusFilter);
      setSelectedIds(new Set());
    }
  };

  const handleBatchStatus = async (status: string) => {
    const ids = Array.from(selectedIds);
    const result = await batchUpdateOrders(ids, { status } as Partial<Order>);
    setBatchResult(result.data ?? { updated: 0, failed: ids.length });
    if (result.data?.updated) {
      fetchOrders(page, statusFilter);
      setSelectedIds(new Set());
    }
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">📦 訂單管理</h1>
            <p className="page-subtitle">
              {total > 0 && <span>共 {total.toLocaleString()} 張訂單</span>}
            </p>
          </div>
          <div className="page-header-right">
            <button className="btn btn-secondary btn-sm" onClick={() => exportOrdersCsv({ status: statusFilter || undefined })}>
              📥 導出 CSV
            </button>
            <Link href="/orders/new" className="btn btn-primary">+ 新訂單</Link>
          </div>
        </div>

        {/* Batch action bar */}
        {selectedIds.size > 0 && (
          <BatchActionBar
            selectedCount={selectedIds.size}
            onAssign={() => setShowBuyerModal(true)}
            onStatusChange={() => setShowStatusModal(true)}
            onCancel={() => setSelectedIds(new Set())}
          />
        )}

        {/* Batch result */}
        {batchResult && (
          <div className={`alert ${batchResult.failed === 0 ? 'alert-success' : 'alert-warning'}`}
            style={{ marginBottom: '1rem' }}
          >
            ✅ 成功更新 {batchResult.updated} 項
            {batchResult.failed > 0 && `，失敗 ${batchResult.failed} 項`}
            <button onClick={() => setBatchResult(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
          </div>
        )}

        {/* Filters */}
        <div className="filter-bar">
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
            className="form-select"
          >
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <input
            type="text"
            className="form-input"
            placeholder="🔍 搜尋訂單號 / 客戶名稱..."
            style={{ maxWidth: 260 }}
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Table */}
        <div className="table-wrap">
          {loading ? (
            <div className="loading">載入中...</div>
          ) : orders.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📦</div>
              <h3>暫無訂單</h3>
              <p>建立第一張訂單以開始使用</p>
              <Link href="/orders/new" className="btn btn-primary" style={{ marginTop: '1rem' }}>+ 新訂單</Link>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 40 }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.size === orders.length && orders.length > 0}
                      onChange={toggleAll}
                      style={{ width: 16, height: 16, cursor: 'pointer', accentColor: '#4f46e5' }}
                    />
                  </th>
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
                {orders.map(order => {
                  const isSelected = selectedIds.has(order.id);
                  const searchLower = search.toLowerCase();
                  const matchesSearch = !search ||
                    order.order_number.toLowerCase().includes(searchLower) ||
                    order.customer?.display_name?.toLowerCase().includes(searchLower) ||
                    order.buyer?.display_name?.toLowerCase().includes(searchLower);

                  if (!matchesSearch) return null;

                  return (
                    <tr
                      key={order.id}
                      style={isSelected ? { background: '#eef2ff' } : undefined}
                    >
                      <td>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(order.id)}
                          style={{ width: 16, height: 16, cursor: 'pointer', accentColor: '#4f46e5' }}
                        />
                      </td>
                      <td>
                        <Link
                          href={`/orders/${order.id}`}
                          style={{ fontFamily: 'monospace', fontSize: '0.85rem', fontWeight: 600, color: 'var(--primary)' }}
                        >
                          {order.order_number}
                        </Link>
                      </td>
                      <td style={{ fontWeight: 500 }}>{order.customer?.display_name ?? '—'}</td>
                      <td>
                        {order.buyer?.display_name
                          ? <span style={{ fontWeight: 500 }}>{order.buyer.display_name}</span>
                          : <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>未分配</span>}
                      </td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[order.status] ?? ''}`}>
                          {STATUS_OPTIONS.find(o => o.value === order.status)?.label?.replace(/^[^\s]+\s/, '') ?? order.status}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>
                        {formatCents(order.total_amount_cents)}
                      </td>
                      <td style={{ fontFamily: 'monospace' }}>{formatCents(order.deposit_paid_cents)}</td>
                      <td style={{
                        fontFamily: 'monospace',
                        color: order.balance_due_cents > 0 ? 'var(--danger)' : 'var(--success)',
                        fontWeight: 500,
                      }}>
                        {formatCents(order.balance_due_cents)}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                        {formatDate(order.created_at)}
                      </td>
                      <td>
                        <Link href={`/orders/${order.id}`} className="btn btn-secondary btn-sm">查看</Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <span>第 {page} / {totalPages} 頁，共 {total.toLocaleString()} 張</span>
            <div className="pagination-buttons">
              <button className="btn btn-outline btn-sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>←</button>
              <button className="btn btn-outline btn-sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>→</button>
            </div>
          </div>
        )}
      </main>

      {showBuyerModal && (
        <BuyerSelectModal
          buyers={buyers}
          onAssign={handleBatchAssign}
          onClose={() => setShowBuyerModal(false)}
        />
      )}

      {showStatusModal && (
        <StatusSelectModal
          currentStatus="pending"
          onChange={handleBatchStatus}
          onClose={() => setShowStatusModal(false)}
        />
      )}
    </div>
  );
}
