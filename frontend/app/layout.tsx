import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BuyerOS 管理台",
  description: "BuyerOS / AIOS shared context operations console"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
