'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getCustomers, formatCents } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

export default function NewOrderPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [customerId, setCustomerId] = useState('');
  const [notes, setNotes] = useState('');
  const [deliveryAddress, setDeliveryAddress] = useState('');
  const [sourceChannel, setSourceChannel] = useState('telegram');

  const [items, setItems] = useState<{ product_name: string; quantity: number; unit_price_cents: number }[]>([
    { product_name: '', quantity: 1, unit_price_cents: 0 },
  ]);

  const totalCents = items.reduce((sum, i) => sum + i.quantity * i.unit_price_cents, 0);

  const addItem = () => setItems(prev => [...prev, { product_name: '', quantity: 1, unit_price_cents: 0 }]);
  const removeItem = (i: number) => setItems(prev => prev.filter((_, idx) => idx !== i));
  const updateItem = (i: number, field: string, value: string | number) =>
    setItems(prev => prev.map((item, idx) => idx === i ? { ...item, [field]: value } : item));

  const handleSubmit = async () => {
    if (!customerId) { setError('請選擇客戶'); return; }
    setSubmitting(true);
    setError('');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
          'apikey': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        },
        body: JSON.stringify({
          customer_id: customerId,
          total_amount_cents: totalCents,
          notes,
          delivery_address: deliveryAddress,
          source_channel: sourceChannel,
          items: items.filter(i => i.product_name.trim() !== ''),
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error?.message ?? '建立失敗');
      router.push(`/orders/${json.data?.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '建立失敗');
      setSubmitting(false);
    }
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <Link href="/orders" style={{ color: 'var(--color-text-muted)', textDecoration: 'none', fontSize: '0.875rem' }}>← 訂單列表</Link>
          </div>
          <h1 className="page-title">📦 新建訂單</h1>
        </div>

        {/* Step indicator */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', fontSize: '0.875rem' }}>
          {['1. 基本資料', '2. 商品明細', '3. 確認'].map((label, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{
                width: '24px', height: '24px', borderRadius: '50%',
                background: step > i + 1 ? 'var(--color-success)' : step === i + 1 ? 'var(--color-primary)' : '#e5e7eb',
                color: step > i + 1 || step === i + 1 ? '#fff' : '#999',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: '0.75rem',
              }}>{step > i + 1 ? '✓' : i + 1}</span>
              <span style={{ color: step === i + 1 ? 'var(--color-text)' : 'var(--color-text-muted)' }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Step 1 */}
        {step === 1 && (
          <div className="card" style={{ maxWidth: '600px' }}>
            <div className="form-group">
              <label className="form-label">客戶 *</label>
              <input
                type="text"
                placeholder="🔍 搜尋客戶名稱或電話..."
                className="form-input"
                onChange={async e => {
                  setCustomerId('');
                  if (e.target.value.length < 2) return;
                  const { data } = await getCustomers({ search: e.target.value });
                  const list = data?.data ?? [];
                  if (list.length === 1) setCustomerId(list[0].id);
                }}
              />
              {customerId && <p style={{ fontSize: '0.8rem', color: 'var(--color-success)', marginTop: '0.25rem' }}>已選擇</p>}
            </div>
            <div className="form-group">
              <label className="form-label">配送地址</label>
              <textarea
                value={deliveryAddress}
                onChange={e => setDeliveryAddress(e.target.value)}
                className="form-textarea"
                rows={2}
                placeholder="九龍旺角亞皆老街8號朗豪坊..."
              />
            </div>
            <div className="form-group">
              <label className="form-label">訂單備註</label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="form-textarea"
                rows={2}
                placeholder="特殊要求、客戶偏好等..."
              />
            </div>
            <div className="form-group">
              <label className="form-label">訂單來源</label>
              <select value={sourceChannel} onChange={e => setSourceChannel(e.target.value)} className="form-select">
                <option value="telegram">Telegram</option>
                <option value="web">Web</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="phone">電話</option>
                <option value="walkin">親自到訪</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={() => { if (!customerId) { setError('請先搜尋並選擇客戶'); return; } setStep(2); setError(''); }}>
              下一步：商品明細 →
            </button>
          </div>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <div style={{ maxWidth: '800px' }}>
            <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: '1rem' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>商品名稱 *</th>
                    <th style={{ width: '80px' }}>數量</th>
                    <th style={{ width: '130px' }}>單價 (HKD)</th>
                    <th style={{ width: '130px' }}>小計</th>
                    <th style={{ width: '40px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, i) => (
                    <tr key={i}>
                      <td>
                        <input
                          type="text"
                          value={item.product_name}
                          onChange={e => updateItem(i, 'product_name', e.target.value)}
                          className="form-input"
                          placeholder="SK-II 神仙水 230ml"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={1}
                          value={item.quantity}
                          onChange={e => updateItem(i, 'quantity', parseInt(e.target.value) || 1)}
                          className="form-input"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={0}
                          value={item.unit_price_cents === 0 ? '' : item.unit_price_cents / 100}
                          onChange={e => updateItem(i, 'unit_price_cents', Math.round(parseFloat(e.target.value || '0') * 100))}
                          className="form-input"
                          placeholder="0.00"
                        />
                      </td>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>
                        {formatCents(item.quantity * item.unit_price_cents)}
                      </td>
                      <td>
                        {items.length > 1 && (
                          <button className="btn btn-outline btn-sm" onClick={() => removeItem(i)}>✕</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <button className="btn btn-outline" onClick={addItem}>+ 添加商品</button>
              <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                合計：<span style={{ color: 'var(--color-success)' }}>{formatCents(totalCents)}</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn btn-outline" onClick={() => setStep(1)}>← 上一步</button>
              <button className="btn btn-primary" onClick={() => setStep(3)}>下一步：確認 →</button>
            </div>
          </div>
        )}

        {/* Step 3 */}
        {step === 3 && (
          <div style={{ maxWidth: '600px' }}>
            <div className="card">
              <div className="card-header"><span className="card-title">✅ 確認訂單</span></div>
              <div style={{ display: 'grid', gap: '0.75rem', fontSize: '0.875rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>訂單總額</span>
                  <span style={{ fontWeight: 700, fontSize: '1.2rem' }}>{formatCents(totalCents)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>來源</span>
                  <span>{sourceChannel}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>商品數量</span>
                  <span>{items.filter(i => i.product_name.trim()).length} 件</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>配送地址</span>
                  <span>{deliveryAddress || '—'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>備註</span>
                  <span>{notes || '—'}</span>
                </div>
              </div>
            </div>
            {error && <div className="card" style={{ color: 'var(--color-danger)', marginTop: '0.5rem' }}>{error}</div>}
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
              <button className="btn btn-outline" onClick={() => setStep(2)}>← 修改</button>
              <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting}>
                {submitting ? '提交中...' : '✅ 確認建立訂單'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
