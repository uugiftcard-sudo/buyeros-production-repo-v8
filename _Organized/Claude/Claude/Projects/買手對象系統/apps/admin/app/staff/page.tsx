'use client';

import { useEffect, useState } from 'react';
import { formatDate, getAdminUsers, createAdminUser, updateAdminUser, type AdminUser } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

const ROLE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  owner:      { label: '創辦人', color: '#7c3aed', bg: '#ede9fe' },
  admin:      { label: '管理員', color: '#dc2626', bg: '#fee2e2' },
  manager:    { label: '經理',   color: '#d97706', bg: '#fef3c7' },
  supervisor: { label: '主管',   color: '#0284c7', bg: '#e0f2fe' },
  staff:      { label: '員工',   color: '#4f46e5', bg: '#eef2ff' },
};

const ROLES = ['owner', 'admin', 'manager', 'supervisor', 'staff'] as const;

type ModalMode = 'create' | 'edit';

function UserModal({
  mode, user, onSave, onClose,
}: {
  mode: ModalMode; user?: AdminUser;
  onSave: (data: Partial<AdminUser>) => Promise<void>; onClose: () => void;
}) {
  const [form, setForm] = useState({
    display_name: user?.display_name ?? '',
    email: user?.email ?? '',
    phone: user?.phone ?? '',
    role: user?.role ?? 'staff',
    notes: user?.notes ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSave = async () => {
    if (!form.display_name.trim()) { setError('姓名不可為空'); return; }
    setSaving(true); setError('');
    try { await onSave(form); onClose(); }
    catch (e) { setError(e instanceof Error ? e.message : '儲存失敗'); }
    finally { setSaving(false); }
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{mode === 'create' ? '👤 新增員工' : '✏️ 編輯員工'}</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'grid', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label form-label-required">姓名</label>
              <input className="form-input" value={form.display_name}
                onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))}
                placeholder="員工姓名" />
            </div>
            <div className="form-group">
              <label className="form-label">電郵</label>
              <input className="form-input" type="email" value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                placeholder="email@example.com" />
            </div>
            <div className="form-group">
              <label className="form-label">電話</label>
              <input className="form-input" value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                placeholder="+852 9xxx xxxx" />
            </div>
            <div className="form-group">
              <label className="form-label form-label-required">角色</label>
              <select className="form-select" value={form.role}
                onChange={e => setForm(f => ({ ...f, role: e.target.value as AdminUser['role'] }))}>
                {ROLES.map(r => (
                  <option key={r} value={r}>{ROLE_CONFIG[r].label}</option>
                ))}
              </select>
              <div className="form-hint">
                {form.role === 'owner' && '⚠️ 創辦人擁有最高權限'}
                {form.role === 'admin' && '擁有幾乎所有管理權限'}
                {form.role === 'manager' && '可管理特定團隊'}
                {form.role === 'supervisor' && '可審批與查看'}
                {form.role === 'staff' && '只能操作自己負責的範圍'}
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">備註</label>
              <textarea className="form-textarea" rows={2} value={form.notes}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                placeholder="員工備註或職責..." />
            </div>
            {error && <div className="alert alert-danger">{error}</div>}
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>取消</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? '儲存中...' : '儲存'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function StaffPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [modalMode, setModalMode] = useState<ModalMode | null>(null);
  const [editTarget, setEditTarget] = useState<AdminUser | undefined>(undefined);
  const [roleFilter, setRoleFilter] = useState('');
  const [search, setSearch] = useState('');

  const fetchUsers = async (pg: number, role: string, searchTerm: string) => {
    setLoading(true);
    const { data } = await getAdminUsers({ page: pg, role: role || undefined, search: searchTerm || undefined });
    if (data?.data) {
      setUsers(data.data);
      setTotal(data.meta?.pagination?.total ?? 0);
      setTotalPages(data.meta?.pagination?.totalPages ?? 1);
    }
    setLoading(false);
  };

  useEffect(() => { fetchUsers(page, roleFilter, search); }, [page, roleFilter, search]);

  const handleSave = async (formData: Partial<AdminUser>) => {
    if (modalMode === 'create') {
      const { data, error } = await createAdminUser(formData);
      if (error) throw new Error(error.message);
      if (data) setUsers(prev => [data, ...prev]);
    } else if (editTarget) {
      const { data, error } = await updateAdminUser(editTarget.id, formData);
      if (error) throw new Error(error.message);
      if (data) setUsers(prev => prev.map(u => u.id === editTarget.id ? { ...u, ...data } : u));
    }
  };

  const roleStats = ROLES.reduce((acc, r) => {
    acc[r] = users.filter(u => u.role === r).length;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">👥 員工管理</h1>
            <p className="page-subtitle">管理員、經理、主管與員工帳戶</p>
          </div>
          <div className="page-header-right">
            <button className="btn btn-primary" onClick={() => { setEditTarget(undefined); setModalMode('create'); }}>
              + 新增員工
            </button>
          </div>
        </div>

        {/* Role summary */}
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.75rem', flexWrap: 'wrap' }}>
          {ROLES.map(r => {
            const cfg = ROLE_CONFIG[r];
            return (
              <button
                key={r}
                onClick={() => { setRoleFilter(roleFilter === r ? '' : r); setPage(1); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.4rem 0.85rem',
                  borderRadius: 99,
                  border: `1px solid ${roleFilter === r ? cfg.color : '#e2e8f0'}`,
                  background: roleFilter === r ? cfg.bg : '#fff',
                  color: roleFilter === r ? cfg.color : '#64748b',
                  cursor: 'pointer', fontSize: '0.8rem', fontWeight: 500,
                  transition: 'all 0.15s',
                }}
              >
                <span style={{ fontSize: '0.9rem' }}>{ROLE_CONFIG[r].label}</span>
                <span style={{
                  background: roleFilter === r ? cfg.color : '#e2e8f0',
                  color: roleFilter === r ? '#fff' : '#64748b',
                  borderRadius: 99, padding: '0 5px', fontSize: '0.7rem', fontWeight: 600,
                }}>
                  {roleStats[r] ?? 0}
                </span>
              </button>
            );
          })}
        </div>

        {/* Filters */}
        <div className="filter-bar">
          <input
            type="text"
            className="form-input"
            placeholder="🔍 搜尋姓名 / 電郵 / 電話..."
            style={{ maxWidth: 280 }}
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            onKeyDown={e => e.key === 'Enter' && fetchUsers(1, roleFilter, search)}
          />
          <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            {total} 人
          </span>
        </div>

        {/* Table */}
        <div className="table-wrap">
          {loading ? (
            <div className="loading">載入中...</div>
          ) : users.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">👥</div>
              <h3>暫無員工記錄</h3>
              <p>新增第一位員工以開始使用</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>電郵</th>
                  <th>電話</th>
                  <th>角色</th>
                  <th>最後登入</th>
                  <th>建立日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const cfg = ROLE_CONFIG[u.role] ?? { label: u.role, color: '#64748b', bg: '#f1f5f9' };
                  return (
                    <tr key={u.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <div style={{
                            width: 32, height: 32, borderRadius: '50%',
                            background: cfg.color, color: '#fff',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 700, fontSize: '0.8rem', flexShrink: 0,
                          }}>
                            {u.display_name.slice(0, 1).toUpperCase()}
                          </div>
                          <span style={{ fontWeight: 600 }}>{u.display_name}</span>
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{u.email ?? '—'}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{u.phone ?? '—'}</td>
                      <td>
                        <span className="badge" style={{ background: cfg.bg, color: cfg.color }}>
                          {cfg.label}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {u.last_login_at ? formatDate(u.last_login_at) : '從未登入'}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{formatDate(u.created_at)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => { setEditTarget(u); setModalMode('edit'); }}>
                            編輯
                          </button>
                        </div>
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
            <span>第 {page} / {totalPages} 頁，共 {total} 人</span>
            <div className="pagination-buttons">
              <button className="btn btn-outline btn-sm" onClick={() => { const p = page - 1; if (p >= 1) setPage(p); }} disabled={page <= 1}>←</button>
              <button className="btn btn-outline btn-sm" onClick={() => { const p = page + 1; if (p <= totalPages) setPage(p); }} disabled={page >= totalPages}>→</button>
            </div>
          </div>
        )}
      </main>

      {modalMode && (
        <UserModal
          mode={modalMode}
          user={editTarget}
          onSave={handleSave}
          onClose={() => { setModalMode(null); setEditTarget(undefined); }}
        />
      )}
    </div>
  );
}
