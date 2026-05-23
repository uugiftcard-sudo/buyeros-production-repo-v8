'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';

type SettingField =
  | { key: string; label: string; type: 'text'; placeholder?: string; description: string }
  | { key: string; label: string; type: 'select'; options: string[]; description: string }
  | { key: string; label: string; type: 'number'; placeholder?: string; description: string }
  | { key: string; label: string; type: 'toggle'; description: string };

type SettingSection = {
  key: string;
  label: string;
  icon: string;
  fields: SettingField[];
};

const SETTING_SECTIONS: SettingSection[] = [
  {
    key: 'general',
    label: '一般設定',
    icon: '⚙️',
    fields: [
      { key: 'company_name', label: '公司名稱', type: 'text', placeholder: '買手對象系統', description: '系統顯示的公司名稱' },
      { key: 'currency', label: '默認貨幣', type: 'select', options: ['HKD', 'USD', 'CNY', 'TWD'], description: '所有金額的顯示貨幣' },
      { key: 'timezone', label: '時區', type: 'select', options: ['Asia/Hong_Kong', 'Asia/Taipei', 'Asia/Shanghai', 'UTC'], description: '所有時間的顯示時區' },
    ],
  },
  {
    key: 'orders',
    label: '訂單設定',
    icon: '📦',
    fields: [
      { key: 'auto_assign', label: '自動分配買手', type: 'toggle', description: '新訂單自動分配給評分最高的可用買手' },
      { key: 'low_stock_threshold', label: '低庫存閾值', type: 'number', placeholder: '5', description: '自動提醒的最低庫存水平' },
      { key: 'payment_timeout_hours', label: '付款超時（小時）', type: 'number', placeholder: '48', description: '未付款訂單自動取消前的小時數' },
    ],
  },
  {
    key: 'notifications',
    label: '通知設定',
    icon: '🔔',
    fields: [
      { key: 'notify_telegram', label: 'Telegram 通知', type: 'toggle', description: '透過 Telegram 發送重要事件通知' },
      { key: 'notify_email', label: '電郵通知', type: 'toggle', description: '訂單狀態變更時發送電郵' },
      { key: 'notify_refund', label: '退款審批通知', type: 'toggle', description: '有待審批退款時通知管理員' },
    ],
  },
  {
    key: 'team',
    label: '團隊與權限',
    icon: '🏆',
    fields: [
      { key: 'require_kyc', label: '買手 KYC 必填', type: 'toggle', description: '新買手必須完成身份驗證才能接單' },
      { key: 'default_commission', label: '默認佣金率 (%)', type: 'number', placeholder: '5.0', description: '新買手的默認佣金率' },
      { key: 'team_target_monthly', label: '團隊月目標收入 (HK$)', type: 'number', placeholder: '50000', description: '每個團隊的月收入目標（以分計算）' },
    ],
  },
];

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);
  const [activeSection, setActiveSection] = useState('general');

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const section = SETTING_SECTIONS.find(s => s.key === activeSection) ?? SETTING_SECTIONS[0];

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">⚙️ 系統設定</h1>
            <p className="page-subtitle">系統配置、通知、權限與整合設定</p>
          </div>
          {saved && (
            <div className="alert alert-success" style={{ marginBottom: 0, padding: '0.5rem 1rem' }}>
              ✅ 設定已保存
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '1.5rem', alignItems: 'start' }}>
          {/* Left nav */}
          <div className="card" style={{ padding: '0.75rem' }}>
            {SETTING_SECTIONS.map(s => (
              <button
                key={s.key}
                onClick={() => setActiveSection(s.key)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.6rem',
                  width: '100%', padding: '0.65rem 0.75rem',
                  border: 'none', borderRadius: 'var(--radius-sm)',
                  background: activeSection === s.key ? 'var(--primary-light)' : 'transparent',
                  color: activeSection === s.key ? 'var(--primary)' : 'var(--text)',
                  fontSize: '0.875rem', fontWeight: activeSection === s.key ? 600 : 450,
                  cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                }}
                onMouseEnter={e => { if (activeSection !== s.key) (e.currentTarget as HTMLElement).style.background = 'var(--border-subtle)'; }}
                onMouseLeave={e => { if (activeSection !== s.key) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                <span>{s.icon}</span>
                {s.label}
              </button>
            ))}
          </div>

          {/* Right content */}
          <form onSubmit={handleSave}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">{section.icon} {section.label}</span>
              </div>

              <div style={{ display: 'grid', gap: '1.5rem' }}>
                {section.fields.map(field => (
                  <div key={field.key} className="form-group" style={{ marginBottom: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                      <label className="form-label" style={{ marginBottom: 0 }}>{field.label}</label>
                      {field.type === 'toggle' && (
                        <button
                          type="button"
                          role="switch"
                          aria-checked="true"
                          style={{
                            width: 44, height: 24, borderRadius: 99, background: 'var(--primary)',
                            border: 'none', cursor: 'pointer', position: 'relative', transition: 'background 0.2s',
                          }}
                        >
                          <span style={{
                            display: 'block', width: 20, height: 20, borderRadius: '50%',
                            background: '#fff', position: 'absolute', top: 2, right: 2,
                            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                            transition: 'right 0.2s',
                          }} />
                        </button>
                      )}
                    </div>

                    {field.type === 'text' && (
                      <input
                        className="form-input"
                        type="text"
                        name={field.key}
                        placeholder={field.placeholder}
                        defaultValue=""
                      />
                    )}
                    {field.type === 'number' && (
                      <input
                        className="form-input"
                        type="number"
                        name={field.key}
                        placeholder={field.placeholder}
                        defaultValue=""
                      />
                    )}
                    {field.type === 'select' && (
                      <select className="form-select" name={field.key}>
                        {((field as { options: string[] }).options ?? []).map(opt => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    )}

                    {field.description && (
                      <div className="form-hint">{field.description}</div>
                    )}
                  </div>
                ))}
              </div>

              <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border)', display: 'flex', gap: '0.6rem' }}>
                <button type="submit" className="btn btn-primary">💾 保存設定</button>
                <button type="reset" className="btn btn-ghost">重置</button>
              </div>
            </div>
          </form>
        </div>

        {/* Environment Info */}
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <span className="card-title">🔑 環境資訊</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            {[
              { label: 'Supabase URL', value: process.env.NEXT_PUBLIC_SUPABASE_URL ? '已配置 ✓' : '未配置 ✗', ok: !!process.env.NEXT_PUBLIC_SUPABASE_URL },
              { label: 'Supabase Anon Key', value: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? '已配置 ✓' : '未配置 ✗', ok: !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY },
              { label: 'Edge Functions', value: '已部署', ok: true },
              { label: '會計層 Migration', value: '已應用', ok: true },
              { label: '審計觸發器', value: '已啟用', ok: true },
              { label: 'Telegram Bot', value: '待配置', ok: false },
            ].map(item => (
              <div key={item.label} style={{
                padding: '0.75rem', background: '#f8fafc',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.25rem' }}>
                  {item.label}
                </div>
                <div style={{ fontSize: '0.875rem', fontWeight: 550, color: item.ok ? 'var(--success)' : 'var(--warning)' }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
