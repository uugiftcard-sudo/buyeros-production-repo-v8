// components/ARBucketBadge.tsx

interface ARBucketBadgeProps {
  bucket: string;
  size?: 'sm' | 'md';
}

const BUCKET_CONFIG: Record<string, { label: string; className: string }> = {
  current: { label: '未逾期', className: 'badge-success' },
  '30':    { label: '逾期 1-30 天', className: 'badge-warning' },
  '60':    { label: '逾期 31-60 天', className: 'badge-orange' },
  '90':    { label: '逾期 61-90 天', className: 'badge-danger' },
  '90plus': { label: '逾期 90+ 天', className: 'badge-danger' },
};

export default function ARBucketBadge({ bucket, size = 'md' }: ARBucketBadgeProps) {
  const config = BUCKET_CONFIG[bucket] ?? { label: bucket, className: 'badge-muted' };
  const sizeClass = size === 'sm' ? 'badge-sm' : '';
  return (
    <span className={`badge ${config.className} ${sizeClass}`}>
      {config.label}
    </span>
  );
}
