'use client';

import { useEffect, useState } from 'react';
import { getCustomers, formatDate } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import type { Customer } from '@/lib/api';

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');

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
          <button className="btn btn-primary" onClick={() => alert('新客戶功能：使用 Telegram Bot 或 Supabase Studio 新增')}>
            + 新客戶
          </button>
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
                      <button className="btn btn-outline btn-sm">編輯</button>
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
    </div>
  );
}
