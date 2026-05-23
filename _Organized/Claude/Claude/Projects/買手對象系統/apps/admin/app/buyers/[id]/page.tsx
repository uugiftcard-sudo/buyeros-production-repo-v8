'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { formatDate } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

interface BuyerDetail {
  id: string;
  display_name: string;
  phone: string | null;
  status: string;
  rating_avg: number;
  rating_count: number;
  commission_rate: number | null;
  created_at: string;
  notes: string | null;
  bank_name?: string | null;
  bank_account?: string | null;
  bank_account_holder?: string | null;
}

const STATUS_OPTIONS: Record<string, { label: string; color: string }> = {
  active:      { label: '✅ 啟用中',  color: 'var(--color-success)' },
  inactive:   { label: '❌ 停用',    color: 'var(--color-text-muted)' },
  pending_kyc:{ label: '⏳ 待 KYC',  color: 'var(--color-warning)' },
  suspended:  { label: '⚠️ 停權',    color: 'var(--color-danger)' },
};

export default function BuyerDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [buyer, setBuyer] = useState<BuyerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    const fetchBuyer = async () => {
      setLoading(true);
      try {
        const url = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/dashboard/buyers/${id}`;
        const res = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
            'apikey': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
          },
        });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error?.message ?? '載入失敗');
        setBuyer(json.data ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '未知錯誤');
      } finally {
        setLoading(false);
      }
    };
    fetchBuyer();
  }, [id]);

  if (loading) return (
    <div className="app-shell"><Sidebar /><main className="main-content"><div className="loading">載入中...</div></main></div>
  );
  if (error) return (
    <div className="app-shell"><Sidebar /><main className="main-content">
      <div className="card" style={{ color: 'var(--color-danger)' }}>載入失敗：{error}</div>
    </main></div>
  );
  if (!buyer) return (
    <div className="app-shell"><Sidebar /><main className="main-content"><div className="empty-state">找不到買手</div></main></div>
  );

  const statusInfo = STATUS_OPTIONS[buyer.status] ?? { label: buyer.status, color: 'var(--color-text-muted)' };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <Link href="/buyers" style={{ color: 'var(--color-text-muted)', textDecoration: 'none', fontSize: '0.875rem' }}>← 買手列表</Link>
            </div>
            <h1 className="page-title">{buyer.display_name}</h1>
            <p className="page-subtitle">買手 #{id.slice(0, 8)} · 建立於 {formatDate(buyer.created_at)}</p>
          </div>
          <span style={{
            padding: '0.5rem 1rem',
            borderRadius: '0.5rem',
            fontWeight: 600,
            color: statusInfo.color,
            border: `1px solid ${statusInfo.color}`,
            fontSize: '0.875rem',
          }}>
            {statusInfo.label}
          </span>
        </div>

        {/* Stats */}
        <div className="stats-grid" style={{ marginBottom: '2rem' }}>
          <div className="stat-card">
            <div className="stat-label">評分</div>
            <div className="stat-value">
              {buyer.rating_avg > 0 ? `⭐ ${buyer.rating_avg.toFixed(1)}` : '—'}
            </div>
            <div className="stat-sub">{buyer.rating_count} 評分</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">佣金率</div>
            <div className="stat-value">
              {buyer.commission_rate != null ? `${(buyer.commission_rate * 100).toFixed(1)}%` : '—'}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">電話</div>
            <div className="stat-value" style={{ fontSize: '1rem' }}>{buyer.phone ?? '—'}</div>
          </div>
        </div>

        {/* Details Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          <div className="card">
            <div className="card-header"><span className="card-title">💰 銀行資料</span></div>
            <div style={{ display: 'grid', gap: '0.75rem', fontSize: '0.875rem' }}>
              <div>
                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>銀行名稱</div>
                <div style={{ fontWeight: 500 }}>{buyer.bank_name ?? '—'}</div>
              </div>
              <div>
                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>帳戶持有人</div>
                <div style={{ fontWeight: 500 }}>{buyer.bank_account_holder ?? '—'}</div>
              </div>
              <div>
                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>帳戶號碼</div>
                <div style={{ fontWeight: 500, fontFamily: 'monospace' }}>{buyer.bank_account ? '****' + buyer.bank_account.slice(-4) : '—'}</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">📝 備註</span></div>
            <p style={{ fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>{buyer.notes ?? '—'}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header"><span className="card-title">⚡ 操作</span></div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <Link href={`/buyers/${id}/settlements`} className="btn btn-outline">📊 結算記錄</Link>
            <button className="btn btn-outline" onClick={() => alert('結算單功能：見 TODO.md P3')}>🔒 暫停買手</button>
          </div>
        </div>
      </main>
    </div>
  );
}
