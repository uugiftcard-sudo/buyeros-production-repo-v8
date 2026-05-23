'use client';

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from 'react';
import { getSupabaseClient } from '@/lib/supabase';
import Sidebar from '@/components/Sidebar';
import { formatDate } from '@/lib/api';

const supabase = getSupabaseClient();

type Channel = 'telegram' | 'whatsapp' | 'email' | 'phone' | 'sms';
type Direction = 'inbound' | 'outbound';

interface Communication {
  id: string;
  customer_id: string | null;
  buyer_id: string | null;
  channel: Channel;
  direction: Direction;
  subject: string | null;
  content: string;
  tags: string[];
  is_archived: boolean;
  created_at: string;
  created_by: string | null;
  customer?: { id: string; display_name: string } | null;
  buyer?: { id: string; display_name: string } | null;
  customer_name?: string;
  buyer_name?: string;
}

interface CommunicationRow {
  id: string;
  customer_id: string | null;
  buyer_id: string | null;
  channel: Channel;
  direction: Direction;
  subject: string | null;
  content: string;
  tags: string[];
  is_archived: boolean;
  created_at: string;
  created_by: string | null;
  customer?: { id: string; display_name: string } | null;
  buyer?: { id: string; display_name: string } | null;
}

const CHANNEL_ICONS: Record<Channel, string> = {
  telegram: '✈️',
  whatsapp: '💬',
  email: '📧',
  phone: '📞',
  sms: '💬',
};

const CHANNEL_OPTIONS: { value: Channel; label: string }[] = [
  { value: 'telegram', label: '✈️ Telegram' },
  { value: 'whatsapp', label: '💬 WhatsApp' },
  { value: 'email', label: '📧 Email' },
  { value: 'phone', label: '📞 Phone' },
  { value: 'sms', label: '💬 SMS' },
];

const TAG_OPTIONS = [
  'order-inquiry', 'complaint', 'follow-up', 'payment', 'delivery',
  'refund-request', 'general', 'feedback', 'urgent',
];

const EXAMPLE_COMMUNICATIONS: Communication[] = [
  {
    id: '1',
    customer_id: null,
    buyer_id: null,
    channel: 'telegram',
    direction: 'inbound',
    subject: 'Chanel CF 黑色 26歲',
    content: '你好，請問有冇 Chanel Classic Flap 黑色 26歲？要無敵卡嘅。',
    tags: ['order-inquiry'],
    is_archived: false,
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    created_by: null,
  },
  {
    id: '2',
    customer_id: null,
    buyer_id: null,
    channel: 'whatsapp',
    direction: 'inbound',
    subject: 'Hermès Kelly 25',
    content: '你好，我想要一個 Hermès Kelly 25 Togo 黑色銀扣，謝謝。',
    tags: ['order-inquiry', 'follow-up'],
    is_archived: false,
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    created_by: null,
  },
  {
    id: '3',
    customer_id: null,
    buyer_id: null,
    channel: 'email',
    direction: 'outbound',
    subject: 'LV Neverfull 白色回覆',
    content: '您好，感謝您的查詢。LV Neverfull 白色 MM 目前現貨，HKD 15,800，包配件和、防塵袋。如有興趣請告知，多謝！',
    tags: ['general'],
    is_archived: false,
    created_at: new Date(Date.now() - 3600000 * 8).toISOString(),
    created_by: 'admin',
  },
];

