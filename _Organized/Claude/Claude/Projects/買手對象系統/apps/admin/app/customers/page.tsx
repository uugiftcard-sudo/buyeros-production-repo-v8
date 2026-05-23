'use client';

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from 'react';
import { getCustomers, createCustomer, updateCustomer, formatDate } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import type { Customer } from '@/lib/api';

type ModalMode = 'create' | 'edit';

function CustomerModal({
  mode,
  customer,
  onSave,
  onClose,
}: {
  mode: ModalMode;
  customer?: Customer;
  onSave: (data: Partial<Customer>) => Promise<void>;
  onClose: () => void;
}) {
  const [displayName, setDisplayName] = useState(customer?.display_name ?? '');
  const [phone, setPhone] = useState(customer?.phone ?? '');
  const [email, setEmail] = useState(customer?.email ?? '');
  const [notes, setNotes] = useState(customer?.notes ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSave = async () => {
    if (!displayName.trim()) { setError('姓名不可為空'); return; }
    setSaving(true);
    setError('');
    try {
      await onSave({ display_name: displayName.trim(), phone: phone.trim() || null, email: email.trim() || null, notes: notes.trim() || null });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '儲存失敗');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }}>
      <div className="card" style={{ width: '400px', maxWidth: '90vw' }}>
        <div className="card-header">
          <span className="card-title">{mode === 'create' ? '➕ 新建客戶' : '✏️ 編輯客戶'}</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}>✕</button>
        </div>
        <div style={{ display: 'grid', gap: '1rem', padding: '1rem 0' }}>
          <div className="form-group">
            <label className="form-label">姓名 *</label>
            <input className="form-input" value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder="客戶姓名" />
          </div>
          <div className="form-group">
            <label className="form-label">電話</label>
            <input className="form-input" value={phone} onChange={e => setPhone(e.target.value)} placeholder="+852 9xxx xxxx" />
          </div>
          <div className="form-group">
            <label className="form-label">電郵</label>
            <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="email@example.com" />
          </div>
          <div className="form-group">
            <label className="form-label">備註</label>
            <textarea className="form-textarea" value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="客戶偏好或特殊需求..." />
          </div>
          {error && <div style={{ color: 'var(--color-danger)', fontSize: '0.875rem' }}>{error}</div>}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button className="btn btn-outline" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? '儲存中...' : '儲存'}</button>
        </div>
      </div>
    </div>
  );
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [modalMode, setModalMode] = useState<ModalMode | null>(null);
  const [editTarget, setEditTarget] = useState<Customer | undefined>(undefined);

  const fetchCustomers = async (pageNum: number, searchTerm: string) => {
    setLoading(true);
    const { data } = await getCustomers({ page: pageNum, search: searchTerm });
    setCustomers(data?.data ?? []);
    setTotalPages(data?.meta?.pagination?.totalPages ?? 1);
    setLoading(false);
  };

  useEffect(() => {
    fetchCustomers(page, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchCustomers(1, search);
  };

  const handleSave = async (formData: Partial<Customer>) => {
    if (modalMode === 'create') {
      const { data, error } = await createCustomer(formData);
      if (error) throw new Error(error.message);
      if (data) setCustomers(prev => [data, ...prev]);
    } else if (editTarget) {
      const { data, error } = await updateCustomer(editTarget.id, formData);
      if (error) throw new Error(error.message);
      if (data) setCustomers(prev => prev.map(c => c.id === editTarget.id ? { ...c, ...data } : c));
    }
  };

  const handleEdit = (c: Customer) => { setEditTarget(c); setModalMode('edit'); };
  const handleCreate = () => { setEditTarget(undefined); setModalMode('create'); };
  const closeModal = () => { setModalMode(null); setEditTarget(undefined); };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <h1 className="page-title">👥 客戶管理</h1>
          <p className="page-subtitle">客戶資料、標籤與通訊記錄</p>
        </div>

        <div className="filter-bar">
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem', flex: 1 }}>
            <input
              type="text"
              placeholder="🔍 搜尋姓名 / 電話 / 電郵..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="form-input"
              style={{ maxWidth: '300px' }}
            />
            <button type="submit" className="btn btn-outline">搜尋</button>
          </form>
          <button className="btn btn-primary" onClick={handleCreate}>+ 新客戶</button>
        </div>

        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {loading ? (
            <div className="loading">載入中...</div>
          ) : customers.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">👥</div>
              <p>找不到客戶記錄</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>電話</th>
                  <th>電郵</th>
                  <th>狀態</th>
                  <th>最近訂單</th>
                  <th>建立日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {customers.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}>{c.display_name}</td>
                    <td>{c.phone ?? '—'}</td>
                    <td>{c.email ?? '—'}</td>
                    <td>
                      <span className={`badge badge-${c.status === 'active' ? 'completed' : 'cancelled'}`}>
                        {c.status === 'active' ? '活躍' : '停用'}
                      </span>
                    </td>
                    <td>{c.recent_orders?.length ?? 0} 單</td>
                    <td>{formatDate(c.created_at)}</td>
                    <td>
                      <button className="btn btn-outline btn-sm" onClick={() => handleEdit(c)}>編輯</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

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

      {modalMode && (
        <CustomerModal
          mode={modalMode}
          customer={editTarget}
          onSave={handleSave}
          onClose={closeModal}
        />
      )}
    </div>
  );
}
