// components/SkeletonLoader.tsx

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  style?: React.CSSProperties;
}

export function SkeletonLine({ width = '100%', height = 16, borderRadius = 4, style }: SkeletonProps) {
  return (
    <div
      className="skeleton-line"
      style={{ width, height, borderRadius, ...style }}
    />
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <SkeletonLine width="40%" height={12} style={{ marginBottom: 16 }} />
      <SkeletonLine width="70%" height={28} style={{ marginBottom: 8 }} />
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine
          key={i}
          width={i === lines - 1 ? '60%' : '100%'}
          height={14}
          style={{ marginBottom: 8 }}
        />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i}><SkeletonLine width="80%" height={12} /></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, ri) => (
            <tr key={ri}>
              {Array.from({ length: cols }).map((_, ci) => (
                <td key={ci}>
                  <SkeletonLine
                    width={ci === 0 ? '60%' : '40%'}
                    height={12}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="stats-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="stat-card">
          <SkeletonLine width="50%" height={12} style={{ marginBottom: 8 }} />
          <SkeletonLine width="70%" height={28} />
        </div>
      ))}
    </div>
  );
}
