'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { label: '儀表板', href: '/', icon: '📊' },
  { label: '訂單管理', href: '/orders', icon: '📦' },
  { label: '客戶管理', href: '/customers', icon: '👥' },
  { label: '買手管理', href: '/buyers', icon: '🛒' },
  { label: '交易記錄', href: '/transactions', icon: '💰' },
  { label: '退款管理', href: '/refunds', icon: '↩️' },
];

const FINANCE = [
  { label: '財務報表', href: '/financials', icon: '📈' },
  { label: '月結管理', href: '/periods', icon: '📅' },
];

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">🛍️ BuyerOS</div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          <div className="nav-section-title">業務</div>
          {NAV.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={isActive(item.href) ? 'active' : ''}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </div>

        <div className="nav-section">
          <div className="nav-section-title">財務</div>
          {FINANCE.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={isActive(item.href) ? 'active' : ''}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </aside>
  );
}