export default function CommunicationsPage() {
  const [communications, setCommunications] = useState<Communication[]>(EXAMPLE_COMMUNICATIONS);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [channelFilter, setChannelFilter] = useState<Channel | ''>('');
  const [directionFilter, setDirectionFilter] = useState<Direction | ''>('');
  const [tagFilter, setTagFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [selectedComm, setSelectedComm] = useState<Communication | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);

  // New form state
  const [newForm, setNewForm] = useState<Partial<Communication>>({
    channel: 'telegram',
    direction: 'outbound',
    subject: '',
    content: '',
    tags: [],
    customer_id: null,
    buyer_id: null,
  });

  const fetchCommunications = async (pageNum: number) => {
    setLoading(true);
    const { data, error } = await supabase
      .from('communications')
      .select('*, customer:customers(id, display_name), buyer:buyers(id, display_name)', { count: 'exact' })
      .eq('is_archived', showArchived)
      .order('created_at', { ascending: false })
      .range((pageNum - 1) * 20, pageNum * 20 - 1);

    if (!error && data && data.length > 0) {
      const mapped: Communication[] = data.map((r: CommunicationRow) => ({
        ...r,
        customer_name: r.customer?.display_name,
        buyer_name: r.buyer?.display_name,
      }));
      setCommunications(mapped);
      setTotalPages(Math.ceil(data.length / 20));
    } else {
      // Use example data if table doesn't exist
      let filtered = EXAMPLE_COMMUNICATIONS;
      if (channelFilter) filtered = filtered.filter(c => c.channel === channelFilter);
      if (directionFilter) filtered = filtered.filter(c => c.direction === directionFilter);
      if (tagFilter) filtered = filtered.filter(c => c.tags.includes(tagFilter));
      if (search) filtered = filtered.filter(c =>
        c.subject?.toLowerCase().includes(search.toLowerCase()) ||
        c.content.toLowerCase().includes(search.toLowerCase())
      );
      setCommunications(filtered);
      setTotalPages(1);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchCommunications(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, channelFilter, directionFilter, tagFilter, showArchived]);

  const handleArchive = async (id: string) => {
    const updated = communications.map(c =>
      c.id === id ? { ...c, is_archived: !c.is_archived } : c
    );
    setCommunications(updated);
    if (selectedComm?.id === id) setSelectedComm(null);

    await supabase
      .from('communications')
      .update({ is_archived: !communications.find(c => c.id === id)?.is_archived })
      .eq('id', id);
  };

  const handleSaveNew = async () => {
    if (!newForm.content?.trim()) { alert('請填寫內容'); return; }
    const newComm: Communication = {
      id: String(Date.now()),
      customer_id: newForm.customer_id ?? null,
      buyer_id: newForm.buyer_id ?? null,
      channel: newForm.channel ?? 'telegram',
      direction: newForm.direction ?? 'outbound',
      subject: newForm.subject ?? null,
      content: newForm.content ?? '',
      tags: newForm.tags ?? [],
      is_archived: false,
      created_at: new Date().toISOString(),
      created_by: 'admin',
    };
    setCommunications(prev => [newComm, ...prev]);
    setShowNewForm(false);
    setNewForm({ channel: 'telegram', direction: 'outbound', subject: '', content: '', tags: [], customer_id: null, buyer_id: null });

    await supabase.from('communications').insert([{
      channel: newForm.channel,
      direction: newForm.direction,
      subject: newForm.subject,
      content: newForm.content,
      tags: newForm.tags,
      customer_id: newForm.customer_id,
      buyer_id: newForm.buyer_id,
    }]);
  };

  const toggleTag = (tag: string) => {
    setNewForm(prev => ({
      ...prev,
      tags: prev.tags?.includes(tag)
        ? prev.tags.filter(t => t !== tag)
        : [...(prev.tags ?? []), tag],
    }));
  };

  const filteredComms = communications;

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 className="page-title">💬 通訊記錄</h1>
            <p className="page-subtitle">客戶、買手、客服的來往記錄</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowNewForm(true)}>
            ✏️ 新建記錄
          </button>
        </div>

        {/* Stats */}
        <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
          <div className="stat-card">
            <div className="stat-label">全部記錄</div>
            <div className="stat-value">{communications.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">📥 來電/訊</div>
            <div className="stat-value">{communications.filter(c => c.direction === 'inbound').length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">📤 去電/訊</div>
            <div className="stat-value">{communications.filter(c => c.direction === 'outbound').length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">⚠️ 待處理投訴</div>
            <div className="stat-value" style={{ color: 'var(--color-danger)' }}>
              {communications.filter(c => c.tags?.includes('complaint')).length}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="filter-bar">
          <input
            type="text"
            placeholder="🔍 搜尋主題或內容..."
            className="form-input"
            style={{ width: '240px' }}
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
          <select className="form-select" style={{ width: 'auto' }} value={channelFilter} onChange={e => { setChannelFilter(e.target.value as Channel | ''); setPage(1); }}>
            <option value="">所有渠道</option>
            {CHANNEL_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <select className="form-select" style={{ width: 'auto' }} value={directionFilter} onChange={e => { setDirectionFilter(e.target.value as Direction | ''); setPage(1); }}>
            <option value="">全部方向</option>
            <option value="inbound">📥 來電/訊</option>
            <option value="outbound">📤 去電/訊</option>
          </select>
          <select className="form-select" style={{ width: 'auto' }} value={tagFilter} onChange={e => { setTagFilter(e.target.value); setPage(1); }}>
            <option value="">所有標籤</option>
            {TAG_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.875rem', color: 'var(--color-text-muted)', cursor: 'pointer' }}>
            <input type="checkbox" checked={showArchived} onChange={e => { setShowArchived(e.target.checked); setPage(1); }} />
            顯示已封存
          </label>
        </div>

        {/* New Record Form */}
        {showNewForm && (
          <div className="card" style={{ border: '2px solid var(--color-primary)', marginBottom: '1.5rem' }}>
            <div className="card-header">
              <span className="card-title">✏️ 新建通訊記錄</span>
              <button className="btn btn-outline btn-sm" onClick={() => setShowNewForm(false)}>取消</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">渠道 *</label>
                <select
                  className="form-select"
                  value={newForm.channel}
                  onChange={e => setNewForm(p => ({ ...p, channel: e.target.value as Channel }))}
                >
                  {CHANNEL_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">方向 *</label>
                <select
                  className="form-select"
                  value={newForm.direction}
                  onChange={e => setNewForm(p => ({ ...p, direction: e.target.value as Direction }))}
                >
                  <option value="inbound">📥 來電/訊</option>
                  <option value="outbound">📤 去電/訊</option>
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">主題</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="例：Hermès Kelly 25 查詢"
                  value={newForm.subject ?? ''}
                  onChange={e => setNewForm(p => ({ ...p, subject: e.target.value }))}
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">內容 *</label>
                <textarea
                  className="form-textarea"
                  rows={4}
                  placeholder="請輸入通訊內容..."
                  value={newForm.content ?? ''}
                  onChange={e => setNewForm(p => ({ ...p, content: e.target.value }))}
                />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">標籤</label>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {TAG_OPTIONS.map(tag => (
                    <button
                      key={tag}
                      className="btn btn-sm"
                      style={{
                        background: newForm.tags?.includes(tag) ? 'var(--color-primary)' : '#f3f4f6',
                        color: newForm.tags?.includes(tag) ? '#fff' : 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                        fontSize: '0.75rem',
                      }}
                      onClick={() => toggleTag(tag)}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
              <button className="btn btn-outline" onClick={() => setShowNewForm(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleSaveNew}>💾 儲存記錄</button>
            </div>
          </div>
        )}

        {/* Comm List vs Detail */}
        <div style={{ display: 'grid', gridTemplateColumns: selectedComm ? '1fr 1fr' : '1fr', gap: '1.5rem' }}>
          {/* List */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {loading ? (
              <div className="loading">載入中...</div>
            ) : filteredComms.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">💬</div>
                <p>暫無通訊記錄</p>
              </div>
            ) : (
              <div>
                {filteredComms.map(comm => (
                  <div
                    key={comm.id}
                    onClick={() => setSelectedComm(comm)}
                    style={{
                      padding: '0.875rem 1rem',
                      borderBottom: '1px solid var(--color-border)',
                      cursor: 'pointer',
                      background: selectedComm?.id === comm.id ? '#eff6ff' : undefined,
                      display: 'flex',
                      gap: '0.75rem',
                      alignItems: 'flex-start',
                    }}
                  >
                    <span style={{ fontSize: '1.1rem', flexShrink: 0 }}>
                      {CHANNEL_ICONS[comm.channel] ?? '💬'}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                          {comm.direction === 'inbound' ? '📥' : '📤'}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', flexShrink: 0 }}>
                          {formatDate(comm.created_at)}
                        </span>
                      </div>
                      <p style={{ fontWeight: 500, fontSize: '0.875rem', marginTop: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {comm.subject ?? '(無主題)'}
                      </p>
                      <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.15rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {comm.content}
                      </p>
                      {comm.tags && comm.tags.length > 0 && (
                        <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.3rem', flexWrap: 'wrap' }}>
                          {comm.tags.map(tag => (
                            <span key={tag} className="badge badge-pending" style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem' }}>{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Detail */}
          {selectedComm && (
            <div className="card" style={{ position: 'sticky', top: '1rem' }}>
              <div className="card-header">
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '1.1rem' }}>{CHANNEL_ICONS[selectedComm.channel]}</span>
                  <span className="badge badge-pending">{selectedComm.direction === 'inbound' ? '📥 來電/訊' : '📤 去電/訊'}</span>
                  {selectedComm.tags?.map(tag => (
                    <span key={tag} className="badge badge-pending">{tag}</span>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => handleArchive(selectedComm.id)}
                  >
                    {selectedComm.is_archived ? '📂 取消封存' : '📥 封存'}
                  </button>
                  <button className="btn btn-outline btn-sm" onClick={() => setSelectedComm(null)}>✕</button>
                </div>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  {formatDate(selectedComm.created_at)} · {selectedComm.created_by ? `by ${selectedComm.created_by}` : ''}
                </div>
                {selectedComm.subject && (
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.5rem' }}>{selectedComm.subject}</h3>
                )}
              </div>
              <div style={{
                background: '#f9fafb',
                border: '1px solid var(--color-border)',
                borderRadius: '0.375rem',
                padding: '1rem',
                fontSize: '0.875rem',
                whiteSpace: 'pre-wrap',
                lineHeight: 1.6,
                maxHeight: '300px',
                overflowY: 'auto',
              }}>
                {selectedComm.content}
              </div>
              <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--color-border)', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                <p>💡 這是 example 數據，請在 Supabase 中執行通訊記錄 migration 後使用真實數據。</p>
                <p style={{ marginTop: '0.3rem' }}>
                  渠道：{selectedComm.channel} · 方向：{selectedComm.direction}
                  {selectedComm.customer_name ? ` · 客戶：${selectedComm.customer_name}` : ''}
                  {selectedComm.buyer_name ? ` · 買手：${selectedComm.buyer_name}` : ''}
                </p>
              </div>
            </div>
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
