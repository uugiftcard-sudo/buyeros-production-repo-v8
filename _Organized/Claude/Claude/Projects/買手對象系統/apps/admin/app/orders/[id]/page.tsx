'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getOrder, updateOrder, formatCents, formatDate } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import type { Order } from '@/lib/api';

const STATUS_OPTIONS = [
  { value: 'pending', label: '⏳ 待處理' },
  { value: 'assigned', label: '👤 已分配' },
  { value: 'in_procurement', label: '🛒 採購中' },
  { value: 'received', label: '📦 已到貨' },
  { value: 'delivered', label: '🚚 已配送' },
  { value: 'completed', label: '✅ 已完成' },
  { value: 'cancelled', label: '❌ 已取消' },
];

const ITEM_STATUS_OPTIONS = [
  { value: 'pending', label: '⏳ 待採購' },
  { value: 'procured', label: '✅ 已購入' },
  { value: 'out_of_stock', label: '❌ 缺貨' },
  { value: 'substituted', label: '🔄 已替代' },
];

export default function OrderDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<'info' | 'items' | 'payments'>('info');

  useEffect(() => {
    if (!id) return;
    getOrder(id).then(({ data, error }) => {
      if (error) setError(error.message);
      else setOrder(data ?? null);
    }).finally(() => setLoading(false));
  }, [id]);

  const handleStatusChange = async (newStatus: string) => {
    if (!order) return;
    setSaving(true);
    const { data } = await updateOrder(order.id, { status: newStatus });
    if (data) setOrder({ ...order, status: newStatus });
    setSaving(false);
  };

  if (loading) return (
    <div className="app-shell"><Sidebar /><main className="main-content"><div className="loading">載入中...</div></main></div>
  );
  if (error) return (
    <div className="app-shell"><Sidebar /><main className="main-content">
      <div className="card" style={{ color: 'var(--color-danger)' }}>載入失敗：{error}</div>
    </main></div>
  );
  if (!order) return (
    <div className="app-shell"><Sidebar /><main className="main-content"><div className="empty-state">找不到訂單</div></main></div>
  );

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <Link href="/orders" style={{ color: 'var(--color-text-muted)', textDecoration: 'none', fontSize: '0.875rem' }}>← 訂單列表</Link>
            </div>
            <h1 className="page-title" style={{ fontFamily: 'monospace' }}>{order.order_number}</h1>
            <p className="page-subtitle">建立於 {formatDate(order.created_at)}</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <select
              value={order.status}
              onChange={e => handleStatusChange(e.target.value)}
              disabled={saving}
              className={`badge badge-${order.status}`}
              style={{ padding: '0.5rem 1rem', fontSize: '0.9rem', cursor: 'pointer' }}
            >
              {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--color-border)' }}>
          {(['info', 'items', 'payments'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: '0.5rem 1rem',
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: tab === t ? 600 : 400,
                borderBottom: tab === t ? '2px solid var(--color-primary)' : '2px solid transparent',
                color: tab === t ? 'var(--color-primary)' : 'var(--color-text-muted)',
                marginBottom: '-1px',
              }}
            >
              {t === 'info' ? '📋 基本資料' : t === 'items' ? '📦 商品明細' : '💳 付款記錄'}
            </button>
          ))}
        </div>

        {/* Info Tab */}
        {tab === 'info' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <div className="card">
              <div className="card-header"><span className="card-title">👤 客戶</span></div>
              <div style={{ fontSize: '0.875rem' }}>
                <p style={{ fontWeight: 600 }}>{order.customer?.display_name ?? '—'}</p>
                <p style={{ color: 'var(--color-text-muted)' }}>{order.customer?.phone ?? ''}</p>
              </div>
            </div>
            <div className="card">
              <div className="card-header"><span className="card-title">🛒 買手</span></div>
              {order.buyer?.display_name ? (
                <div style={{ fontSize: '0.875rem' }}>
                  <p style={{ fontWeight: 600 }}>{order.buyer.display_name}</p>
                  <p style={{ color: 'var(--color-text-muted)' }}>
                    {order.assigned_at ? `分配於 ${formatDate(order.assigned_at)}` : ''}
                  </p>
                </div>
              ) : (
                <p style={{ color: 'var(--color-text-muted)' }}>未分配</p>
              )}
            </div>
            <div className="card">
              <div className="card-header"><span className="card-title">💰 金額</span></div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.875rem' }}>
                <div><div style={{ color: 'var(--color-text-muted)' }}>訂單總額</div><div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{formatCents(order.total_amount_cents)}</div></div>
                <div><div style={{ color: 'var(--color-text-muted)' }}>已付</div><div style={{ fontWeight: 600, color: 'var(--color-success)' }}>{formatCents(order.deposit_paid_cents)}</div></div>
                <div><div style={{ color: 'var(--color-text-muted)' }}>尚欠</div><div style={{ fontWeight: 600, color: order.balance_due_cents > 0 ? 'var(--color-danger)' : 'var(--color-success)', fontSize: '1.1rem' }}>{formatCents(order.balance_due_cents)}</div></div>
                <div><div style={{ color: 'var(--color-text-muted)' }}>配送地址</div><div>{order.delivery_address ?? '—'}</div></div>
              </div>
            </div>
            <div className="card">
              <div className="card-header"><span className="card-title">📝 備註</span></div>
              <p style={{ fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>{order.notes ?? '—'}</p>
            </div>
          </div>
        )}

        {/* Items Tab */}
        {tab === 'items' && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>商品名稱</th>
                  <th>URL</th>
                  <th>數量</th>
                  <th>單價</th>
                  <th>小計</th>
                  <th>狀態</th>
                </tr>
              </thead>
              <tbody>
                {(order.items as Array<{ id: string; product_name: string; product_url?: string; quantity: number; unit_price_cents: number; status: string }> | undefined)?.map(item => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 500 }}>{item.product_name}</td>
                    <td>
                      {item.product_url
                        ? <a href={item.product_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-primary)', fontSize: '0.8rem' }}>連結</a>
                        : '—'}
                    </td>
                    <td>{item.quantity}</td>
                    <td style={{ fontFamily: 'monospace' }}>{formatCents(item.unit_price_cents)}</td>
                    <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{formatCents(item.quantity * item.unit_price_cents)}</td>
                    <td>
                      <span className={`badge badge-${item.status === 'procured' ? 'completed' : 'pending'}`}>
                        {ITEM_STATUS_OPTIONS.find(s => s.value === item.status)?.label ?? item.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {(!order.items || order.items.length === 0) && (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>暫無商品明細</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Payments Tab */}
        {tab === 'payments' && (
          <div className="card">
            <div className="card-header"><span className="card-title">💳 付款記錄</span></div>
            <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>此功能需要 Supabase Storage 整合，詳見 TODO.md P2.3</p>
          </div>
        )}
      </main>
    </div>
  );
}
