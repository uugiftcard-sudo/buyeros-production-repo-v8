'use client';

import { useEffect, useState } from 'react';
import { formatDate, getAuditLog, getAuditSummary, exportAuditCsv, type AuditLogEntry, type AuditSummary } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

const ACTION_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  INSERT: { bg: '#d1fae5', text: '#065f46', label: '新增' },
  UPDATE: { bg: '#dbeafe', text: '#1e40af', label: '更新' },
  DELETE: { bg: '#fee2e2', text: '#991b1b', label: '刪除' },
};

const ROLE_COLORS: Record<string, string> = {
  owner: '#7c3aed', admin: '#dc2626', manager: '#d97706',
  supervisor: '#0284c7', staff: '#4f46e5', buyer: '#059669',
  customer: '#0891b2', system: '#64748b',
};

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ table: '', action: '', role: '', from: '', to: '', search: '' });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [tables, setTables] = useState<string[]>([]);
  const [actions, setActions] = useState<string[]>([]);
  const [roles, setRoles] = useState<string[]>([]);

  const fetchLogs = async (pg: number, f: typeof filters) => {
    setLoading(true);
    const { data, error } = await getAuditLog({
      page: pg, table: f.table || undefined,
      action: f.action || undefined, role: f.role || undefined,
      from: f.from || undefined, to: f.to || undefined, search: f.search || undefined,
    });
    if (!error && data) {
      setLogs(data.data ?? []);
      setTotal(data.meta?.total ?? 0);
      setTotalPages(data.meta?.totalPages ?? 1);
      if (data.tables) setTables(data.tables);
      if (data.actions) setActions(data.actions);
      if (data.roles) setRoles(data.roles);
    }
    setLoading(false);
  };

  useEffect(() => {
    getAuditSummary().then(({ data }) => { if (data) setSummary(data); });
    fetchLogs(page, filters);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFilter = (pg = 1) => { setPage(pg); fetchLogs(pg, filters); };

  const handleExport = () => exportAuditCsv({ table: filters.table || undefined, from: filters.from || undefined, to: filters.to || undefined });

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">🕵️ 審計日誌</h1>
            <p className="page-subtitle">所有操作記錄、變更追蹤與合規審查</p>
          </div>
          <div className="page-header-right">
            <button className="btn btn-secondary btn-sm" onClick={handleExport}>📥 導出 CSV</button>
          </div>
        </div>

        {/* Summary cards */}
        {summary && (
          <div className="stats-grid" style={{ marginBottom: '1.75rem' }}>
            {[
              { label: '今日操作', value: summary.counts.today, accent: '#4f46e5' },
              { label: '本週操作', value: summary.counts.thisWeek, accent: '#7c3aed' },
              { label: '本月操作', value: summary.counts.thisMonth, accent: '#0891b2' },
              { label: '記錄總數', value: total.toLocaleString(), accent: '#059669' },
            ].map(s => (
              <div key={s.label} className="stat-card" style={{ ['--stat-accent' as string]: s.accent }}>
                <div className="stat-label">{s.label}</div>
                <div className="stat-value">{s.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="card" style={{ marginBottom: '1rem', padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <select className="form-select" style={{ width: 'auto', minWidth: 140 }} value={filters.table} onChange={e => { setFilters(f => ({ ...f, table: e.target.value })); }}>
              <option value="">全部資料表</option>
              {tables.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select className="form-select" style={{ width: 'auto', minWidth: 120 }} value={filters.action} onChange={e => { setFilters(f => ({ ...f, action: e.target.value })); }}>
              <option value="">全部操作</option>
              {actions.map(a => <option key={a} value={a}>{ACTION_COLORS[a]?.label ?? a}</option>)}
            </select>
            <select className="form-select" style={{ width: 'auto', minWidth: 120 }} value={filters.role} onChange={e => { setFilters(f => ({ ...f, role: e.target.value })); }}>
              <option value="">全部角色</option>
              {roles.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <input type="date" className="form-input" style={{ width: 'auto' }} value={filters.from} onChange={e => { setFilters(f => ({ ...f, from: e.target.value })); }} />
            <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>至</span>
            <input type="date" className="form-input" style={{ width: 'auto' }} value={filters.to} onChange={e => { setFilters(f => ({ ...f, to: e.target.value })); }} />
            <input
              type="text"
              className="form-input"
              placeholder="🔍 搜尋..."
              style={{ maxWidth: 220 }}
              value={filters.search}
              onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); }}
              onKeyDown={e => e.key === 'Enter' && handleFilter()}
            />
            <button className="btn btn-primary btn-sm" onClick={() => handleFilter(1)}>篩選</button>
            <button className="btn btn-ghost btn-sm" onClick={() => { setFilters({ table: '', action: '', role: '', from: '', to: '', search: '' }); handleFilter(1); }}>清除</button>
            <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              {total.toLocaleString()} 筆記錄
            </span>
          </div>
        </div>

        {/* Table */}
        <div className="table-wrap">
          {loading ? (
            <div className="loading">載入中...</div>
          ) : logs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🕵️</div>
              <h3>暫無審計記錄</h3>
              <p>變更資料庫時會自動記錄在此</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>時間</th>
                  <th>操作</th>
                  <th>資料表</th>
                  <th>記錄 ID</th>
                  <th>角色</th>
                  <th>用戶</th>
                  <th>原因 / 備註</th>
                  <th>詳情</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => {
                  const ac = ACTION_COLORS[log.action] ?? { bg: '#f1f5f9', text: '#64748b', label: log.action };
                  const roleColor = ROLE_COLORS[log.changed_by_role ?? ''] ?? '#64748b';
                  return (
                    <tr key={log.id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {new Date(log.created_at).toLocaleString('zh-HK', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td>
                        <span className="badge" style={{ background: ac.bg, color: ac.text }}>
                          {ac.label}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', background: '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>
                          {log.table_name}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {log.row_id.slice(0, 8)}…
                        </span>
                      </td>
                      <td>
                        {log.changed_by_role && (
                          <span style={{
                            fontSize: '0.7rem', fontWeight: 600, padding: '2px 8px', borderRadius: 99,
                            background: `${roleColor}22`, color: roleColor,
                          }}>
                            {log.changed_by_role}
                          </span>
                        )}
                      </td>
                      <td style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                        {log.changed_by_name ?? '—'}
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.reason ?? '—'}
                      </td>
                      <td>
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                        >
                          {expandedId === log.id ? '隱藏' : '查看'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Expanded detail */}
        {expandedId && (() => {
          const log = logs.find(l => l.id === expandedId);
          if (!log) return null;
          return (
            <div className="card" style={{ marginTop: '1rem' }}>
              <div className="card-header">
                <span className="card-title">📋 變更詳情 — {log.table_name} / {log.row_id.slice(0, 8)}…</span>
                <button className="btn btn-ghost btn-sm" onClick={() => setExpandedId(null)}>✕</button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                {log.old_data && (
                  <div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#dc2626', marginBottom: '0.5rem' }}>🔴 變更前 (舊數據)</div>
                    <pre style={{ background: '#fff5f5', border: '1px solid #fecaca', borderRadius: 6, padding: '0.75rem', fontSize: '0.8rem', overflow: 'auto', maxHeight: 300, fontFamily: 'monospace' }}>
                      {JSON.stringify(log.old_data, null, 2)}
                    </pre>
                  </div>
                )}
                {log.new_data && (
                  <div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#059669', marginBottom: '0.5rem' }}>🟢 變更後 (新數據)</div>
                    <pre style={{ background: '#f0fdf4', border: '1px solid #a7f3d0', borderRadius: 6, padding: '0.75rem', fontSize: '0.8rem', overflow: 'auto', maxHeight: 300, fontFamily: 'monospace' }}>
                      {JSON.stringify(log.new_data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          );
        })()}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <span>第 {page} / {totalPages} 頁，共 {total.toLocaleString()} 筆記錄</span>
            <div className="pagination-buttons">
              <button className="btn btn-outline btn-sm" onClick={() => handleFilter(page - 1)} disabled={page <= 1}>← 上一頁</button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const p = Math.max(1, Math.min(totalPages - 4, page - 2)) + i;
                return p <= totalPages && (
                  <button
                    key={p}
                    className={`btn btn-sm ${p === page ? 'btn-primary' : 'btn-outline'}`}
                    onClick={() => handleFilter(p)}
                  >{p}</button>
                );
              })}
              <button className="btn btn-outline btn-sm" onClick={() => handleFilter(page + 1)} disabled={page >= totalPages}>下一頁 →</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
