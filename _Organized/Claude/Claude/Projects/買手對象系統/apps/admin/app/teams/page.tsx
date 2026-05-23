'use client';

import { useEffect, useState } from 'react';
import { formatCents, formatDate, getTeamPerformance, getTeams, type TeamPerformance } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

const TEAM_COLORS = [
  '#4f46e5', '#7c3aed', '#0891b2', '#059669',
  '#d97706', '#dc2626', '#db2777', '#65a30d',
];

function ProgressBar({ value, max, color = '#4f46e5' }: { value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <div style={{ flex: 1, height: 6, background: '#e5e7eb', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 99, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 550, minWidth: 36, textAlign: 'right' }}>
        {pct}%
      </span>
    </div>
  );
}

function TeamCard({ team, index }: { team: TeamPerformance; index: number }) {
  const color = TEAM_COLORS[index % TEAM_COLORS.length];
  const orderPct = team.monthly_orders_pct ?? 0;
  const revenuePct = team.monthly_revenue_pct ?? 0;

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        background: `linear-gradient(135deg, ${color}22, ${color}11)`,
        borderBottom: `3px solid ${color}`,
        padding: '1rem 1.25rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '0.65rem', fontWeight: 600, color, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>
              {team.team_code}
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>{team.team_name}</div>
            <div style={{ fontSize: '0.775rem', color: '#64748b', marginTop: 2 }}>
              {team.member_count} 名成員
            </div>
          </div>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            background: color, color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: '0.95rem',
          }}>
            {team.member_count}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div style={{ padding: '1rem 1.25rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>月訂單</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 750, color: '#0f172a', letterSpacing: '-0.02em' }}>
            {team.monthly_orders}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: 2 }}>
            目標 {team.target_orders_monthly}
          </div>
          <div style={{ marginTop: '0.5rem' }}>
            <ProgressBar value={team.monthly_orders} max={team.target_orders_monthly} color={color} />
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>月收入</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 750, color: '#0f172a', letterSpacing: '-0.02em' }}>
            {formatCents(team.monthly_revenue_cents)}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: 2 }}>
            目標 {formatCents(team.target_revenue_monthly_cents)}
          </div>
          <div style={{ marginTop: '0.5rem' }}>
            <ProgressBar value={team.monthly_revenue_cents} max={team.target_revenue_monthly_cents} color={color} />
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
        borderTop: '1px solid #f1f5f9',
        padding: '0.75rem 1.25rem',
        gap: '0.5rem',
      }}>
        {[
          { label: '總訂單', value: team.total_orders },
          { label: '已完成', value: team.completed_orders },
          { label: '均單', value: formatCents(team.avg_order_value_cents) },
        ].map(item => (
          <div key={item.label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>{item.value}</div>
            <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getTeamPerformance()
      .then(({ data, error }) => {
        if (error) setError(error.message);
        else setTeams(data ?? []);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalMembers = teams.reduce((s, t) => s + t.member_count, 0);
  const totalMonthlyOrders = teams.reduce((s, t) => s + t.monthly_orders, 0);
  const totalMonthlyRevenue = teams.reduce((s, t) => s + t.monthly_revenue_cents, 0);

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div>
            <h1 className="page-title">🏆 團隊管理</h1>
            <p className="page-subtitle">買手團隊、表現追蹤與目標管理</p>
          </div>
          <div className="page-header-right">
            <button className="btn btn-primary">+ 新增團隊</button>
          </div>
        </div>

        {/* Overview stats */}
        <div className="stats-grid" style={{ marginBottom: '1.75rem' }}>
          {[
            { label: '團隊數', value: teams.length, icon: '🏢', accent: '#4f46e5' },
            { label: '總成員', value: totalMembers, icon: '👥', accent: '#7c3aed' },
            { label: '本月訂單', value: totalMonthlyOrders, icon: '📦', accent: '#0891b2' },
            { label: '本月收入', value: formatCents(totalMonthlyRevenue), icon: '💰', accent: '#059669' },
          ].map(s => (
            <div key={s.label} className="stat-card" style={{ ['--stat-accent' as string]: s.accent }}>
              <div className="stat-label">{s.label}</div>
              <div className="stat-value">{s.value}</div>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="loading">載入中...</div>
        ) : error ? (
          <div className="alert alert-danger">⚠️ {error}</div>
        ) : teams.length === 0 ? (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">🏆</div>
              <h3>尚未建立團隊</h3>
              <p>點擊「新增團隊」建立第一個買手團隊</p>
              <button className="btn btn-primary" style={{ marginTop: '1rem' }}>+ 新增團隊</button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.25rem' }}>
            {teams.map((team, i) => (
              <TeamCard key={team.team_id} team={team} index={i} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
