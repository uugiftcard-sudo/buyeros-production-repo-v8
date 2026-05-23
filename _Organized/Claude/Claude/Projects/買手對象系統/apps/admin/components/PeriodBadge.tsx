// components/PeriodBadge.tsx

interface PeriodBadgeProps {
  status: 'open' | 'closed' | 'archived' | string;
  size?: 'sm' | 'md';
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  open: { label: '進行中', className: 'badge-success' },
  closed: { label: '已結帳', className: 'badge-muted' },
  archived: { label: '已封存', className: 'badge-muted' },
  pending: { label: '待處理', className: 'badge-warning' },
  active: { label: '啟用', className: 'badge-success' },
  inactive: { label: '停用', className: 'badge-muted' },
};

export default function PeriodBadge({ status, size = 'md' }: PeriodBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, className: 'badge-muted' };
  const sizeClass = size === 'sm' ? 'badge-sm' : '';
  return (
    <span className={`badge ${config.className} ${sizeClass}`}>
      {config.label}
    </span>
  );
}
