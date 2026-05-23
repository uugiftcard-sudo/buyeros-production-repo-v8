import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'BuyerOS Admin',
  description: '買手對象系統管理後台',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
