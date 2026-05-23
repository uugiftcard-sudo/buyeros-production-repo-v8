'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const MAIN = [
  { label: '儀表板',    href: '/',           icon: '📊' },
  { label: '訂單管理',   href: '/orders',     icon: '📦' },
  { label: '客戶管理',   href: '/customers',  icon: '👥' },
  { label: '買手管理',   href: '/buyers',     icon: '🛒' },
  { label: '交易記錄',   href: '/transactions', icon: '💳' },
  { label: '退款管理',   href: '/refunds',    icon: '↩️' },
];

const MANAGEMENT = [
  { label: '團隊管理',   href: '/teams',      icon: '🏆' },
  { label: '員工管理',   href: '/staff',      icon: '👤' },
  { label: '審計日誌',   href: '/audit-log', icon: '🕵️' },
];

const FINANCE = [
  { label: '財務報表',   href: '/financials',  icon: '📈' },
  { label: '月結管理',  href: '/periods',    icon: '📅' },
];

const SYSTEM = [
  { label: '通訊記錄',  href: '/communications', icon: '💬' },
  { label: '系統設定',  href: '/settings',     icon: '⚙️' },
];

function NavItem({ href, label, icon }: { href: string; label: string; icon: string }) {
  const pathname = usePathname();
  const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <Link href={href} className={isActive ? 'active' : ''}>
      <span className="nav-icon">{icon}</span>
      <span className="nav-label">{label}</span>
    </Link>
  );
}

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🛍</div>
        <div>
          <div className="sidebar-logo-text">BuyerOS</div>
          <div className="sidebar-logo-sub">Admin Console</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          <div className="nav-section-title">業務</div>
          {MAIN.map(item => <NavItem key={item.href} {...item} />)}
        </div>

        <div className="nav-section">
          <div className="nav-section-title">管理</div>
          {MANAGEMENT.map(item => <NavItem key={item.href} {...item} />)}
        </div>

        <div className="nav-section">
          <div className="nav-section-title">財務</div>
          {FINANCE.map(item => <NavItem key={item.href} {...item} />)}
        </div>

        <div className="nav-section">
          <div className="nav-section-title">系統</div>
          {SYSTEM.map(item => <NavItem key={item.href} {...item} />)}
        </div>
      </nav>

      <div className="sidebar-footer">
        <div>BuyerOS v1.0</div>
        <div style={{ marginTop: 2, opacity: 0.6 }}>買手對象系統</div>
      </div>
    </aside>
  );
}
