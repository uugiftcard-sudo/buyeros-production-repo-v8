// components/StatCard.tsx
'use client';

interface StatCardProps {
  label: string;
  value: string;
  subValue?: string;
  accent?: string;
  loading?: boolean;
}

export default function StatCard({
  label,
  value,
  subValue,
  accent = 'var(--primary)',
  loading = false,
}: StatCardProps) {
  if (loading) {
    return (
      <div className="stat-card" style={{ '--stat-accent': accent } as React.CSSProperties}>
        <div className="skeleton-line" style={{ width: '60%', height: 12, marginBottom: 8 }} />
        <div className="skeleton-line" style={{ width: '80%', height: 28 }} />
      </div>
    );
  }

  return (
    <div className="stat-card" style={{ '--stat-accent': accent } as React.CSSProperties}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {subValue && <div className="stat-sub">{subValue}</div>}
    </div>
  );
}
